#!/usr/bin/env python3
"""Validate and resolve PStack's user-owned model policy without changing files.

The OpenCode native-agent adapter targets OpenCode 1.x only.
"""

import argparse
import json
import re
import sys
from pathlib import Path


SINGLE_ROLES = {
    "feature", "refactoring", "bug-fix", "perf-issue", "hillclimb",
    "judgment and prose", "hardest tasks", "how explorer", "how explainer",
    "why investigators", "why synthesizer", "reflect tooling",
    "reflect judgment, divergent, synthesizer", "swarm workers", "recall fanout",
}
LIST_ROLES = {
    "arena runners", "arena cross-judge pool", "architect runners",
    "interrogate reviewers",
}
HARNESSES = {"codex", "opencode"}
PROFILE_ID = re.compile(r"^[a-z][a-z0-9-]*$")


class PolicyError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PolicyError(message)


def validate(policy):
    require(isinstance(policy, dict), "policy must be a JSON object")
    require(set(policy) == {"version", "harnesses", "profiles", "roles"}, "policy has unknown or missing top-level fields")
    require(type(policy.get("version")) is int and policy["version"] == 1, "version must be 1")
    harnesses = policy.get("harnesses")
    require(isinstance(harnesses, list) and harnesses, "harnesses must be a nonempty list")
    require(all(isinstance(h, str) and h in HARNESSES for h in harnesses), "unsupported harness")
    require(len(harnesses) == len(set(harnesses)), "duplicate harness")

    profiles = policy.get("profiles")
    require(isinstance(profiles, dict) and profiles, "profiles must be a nonempty object")
    for name, targets in profiles.items():
        require(isinstance(name, str) and PROFILE_ID.fullmatch(name), f"invalid profile name: {name!r}")
        require(isinstance(targets, dict), f"profile {name} must be an object")
        require(set(targets) <= HARNESSES, f"profile {name} has an unsupported harness entry")
        for harness in harnesses:
            spec = targets.get(harness)
            require(isinstance(spec, dict), f"profile {name} lacks {harness} settings")
            if "selection" in spec:
                require(spec == {"selection": "inherit-parent"}, f"profile {name}/{harness}: invalid inherit entry")
                continue
            model = spec.get("model")
            require(isinstance(model, str) and model.strip() == model and model, f"profile {name}/{harness}: model is required")
            require(not any(c.isspace() for c in model), f"profile {name}/{harness}: model contains whitespace")
            require(model not in {"auto", "inherit-parent"}, f"profile {name}/{harness}: alias is not a model")
            if harness == "codex":
                require(set(spec) <= {"model", "reasoning_effort"}, f"profile {name}/codex: unknown field")
                if "reasoning_effort" in spec:
                    effort = spec["reasoning_effort"]
                    require(isinstance(effort, str) and effort, f"profile {name}/codex: invalid effort")
            else:
                require("/" in model and not model.startswith("/") and not model.endswith("/"), f"profile {name}/opencode: use provider/model")
                require("#" not in model, f"profile {name}/opencode: keep variants out of the model ID for OpenCode 1.x")
                require(set(spec) <= {"model", "options"}, f"profile {name}/opencode: unknown field")
                options = spec.get("options", {})
                require(isinstance(options, dict), f"profile {name}/opencode: options must be an object")
                reserved = {"description", "mode", "model", "name", "permission", "prompt", "temperature", "tools", "top_p"}
                for key in options:
                    require(isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key), f"profile {name}/opencode: invalid option key {key!r}")
                    require(key not in reserved, f"profile {name}/opencode: {key!r} is an agent field, not a model option")

    roles = policy.get("roles")
    require(isinstance(roles, dict), "roles must be an object")
    expected = SINGLE_ROLES | LIST_ROLES
    require(set(roles) == expected, f"roles differ: missing={sorted(expected - set(roles))}, extra={sorted(set(roles) - expected)}")
    for role in SINGLE_ROLES:
        route = roles[role]
        require(isinstance(route, dict), f"role {role}: expected an object")
        default, allowed = route.get("default"), route.get("allowed")
        require(isinstance(default, str) and default in profiles, f"role {role}: unknown default profile")
        require(isinstance(allowed, list) and allowed, f"role {role}: allowed must be a nonempty list")
        require(all(isinstance(p, str) and p in profiles for p in allowed), f"role {role}: unknown allowed profile")
        require(default in allowed and len(allowed) == len(set(allowed)), f"role {role}: allowed must uniquely include default")
        require(set(route) == {"default", "allowed"}, f"role {role}: unknown field")
    for role in LIST_ROLES:
        route = roles[role]
        require(isinstance(route, dict) and set(route) == {"default"}, f"role {role}: expected a default list")
        values = route["default"]
        require(isinstance(values, list) and values, f"role {role}: list must be nonempty")
        require(all(isinstance(p, str) and p in profiles for p in values), f"role {role}: unknown profile")
    return policy


def resolve(policy, harness, role, profile=None, index=None):
    require(harness in policy["harnesses"], f"harness {harness} is not configured")
    require(role in policy["roles"], f"unknown role: {role}")
    route = policy["roles"][role]
    if role in LIST_ROLES:
        require(profile is None, "list roles do not accept a profile override")
        require(index is not None, "list roles require --index (zero-based)")
        require(0 <= index < len(route["default"]), "list index is out of range")
        selected = route["default"][index]
    else:
        require(index is None, "single roles do not accept --index")
        selected = profile or route["default"]
        require(selected in route["allowed"], f"profile {selected} is not allowed for {role}")
    return {"role": role, "profile": selected, "harness": harness, "settings": policy["profiles"][selected][harness]}


def render_agent(policy, harness, profile):
    require(harness in policy["harnesses"], f"harness {harness} is not configured")
    require(profile in policy["profiles"], f"unknown profile: {profile}")
    settings = policy["profiles"][profile][harness]
    name = f"pstack-{profile}"
    if harness == "codex":
        lines = [
            f"name = {json.dumps(name)}",
            f"description = {json.dumps('PStack model profile: ' + profile)}",
            'developer_instructions = "Follow the invoking task and its constraints."',
        ]
        if "model" in settings:
            lines.append(f"model = {json.dumps(settings['model'])}")
            if settings.get("reasoning_effort") is not None:
                lines.append(f"model_reasoning_effort = {json.dumps(settings['reasoning_effort'])}")
        return "\n".join(lines) + "\n"
    lines = ["---", f"description: {json.dumps('PStack model profile: ' + profile)}", "mode: subagent"]
    if "model" in settings:
        lines.append(f"model: {json.dumps(settings['model'])}")
        for key, value in settings.get("options", {}).items():
            require(isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key), f"invalid OpenCode option key: {key!r}")
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "resolve", "render-agent"])
    parser.add_argument("--policy", type=Path, default=Path.home() / ".config/pstack/models.json")
    parser.add_argument("--harness", choices=sorted(HARNESSES))
    parser.add_argument("--role")
    parser.add_argument("--profile")
    parser.add_argument("--index", type=int)
    args = parser.parse_args()
    try:
        policy = validate(json.loads(args.policy.read_text(encoding="utf-8")))
        if args.command == "validate":
            print("PStack model policy is structurally valid; model availability still needs harness verification")
        elif args.command == "resolve":
            require(args.harness and args.role, "resolve requires --harness and --role")
            print(json.dumps(resolve(policy, args.harness, args.role, args.profile, args.index), ensure_ascii=False))
        else:
            require(args.harness and args.profile, "render-agent requires --harness and --profile")
            print(render_agent(policy, args.harness, args.profile), end="")
    except (OSError, json.JSONDecodeError, PolicyError) as exc:
        print(f"PStack model policy error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
