#!/usr/bin/env python3
"""Pure checks for PStack's v2 model-pool policy.

Reads `~/.config/pstack/models.json` and an optional orchestrator_capabilities
snapshot, then prints structure, resolution, or readiness results. It never
writes user files, never invokes a model, and never contacts a provider.
"""

import argparse
import json
import re
import sys
from pathlib import Path

POLICY_VERSION = 2
ENTRY_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
OPTION_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
TIERS = ("default", "escalation")
V1_HINT = (
    "version 1 is a role-routing policy and is no longer read by this helper; "
    "the file was left unchanged. Run `model_policy.py convert` to print a "
    "reviewed v2 conversion, confirm each entry with the user, then save the "
    "reviewed policy."
)


class PolicyError(ValueError):
    pass


class MigrationRequired(PolicyError):
    pass


def require(condition, message):
    if not condition:
        raise PolicyError(message)


def is_token(value):
    return (
        isinstance(value, str)
        and value == value.strip()
        and bool(value)
        and not any(character.isspace() for character in value)
    )


def validate(policy):
    require(isinstance(policy, dict), "policy must be a JSON object")
    version = policy.get("version")
    if (type(version) is int and version == 1) or (
        "version" not in policy and "profiles" in policy and "roles" in policy
    ):
        raise MigrationRequired(V1_HINT)
    require(
        set(policy) == {"version", "pool"},
        "policy has unknown or missing top-level fields",
    )
    require(
        type(version) is int and version == POLICY_VERSION,
        f"version must be the integer {POLICY_VERSION}",
    )
    pool = policy["pool"]
    require(isinstance(pool, list) and pool, "pool must be a nonempty list")
    seen = set()
    for entry in pool:
        require(isinstance(entry, dict), "pool entries must be objects")
        extra = set(entry) - {"id", "providerInstanceId", "model", "options", "tier"}
        require(not extra, f"pool entry has unknown fields: {sorted(extra)}")
        missing = {"id", "providerInstanceId", "model"} - set(entry)
        require(not missing, f"pool entry is missing {sorted(missing)}")
        entry_id = entry["id"]
        require(
            isinstance(entry_id, str) and ENTRY_ID.fullmatch(entry_id),
            f"invalid pool entry id: {entry_id!r}",
        )
        require(entry_id not in seen, f"duplicate pool entry id: {entry_id}")
        seen.add(entry_id)
        for field in ("providerInstanceId", "model"):
            require(
                is_token(entry[field]),
                f"pool entry {entry_id}: {field} must be a nonempty token",
            )
        require(
            entry.get("tier", "default") in TIERS,
            f"pool entry {entry_id}: tier must be one of {list(TIERS)}",
        )
        options = entry.get("options", {})
        require(isinstance(options, dict), f"pool entry {entry_id}: options must be an object")
        for key, value in options.items():
            require(
                isinstance(key, str) and OPTION_KEY.fullmatch(key),
                f"pool entry {entry_id}: invalid option key {key!r}",
            )
            require(
                isinstance(value, bool) or is_token(value),
                f"pool entry {entry_id}: option {key} must be a nonempty token or boolean",
            )
    require(
        any(entry.get("tier", "default") == "default" for entry in pool),
        "pool needs at least one default-tier entry",
    )
    return policy


def validate_snapshot(snapshot):
    require(isinstance(snapshot, dict), "snapshot must be a JSON object")
    require(
        isinstance(snapshot.get("providers"), list),
        "snapshot must be an orchestrator_capabilities object with a providers list",
    )
    inherited = snapshot.get("inheritedProviderInstanceId")
    if inherited is not None:
        require(
            isinstance(inherited, str),
            "snapshot inheritedProviderInstanceId must be a string",
        )
    for provider in snapshot["providers"]:
        require(isinstance(provider, dict), "snapshot provider entries must be objects")
        provider_id = provider.get("providerInstanceId")
        require(
            isinstance(provider_id, str) and provider_id,
            "snapshot provider entries need a providerInstanceId",
        )
        models = provider.get("models")
        require(
            isinstance(models, list), f"provider {provider_id}: models must be a list"
        )
        for model in models:
            require(
                isinstance(model, dict), f"provider {provider_id}: model entries must be objects"
            )
            model_id = model.get("id")
            require(
                isinstance(model_id, str) and model_id,
                f"provider {provider_id}: model entries need a string id",
            )
            descriptors = model.get("options", [])
            require(isinstance(descriptors, list), f"model {model_id}: options must be a list")
            for descriptor in descriptors:
                require(
                    isinstance(descriptor, dict),
                    f"model {model_id}: option descriptors must be objects",
                )
                descriptor_id = descriptor.get("id")
                require(
                    isinstance(descriptor_id, str) and descriptor_id,
                    f"model {model_id}: option descriptors need a string id",
                )
                kind = descriptor.get("type")
                require(
                    kind in {"select", "boolean"},
                    f"model {model_id}: option {descriptor_id} has unsupported type {kind!r}",
                )
                if kind == "select":
                    choices = descriptor.get("options")
                    require(
                        isinstance(choices, list),
                        f"model {model_id}: select option {descriptor_id} needs an options list",
                    )
                    for choice in choices:
                        require(
                            isinstance(choice, dict) and isinstance(choice.get("id"), str),
                            f"model {model_id}: select option {descriptor_id} choices need string ids",
                        )
                if "promptInjectedValues" in descriptor:
                    injected = descriptor["promptInjectedValues"]
                    require(
                        isinstance(injected, list)
                        and all(isinstance(value, str) for value in injected),
                        f"model {model_id}: promptInjectedValues must be a list of strings",
                    )
        constraints = provider.get("constraints", [])
        require(
            isinstance(constraints, list),
            f"provider {provider_id}: constraints must be a list",
        )
    return snapshot


def provider_by_id(snapshot, provider_instance_id):
    for provider in snapshot["providers"]:
        if provider.get("providerInstanceId") == provider_instance_id:
            return provider
    return None


def unavailable_reason(snapshot, provider):
    constraints = [str(item) for item in provider.get("constraints") or []]
    if constraints:
        return "reports constraints: " + "; ".join(constraints)
    if provider.get("canRunChildTask") is not True:
        return "does not advertise canRunChildTask"
    if (
        provider.get("providerInstanceId") != snapshot.get("inheritedProviderInstanceId")
        and provider.get("canRunCrossProviderChildTask") is not True
    ):
        return "does not advertise canRunCrossProviderChildTask"
    return None


def model_by_id(provider, model_id):
    for model in provider.get("models", []):
        if model.get("id") == model_id:
            return model
    return None


def binding_problems(snapshot, provider_instance_id, model_id, options):
    provider = provider_by_id(snapshot, provider_instance_id)
    if provider is None:
        return [f"provider {provider_instance_id!r} is not advertised in this snapshot"]
    problems = []
    reason = unavailable_reason(snapshot, provider)
    if reason:
        problems.append(f"provider {provider_instance_id!r} {reason}")
    model = model_by_id(provider, model_id)
    if model is None:
        problems.append(
            f"model {model_id!r} is not advertised for provider {provider_instance_id!r}"
        )
        return problems
    descriptors = {
        descriptor.get("id"): descriptor
        for descriptor in model.get("options") or []
        if isinstance(descriptor, dict)
    }
    for key, value in (options or {}).items():
        descriptor = descriptors.get(key)
        if descriptor is None:
            problems.append(f"model {model_id!r} does not advertise option {key!r}")
            continue
        kind = descriptor.get("type")
        if kind == "select":
            advertised = [
                choice.get("id")
                for choice in descriptor.get("options") or []
                if isinstance(choice, dict)
            ]
            if value not in advertised:
                problems.append(
                    f"option {key}={value!r} is not advertised for model {model_id!r}; "
                    f"advertised: {advertised}"
                )
        elif kind == "boolean":
            if not isinstance(value, bool):
                problems.append(f"option {key} expects a boolean value")
        else:
            problems.append(f"option {key!r} advertises unsupported type {kind!r}")
    return problems


def ready(policy, snapshot=None):
    result = {"structural": True, "pool": len(policy["pool"])}
    if snapshot is None:
        result["advertised"] = "not-checked"
    else:
        failures = []
        for entry in policy["pool"]:
            problems = binding_problems(
                snapshot,
                entry["providerInstanceId"],
                entry["model"],
                entry.get("options", {}),
            )
            if problems:
                failures.append({"id": entry["id"], "problems": problems})
        result["advertised"] = {"verified": not failures}
        if failures:
            result["advertised"]["failures"] = failures
    result["invocation"] = (
        "unverified: only a live delegated call that succeeds can confirm the target runs"
    )
    return result


def resolve(
    policy,
    snapshot=None,
    entry_id=None,
    provider_instance_id=None,
    model=None,
    options=None,
    authorize_explicit=None,
):
    options = dict(options or {})
    if entry_id is not None:
        require(
            provider_instance_id is None and model is None and not options,
            "--id resolves one saved pool entry and cannot be combined with target flags",
        )
        entry = next((item for item in policy["pool"] if item["id"] == entry_id), None)
        require(entry is not None, f"unknown pool entry id: {entry_id!r}")
        target = {
            "source": "pool",
            "id": entry["id"],
            "providerInstanceId": entry["providerInstanceId"],
            "model": entry["model"],
            "options": dict(entry.get("options", {})),
            "tier": entry.get("tier", "default"),
        }
    else:
        require(
            provider_instance_id and model,
            "resolve needs --id, or --provider-instance-id with --model",
        )
        match = next(
            (
                item
                for item in policy["pool"]
                if item["providerInstanceId"] == provider_instance_id
                and item["model"] == model
                and dict(item.get("options", {})) == options
            ),
            None,
        )
        if match is not None:
            target = {
                "source": "pool",
                "id": match["id"],
                "providerInstanceId": match["providerInstanceId"],
                "model": match["model"],
                "tier": match.get("tier", "default"),
                "options": dict(match.get("options", {})),
            }
        else:
            require(
                isinstance(authorize_explicit, str) and authorize_explicit.strip(),
                f"{provider_instance_id}/{model} with options {options} is not a saved "
                "pool combination. The pool is not expanded automatically: get the "
                "user's explicit authorization for this task, then retry with "
                "--authorize-explicit carrying that instruction as evidence. This "
                "script cannot verify consent and is not a permission check.",
            )
            target = {
                "source": "explicit",
                "providerInstanceId": provider_instance_id,
                "model": model,
                "options": options,
                "authorization": authorize_explicit.strip(),
            }
    if snapshot is not None:
        problems = binding_problems(
            snapshot, target["providerInstanceId"], target["model"], target["options"]
        )
        require(not problems, "; ".join(problems))
        target["advertised"] = "verified"
    else:
        target["advertised"] = "not-checked"
    target["invocation"] = "unverified"
    return target


def list_pool(policy, tier=None):
    return [
        {
            "id": entry["id"],
            "tier": entry.get("tier", "default"),
            "providerInstanceId": entry["providerInstanceId"],
            "model": entry["model"],
            "options": dict(entry.get("options", {})),
        }
        for entry in policy["pool"]
        if tier is None or entry.get("tier", "default") == tier
    ]


def propose(snapshot, provider_instance_id, model_id):
    provider = provider_by_id(snapshot, provider_instance_id)
    require(
        provider is not None,
        f"provider {provider_instance_id!r} is not advertised in this snapshot",
    )
    model = model_by_id(provider, model_id)
    require(
        model is not None,
        f"model {model_id!r} is not advertised for provider {provider_instance_id!r}",
    )
    descriptors = []
    for descriptor in model.get("options") or []:
        item = {
            "id": descriptor.get("id"),
            "label": descriptor.get("label"),
            "type": descriptor.get("type"),
        }
        if "description" in descriptor:
            item["description"] = descriptor["description"]
        if "currentValue" in descriptor:
            item["currentValue"] = descriptor["currentValue"]
        if "promptInjectedValues" in descriptor:
            item["promptInjectedValues"] = list(descriptor["promptInjectedValues"])
        if descriptor.get("type") == "select":
            choices = []
            for choice in descriptor.get("options") or []:
                entry = {"id": choice.get("id"), "label": choice.get("label")}
                if "description" in choice:
                    entry["description"] = choice["description"]
                if "isDefault" in choice:
                    entry["isDefault"] = choice["isDefault"]
                choices.append(entry)
            item["choices"] = choices
        descriptors.append(item)
    return {
        "providerInstanceId": provider_instance_id,
        "model": model_id,
        "label": model.get("label"),
        "runnable": unavailable_reason(snapshot, provider) is None,
        "constraints": [str(item) for item in provider.get("constraints") or []],
        "options": descriptors,
        "proposalRule": (
            "No value is ranked here: descriptor order has no guaranteed strength "
            "semantics. Recommend a value only when the descriptor's label, "
            "description, default, promptInjectedValues, or current provider evidence "
            "establishes it; otherwise show the choices and ask. Never treat a "
            "non-reasoning option (serviceTier, fastMode, contextWindow, agent) as a "
            "reasoning setting."
        ),
    }


def make_entry_id(taken, provider_instance_id, model_id):
    slug = re.sub(r"[^a-z0-9]+", "-", f"{provider_instance_id}-{model_id}".lower()).strip("-")
    if not slug or not slug[0].isalpha():
        slug = f"target-{slug}".strip("-")
    slug = slug[:64].rstrip("-")
    candidate = slug
    suffix = 2
    while candidate in taken:
        tail = f"-{suffix}"
        candidate = slug[: 64 - len(tail)].rstrip("-") + tail
        suffix += 1
    return candidate


def convert_v1(policy):
    require(isinstance(policy, dict), "v1 policy must be a JSON object")
    require(policy.get("version") == 1, "convert expects a version 1 policy")
    profiles = policy.get("profiles")
    harnesses = policy.get("harnesses")
    roles = policy.get("roles")
    require(isinstance(profiles, dict) and profiles, "v1 policy has no profiles")
    require(isinstance(harnesses, list) and harnesses, "v1 policy has no harnesses")
    require(isinstance(roles, dict) and roles, "v1 policy has no roles")

    role_scope = {}
    for role, route in roles.items():
        if not isinstance(route, dict):
            continue
        default = route.get("default")
        names = [default] if isinstance(default, str) else []
        if isinstance(default, list):
            names = [name for name in default if isinstance(name, str)]
        if isinstance(route.get("allowed"), list):
            names += [name for name in route["allowed"] if isinstance(name, str)]
        for name in names:
            role_scope.setdefault(name, set()).add(role)

    drafts = {}
    dropped = []
    for profile in sorted(profiles):
        targets = profiles[profile]
        if not isinstance(targets, dict):
            dropped.append({"profile": profile, "reason": "v1 profile is not an object"})
            continue
        for harness in harnesses:
            spec = targets.get(harness)
            if not isinstance(spec, dict):
                dropped.append(
                    {"profile": profile, "harness": harness, "reason": "no entry for this harness"}
                )
                continue
            if spec.get("selection") == "inherit-parent":
                dropped.append(
                    {
                        "profile": profile,
                        "harness": harness,
                        "reason": "inherit-parent is not a concrete target and has no v2 equivalent",
                    }
                )
                continue
            model = spec.get("model")
            if not isinstance(model, str) or not model:
                dropped.append(
                    {"profile": profile, "harness": harness, "reason": "no concrete model"}
                )
                continue
            options = {}
            if isinstance(spec.get("reasoning_effort"), str):
                options["reasoning_effort"] = spec["reasoning_effort"]
            if isinstance(spec.get("options"), dict):
                for key, value in spec["options"].items():
                    if isinstance(value, (str, bool)):
                        options[key] = value
            key = (harness, model, json.dumps(options, sort_keys=True))
            draft = drafts.get(key)
            if draft is None:
                draft = {
                    "providerInstanceId": harness,
                    "model": model,
                    "options": options,
                    "v1Profiles": [],
                    "v1Roles": set(),
                }
                drafts[key] = draft
            draft["v1Profiles"].append(profile)
            draft["v1Roles"].update(role_scope.get(profile, ()))

    taken = set()
    review = []
    pool = []
    for draft in drafts.values():
        entry_id = make_entry_id(taken, draft["providerInstanceId"], draft["model"])
        taken.add(entry_id)
        warnings = [
            "v1 role restrictions do not carry into the v2 pool: a saved entry is "
            "authorized for every task role. Confirm this entry or remove it.",
            "re-verify the model id, option ids, and option values against this "
            "thread's capability snapshot; v1 harness-native names may differ from "
            "T3 option descriptors.",
        ]
        review.append(
            {
                "id": entry_id,
                "providerInstanceId": draft["providerInstanceId"],
                "model": draft["model"],
                "options": draft["options"],
                "v1Profiles": draft["v1Profiles"],
                "v1Roles": sorted(draft["v1Roles"]),
                "warnings": warnings,
            }
        )
        pool.append(
            {
                "id": entry_id,
                "providerInstanceId": draft["providerInstanceId"],
                "model": draft["model"],
                "options": draft["options"],
            }
        )
    return {
        "migrationRequired": True,
        "sourceVersion": 1,
        "notes": [
            "This is a draft for review; this helper never writes the policy file.",
            "v1 role restrictions are not preserved: v2 has one shared pool.",
            "Save only after the user confirms each entry and after option ids are "
            "re-verified against the current capability snapshot.",
        ],
        "dropped": dropped,
        "review": review,
        "proposed": {"version": 2, "pool": pool},
    }


def parse_option_flags(flags):
    options = {}
    for flag in flags:
        require("=" in flag, f"--option expects KEY=VALUE, got {flag!r}")
        key, _, raw = flag.partition("=")
        require(
            isinstance(key, str) and OPTION_KEY.fullmatch(key),
            f"invalid option key {key!r}",
        )
        require(key not in options, f"duplicate option {key!r}")
        if raw in {"true", "false"}:
            options[key] = raw == "true"
        else:
            require(is_token(raw), f"invalid value for option {key!r}")
            options[key] = raw
    return options


def load_snapshot(source):
    text = sys.stdin.read() if str(source) == "-" else Path(source).read_text(encoding="utf-8")
    return validate_snapshot(json.loads(text))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "ready", "resolve", "list", "propose", "convert"])
    parser.add_argument("--policy", type=Path, default=Path.home() / ".config/pstack/models.json")
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="file with the orchestrator_capabilities JSON, or - for stdin",
    )
    parser.add_argument("--id", dest="entry_id")
    parser.add_argument("--tier", choices=TIERS, help="list only entries of this tier")
    parser.add_argument("--provider-instance-id")
    parser.add_argument("--model")
    parser.add_argument("--option", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument(
        "--authorize-explicit",
        metavar="REASON",
        help=(
            "the user's actual instruction authorizing a one-off target; supplied as "
            "evidence by the caller, not verified by this script"
        ),
    )
    parser.add_argument("--harness", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.command == "propose":
            require(args.snapshot is not None, "propose requires --snapshot")
            require(
                args.provider_instance_id and args.model,
                "propose requires --provider-instance-id and --model",
            )
            print(
                json.dumps(
                    propose(load_snapshot(args.snapshot), args.provider_instance_id, args.model),
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0
        raw = json.loads(args.policy.read_text(encoding="utf-8"))
        if args.command == "convert":
            print(json.dumps(convert_v1(raw), indent=2, ensure_ascii=False))
            return 0
        policy = validate(raw)
        require(
            args.harness is None,
            "--harness belonged to the version 1 per-harness role policy and is not "
            "part of the v2 shared pool (see references/model-routing.md).",
        )
        snapshot = load_snapshot(args.snapshot) if args.snapshot else None
        if args.command == "list":
            print(json.dumps(list_pool(policy, args.tier), indent=2, ensure_ascii=False))
        elif args.command == "validate":
            print("PStack model pool is structurally valid; availability and invocation are not checked")
        elif args.command == "ready":
            result = ready(policy, snapshot)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            advertised = result["advertised"]
            if isinstance(advertised, dict) and not advertised["verified"]:
                print("not ready: advertised capability check failed", file=sys.stderr)
                return 1
        elif args.command == "resolve":
            target = resolve(
                policy,
                snapshot,
                args.entry_id,
                args.provider_instance_id,
                args.model,
                parse_option_flags(args.option),
                args.authorize_explicit,
            )
            print(json.dumps(target, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, PolicyError) as exc:
        print(f"PStack model policy error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
