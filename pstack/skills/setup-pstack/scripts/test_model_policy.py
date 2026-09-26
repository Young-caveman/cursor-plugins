#!/usr/bin/env python3
"""Tests for the PStack v2 model-policy helper. Standard library only."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import model_policy

SCRIPT = Path(__file__).resolve().with_name("model_policy.py")


def capability_snapshot():
    return {
        "parentThreadId": "thread:test",
        "inheritedProviderInstanceId": "opencode",
        "inheritedModel": "opencode-go/deepseek-v4.1-flash",
        "providers": [
            {
                "providerInstanceId": "codex",
                "driverKind": "codex",
                "displayName": "Codex",
                "models": [
                    {
                        "id": "gpt-6-astra",
                        "label": "GPT-6-Astra",
                        "options": [
                            {
                                "id": "reasoningEffort",
                                "label": "Reasoning",
                                "type": "select",
                                "options": [
                                    {"id": "low", "label": "Low"},
                                    {"id": "medium", "label": "Medium", "isDefault": True},
                                    {"id": "high", "label": "High"},
                                    {"id": "xhigh", "label": "Extra High"},
                                ],
                                "currentValue": "medium",
                            },
                            {
                                "id": "serviceTier",
                                "label": "Service Tier",
                                "type": "select",
                                "options": [
                                    {"id": "default", "label": "Standard", "isDefault": True},
                                    {
                                        "id": "priority",
                                        "label": "Fast",
                                        "description": "2x speed",
                                    },
                                ],
                                "currentValue": "default",
                            },
                        ],
                    }
                ],
                "canRunChildTask": True,
                "canRunCrossProviderChildTask": True,
                "constraints": [],
            },
            {
                "providerInstanceId": "opencode",
                "driverKind": "opencode",
                "displayName": "OpenCode",
                "models": [
                    {
                        "id": "opencode-go/deepseek-v4.1-flash",
                        "label": "DeepSeek V4.1 Flash",
                        "options": [
                            {
                                "id": "variant",
                                "label": "Reasoning",
                                "type": "select",
                                "options": [
                                    {"id": "low", "label": "Low"},
                                    {"id": "high", "label": "High"},
                                    {"id": "max", "label": "Max"},
                                ],
                            },
                            {
                                "id": "agent",
                                "label": "Agent",
                                "type": "select",
                                "options": [
                                    {"id": "build", "label": "Build", "isDefault": True},
                                    {"id": "plan", "label": "Plan"},
                                ],
                                "currentValue": "build",
                            },
                        ],
                    }
                ],
                "canRunChildTask": True,
                "canRunCrossProviderChildTask": True,
                "constraints": [],
            },
            {
                "providerInstanceId": "claudeAgent",
                "driverKind": "claudeAgent",
                "displayName": "Claude",
                "models": [
                    {
                        "id": "claude-opus-5",
                        "label": "Claude Opus 5",
                        "options": [
                            {
                                "id": "effort",
                                "label": "Reasoning",
                                "type": "select",
                                "options": [
                                    {"id": "low", "label": "Low"},
                                    {"id": "medium", "label": "Medium"},
                                    {"id": "high", "label": "High", "isDefault": True},
                                    {"id": "xhigh", "label": "Extra High"},
                                    {"id": "max", "label": "Max"},
                                    {
                                        "id": "ultracode",
                                        "label": "Ultracode",
                                        "description": "xhigh effort plus multi-agent workflow orchestration",
                                    },
                                    {"id": "ultrathink", "label": "Ultrathink"},
                                ],
                                "promptInjectedValues": ["ultrathink"],
                            },
                            {"id": "fastMode", "label": "Fast Mode", "type": "boolean"},
                            {
                                "id": "contextWindow",
                                "label": "Context Window",
                                "type": "select",
                                "options": [
                                    {"id": "200k", "label": "200k"},
                                    {"id": "1m", "label": "1M", "isDefault": True},
                                ],
                            },
                        ],
                    }
                ],
                "canRunChildTask": False,
                "canRunCrossProviderChildTask": False,
                "constraints": ["Provider instance is disabled."],
            },
        ],
    }


def boolean_snapshot(label="Thinking"):
    return {
        "inheritedProviderInstanceId": "testp",
        "providers": [
            {
                "providerInstanceId": "testp",
                "driverKind": "codex",
                "displayName": "Test",
                "models": [
                    {
                        "id": "m",
                        "label": "M",
                        "options": [
                            {
                                "id": "thinking",
                                "label": label,
                                "type": "boolean",
                                "currentValue": False,
                            }
                        ],
                    }
                ],
                "canRunChildTask": True,
                "canRunCrossProviderChildTask": True,
                "constraints": [],
            }
        ],
    }


def pool_policy():
    return {
        "version": 2,
        "pool": [
            {
                "id": "codex-gpt-6-astra-high",
                "providerInstanceId": "codex",
                "model": "gpt-6-astra",
                "options": {"reasoningEffort": "high"},
            },
            {
                "id": "opencode-deepseek-v4-1-flash-max",
                "providerInstanceId": "opencode",
                "model": "opencode-go/deepseek-v4.1-flash",
                "options": {"variant": "max"},
            },
        ],
    }


def v1_policy():
    return {
        "version": 1,
        "harnesses": ["codex", "opencode"],
        "profiles": {
            "fast": {
                "codex": {"model": "gpt-6-astra", "reasoning_effort": "high"},
                "opencode": {
                    "model": "opencode-go/deepseek-v4.1-flash",
                    "options": {"variant": "max"},
                },
            },
            "parent": {
                "codex": {"selection": "inherit-parent"},
                "opencode": {"selection": "inherit-parent"},
            },
        },
        "roles": {
            "feature": {"default": "fast", "allowed": ["fast", "parent"]},
            "judgment and prose": {"default": "fast", "allowed": ["fast"]},
            "arena runners": {"default": ["fast"]},
        },
    }


class ValidateTest(unittest.TestCase):
    def test_pool_without_roles_is_valid(self):
        policy = pool_policy()
        self.assertEqual(model_policy.validate(policy), policy)
        self.assertNotIn("roles", policy)

    def test_unknown_top_level_field_rejected(self):
        policy = pool_policy()
        policy["roles"] = {"feature": {"default": "x", "allowed": ["x"]}}
        with self.assertRaises(model_policy.PolicyError) as caught:
            model_policy.validate(policy)
        self.assertIn("top-level", str(caught.exception))

    def test_duplicate_entry_ids_rejected(self):
        policy = pool_policy()
        policy["pool"][1]["id"] = policy["pool"][0]["id"]
        with self.assertRaises(model_policy.PolicyError) as caught:
            model_policy.validate(policy)
        self.assertIn("duplicate", str(caught.exception))

    def test_untoken_option_value_rejected(self):
        policy = pool_policy()
        policy["pool"][0]["options"] = {"reasoningEffort": "extra high"}
        with self.assertRaises(model_policy.PolicyError):
            model_policy.validate(policy)

    def test_tier_defaults_and_rejects_unknown(self):
        policy = pool_policy()
        policy["pool"][0]["tier"] = "escalation"
        model_policy.validate(policy)
        policy["pool"][0]["tier"] = "premium"
        with self.assertRaises(model_policy.PolicyError) as caught:
            model_policy.validate(policy)
        self.assertIn("tier", str(caught.exception))

    def test_all_escalation_pool_rejected(self):
        policy = pool_policy()
        for entry in policy["pool"]:
            entry["tier"] = "escalation"
        with self.assertRaises(model_policy.PolicyError) as caught:
            model_policy.validate(policy)
        self.assertIn("default-tier", str(caught.exception))

    def test_list_filters_by_tier_and_resolve_reports_it(self):
        policy = pool_policy()
        policy["pool"][0]["tier"] = "escalation"
        ids = [e["id"] for e in model_policy.list_pool(policy, "default")]
        self.assertNotIn(policy["pool"][0]["id"], ids)
        self.assertEqual(len(ids), len(policy["pool"]) - 1)
        target = model_policy.resolve(policy, entry_id=policy["pool"][0]["id"])
        self.assertEqual(target["tier"], "escalation")
        other = model_policy.resolve(policy, entry_id=policy["pool"][1]["id"])
        self.assertEqual(other["tier"], "default")

    def test_v1_reports_migration_required(self):
        policy = v1_policy()
        before = copy.deepcopy(policy)
        with self.assertRaises(model_policy.MigrationRequired) as caught:
            model_policy.validate(policy)
        self.assertIn("convert", str(caught.exception))
        self.assertEqual(policy, before)

    def test_missing_pool_rejected(self):
        with self.assertRaises(model_policy.PolicyError):
            model_policy.validate({"version": 2, "pool": []})

    def test_non_integer_version_rejected(self):
        for bad in (2.0, "2", True):
            with self.assertRaises(model_policy.PolicyError) as caught:
                model_policy.validate(
                    {
                        "version": bad,
                        "pool": [{"id": "p-m", "providerInstanceId": "p", "model": "m"}],
                    }
                )
            self.assertNotIsInstance(caught.exception, model_policy.MigrationRequired)


class SnapshotTest(unittest.TestCase):
    def test_provider_specific_options_verify(self):
        result = model_policy.ready(pool_policy(), capability_snapshot())
        self.assertTrue(result["structural"])
        self.assertEqual(result["advertised"], {"verified": True})
        self.assertIn("unverified", result["invocation"])

    def test_ready_without_snapshot_is_structural_only(self):
        result = model_policy.ready(pool_policy())
        self.assertEqual(result["advertised"], "not-checked")

    def test_unavailable_provider_reported(self):
        policy = pool_policy()
        policy["pool"].append(
            {
                "id": "claude-opus-5-max",
                "providerInstanceId": "claudeAgent",
                "model": "claude-opus-5",
                "options": {"effort": "max"},
            }
        )
        result = model_policy.ready(policy, capability_snapshot())
        self.assertFalse(result["advertised"]["verified"])
        problems = result["advertised"]["failures"][0]["problems"]
        self.assertTrue(any("disabled" in problem for problem in problems))

    def test_missing_model_reported(self):
        policy = pool_policy()
        policy["pool"][0]["model"] = "gpt-7-absent"
        result = model_policy.ready(policy, capability_snapshot())
        problems = result["advertised"]["failures"][0]["problems"]
        self.assertTrue(any("not advertised" in problem for problem in problems))

    def test_invalid_select_value_reported(self):
        policy = pool_policy()
        policy["pool"][0]["options"] = {"reasoningEffort": "impossible"}
        result = model_policy.ready(policy, capability_snapshot())
        problems = result["advertised"]["failures"][0]["problems"]
        self.assertTrue(any("not advertised" in problem for problem in problems))

    def test_v1_option_name_reported_unknown(self):
        problems = model_policy.binding_problems(
            capability_snapshot(), "codex", "gpt-6-astra", {"reasoning_effort": "high"}
        )
        self.assertTrue(any("does not advertise option" in problem for problem in problems))

    def test_boolean_option_type_enforced(self):
        self.assertEqual(
            model_policy.binding_problems(boolean_snapshot(), "testp", "m", {"thinking": True}),
            [],
        )
        problems = model_policy.binding_problems(
            boolean_snapshot(), "testp", "m", {"thinking": "true"}
        )
        self.assertTrue(any("boolean" in problem for problem in problems))

    def test_unknown_provider_reported(self):
        problems = model_policy.binding_problems(
            capability_snapshot(), "ghost", "model", {}
        )
        self.assertTrue(any("not advertised" in problem for problem in problems))

    def test_malformed_model_entry_rejected(self):
        snapshot = capability_snapshot()
        snapshot["providers"][0]["models"] = ["gpt-6-astra"]
        with self.assertRaises(model_policy.PolicyError):
            model_policy.validate_snapshot(snapshot)

    def test_malformed_descriptor_rejected(self):
        snapshot = capability_snapshot()
        snapshot["providers"][0]["models"][0]["options"][0]["type"] = "slider"
        with self.assertRaises(model_policy.PolicyError):
            model_policy.validate_snapshot(snapshot)
        snapshot = capability_snapshot()
        del snapshot["providers"][0]["models"][0]["options"][0]["options"]
        with self.assertRaises(model_policy.PolicyError):
            model_policy.validate_snapshot(snapshot)

    def test_malformed_prompt_injected_values_rejected(self):
        snapshot = capability_snapshot()
        snapshot["providers"][0]["models"][0]["options"][0]["promptInjectedValues"] = "high"
        with self.assertRaises(model_policy.PolicyError):
            model_policy.validate_snapshot(snapshot)


class ResolveTest(unittest.TestCase):
    def test_resolve_pool_entry_by_id(self):
        target = model_policy.resolve(pool_policy(), entry_id="codex-gpt-6-astra-high")
        self.assertEqual(target["source"], "pool")
        self.assertEqual(target["providerInstanceId"], "codex")
        self.assertEqual(target["options"], {"reasoningEffort": "high"})
        self.assertEqual(target["advertised"], "not-checked")

    def test_resolve_pool_entry_by_exact_target(self):
        target = model_policy.resolve(
            pool_policy(),
            provider_instance_id="opencode",
            model="opencode-go/deepseek-v4.1-flash",
            options={"variant": "max"},
        )
        self.assertEqual(target["source"], "pool")
        self.assertEqual(target["id"], "opencode-deepseek-v4-1-flash-max")

    def test_out_of_pool_rejected_without_authorization(self):
        with self.assertRaises(model_policy.PolicyError) as caught:
            model_policy.resolve(
                pool_policy(),
                provider_instance_id="claudeAgent",
                model="claude-opus-5",
                options={"effort": "max"},
            )
        self.assertIn("explicit authorization", str(caught.exception))

    def test_option_change_rejected_without_authorization(self):
        with self.assertRaises(model_policy.PolicyError):
            model_policy.resolve(
                pool_policy(),
                provider_instance_id="codex",
                model="gpt-6-astra",
                options={"reasoningEffort": "xhigh"},
            )

    def test_explicit_authorization_does_not_mutate_policy(self):
        policy = pool_policy()
        before = copy.deepcopy(policy)
        target = model_policy.resolve(
            policy,
            provider_instance_id="claudeAgent",
            model="claude-opus-5",
            options={"effort": "max"},
            authorize_explicit="user asked for Opus on this task",
        )
        self.assertEqual(target["source"], "explicit")
        self.assertEqual(target["authorization"], "user asked for Opus on this task")
        self.assertEqual(policy, before)

    def test_resolve_with_snapshot_verifies_advertised(self):
        target = model_policy.resolve(
            pool_policy(),
            snapshot=capability_snapshot(),
            entry_id="opencode-deepseek-v4-1-flash-max",
        )
        self.assertEqual(target["advertised"], "verified")
        with self.assertRaises(model_policy.PolicyError):
            model_policy.resolve(
                pool_policy(),
                snapshot=capability_snapshot(),
                provider_instance_id="codex",
                model="gpt-6-astra",
                options={"reasoningEffort": "ultra"},
                authorize_explicit="user asked for ultra on this task",
            )

    def test_unknown_entry_id_rejected(self):
        with self.assertRaises(model_policy.PolicyError):
            model_policy.resolve(pool_policy(), entry_id="missing")


class ProposeTest(unittest.TestCase):
    def test_shuffled_choices_get_no_false_max(self):
        snapshot = capability_snapshot()
        descriptor = snapshot["providers"][0]["models"][0]["options"][0]
        descriptor["options"] = [
            {"id": "max", "label": "Max"},
            {"id": "low", "label": "Low"},
            {"id": "high", "label": "High"},
        ]
        descriptor["promptInjectedValues"] = ["high"]
        result = model_policy.propose(snapshot, "codex", "gpt-6-astra")
        reasoning = next(
            item for item in result["options"] if item["id"] == "reasoningEffort"
        )
        self.assertEqual(
            [choice["id"] for choice in reasoning["choices"]], ["max", "low", "high"]
        )
        self.assertEqual(reasoning["promptInjectedValues"], ["high"])
        self.assertEqual(reasoning["currentValue"], "medium")
        for item in result["options"]:
            self.assertNotIn("proposedValue", item)
            self.assertNotIn("proposalBasis", item)

    def test_choices_carry_defaults_and_descriptions(self):
        result = model_policy.propose(capability_snapshot(), "codex", "gpt-6-astra")
        service = next(item for item in result["options"] if item["id"] == "serviceTier")
        priority = next(
            choice for choice in service["choices"] if choice["id"] == "priority"
        )
        self.assertEqual(priority["description"], "2x speed")
        standard = next(
            choice for choice in service["choices"] if choice["id"] == "default"
        )
        self.assertTrue(standard["isDefault"])

    def test_provider_specific_descriptors_unchanged(self):
        result = model_policy.propose(
            capability_snapshot(), "opencode", "opencode-go/deepseek-v4.1-flash"
        )
        variant = next(item for item in result["options"] if item["id"] == "variant")
        self.assertEqual(
            [choice["id"] for choice in variant["choices"]], ["low", "high", "max"]
        )
        agent = next(item for item in result["options"] if item["id"] == "agent")
        for item in (variant, agent):
            self.assertNotIn("proposedValue", item)

    def test_non_reasoning_boolean_unchanged(self):
        result = model_policy.propose(boolean_snapshot(), "testp", "m")
        self.assertNotIn("proposedValue", result["options"][0])
        self.assertNotIn("choices", result["options"][0])


class ConvertTest(unittest.TestCase):
    def test_v1_conversion_requires_review(self):
        result = model_policy.convert_v1(v1_policy())
        self.assertTrue(result["migrationRequired"])
        self.assertEqual(result["proposed"]["version"], 2)
        self.assertEqual(len(result["proposed"]["pool"]), 2)
        codex = next(
            entry for entry in result["review"] if entry["providerInstanceId"] == "codex"
        )
        self.assertEqual(codex["v1Roles"], ["arena runners", "feature", "judgment and prose"])
        self.assertTrue(any("not carry" in warning for warning in codex["warnings"]))
        self.assertTrue(any("snapshot" in warning for warning in codex["warnings"]))
        dropped = {(item["profile"], item["harness"]) for item in result["dropped"]}
        self.assertEqual(dropped, {("parent", "codex"), ("parent", "opencode")})
        ids = [entry["id"] for entry in result["proposed"]["pool"]]
        self.assertEqual(len(ids), len(set(ids)))
        for entry_id in ids:
            self.assertRegex(entry_id, model_policy.ENTRY_ID)

    def test_duplicate_combinations_merge_profiles(self):
        policy = v1_policy()
        policy["profiles"]["slow"] = copy.deepcopy(policy["profiles"]["fast"])
        result = model_policy.convert_v1(policy)
        self.assertEqual(len(result["proposed"]["pool"]), 2)
        codex = next(
            entry for entry in result["review"] if entry["providerInstanceId"] == "codex"
        )
        self.assertIn("slow", codex["v1Profiles"])

    def test_convert_rejects_v2(self):
        with self.assertRaises(model_policy.PolicyError):
            model_policy.convert_v1(pool_policy())


class CliTest(unittest.TestCase):
    def run_cli(self, args, policy=None, snapshot=None, raw_policy=None, missing_policy=False):
        with tempfile.TemporaryDirectory(prefix="pstack-policy-test-") as tmp:
            command = [sys.executable, "-B", str(SCRIPT)]
            policy_path = Path(tmp) / "models.json"
            if missing_policy:
                command += ["--policy", str(policy_path)]
            elif raw_policy is not None:
                policy_path.write_text(raw_policy, encoding="utf-8")
                command += ["--policy", str(policy_path)]
            elif policy is not None:
                policy_path.write_text(json.dumps(policy), encoding="utf-8")
                command += ["--policy", str(policy_path)]
            if snapshot is not None:
                snapshot_path = Path(tmp) / "capabilities.json"
                snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
                command += ["--snapshot", str(snapshot_path)]
            completed = subprocess.run(
                command + args, capture_output=True, text=True, check=False
            )
            content = policy_path.read_text(encoding="utf-8") if policy_path.exists() else None
            return completed, content

    def test_list_command(self):
        policy = pool_policy()
        policy["pool"][0]["tier"] = "escalation"
        completed, _ = self.run_cli(["list", "--tier", "escalation"], policy=policy)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual([e["id"] for e in json.loads(completed.stdout)], [policy["pool"][0]["id"]])

    def test_missing_policy_file_fails(self):
        with tempfile.TemporaryDirectory(prefix="pstack-policy-test-") as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--policy",
                    str(Path(tmp) / "absent.json"),
                    "validate",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("error", completed.stderr.lower())

    def test_malformed_policy_fails(self):
        completed, _ = self.run_cli(["validate"], raw_policy="{not json")
        self.assertEqual(completed.returncode, 1)
        self.assertIn("error", completed.stderr.lower())

    def test_bad_usage_fails(self):
        completed, _ = self.run_cli(["frobnicate"], policy=pool_policy())
        self.assertEqual(completed.returncode, 2)

    def test_validate_succeeds(self):
        completed, _ = self.run_cli(["validate"], policy=pool_policy())
        self.assertEqual(completed.returncode, 0)
        self.assertIn("structurally valid", completed.stdout)

    def test_ready_snapshot_failure_exits_1(self):
        policy = pool_policy()
        policy["pool"][0]["options"] = {"reasoningEffort": "impossible"}
        completed, _ = self.run_cli(
            ["ready"], policy=policy, snapshot=capability_snapshot()
        )
        self.assertEqual(completed.returncode, 1)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["advertised"]["verified"])

    def test_out_of_pool_cli_requires_authorization_and_preserves_file(self):
        args = ["resolve", "--provider-instance-id", "claudeAgent", "--model", "claude-opus-5", "--option", "effort=max"]
        rejected, content = self.run_cli(args, policy=pool_policy())
        self.assertEqual(rejected.returncode, 1)
        accepted, accepted_content = self.run_cli(
            args + ["--authorize-explicit", "user asked for Opus on this task"],
            policy=pool_policy(),
        )
        self.assertEqual(accepted.returncode, 0)
        payload = json.loads(accepted.stdout)
        self.assertEqual(payload["source"], "explicit")
        self.assertEqual(payload["authorization"], "user asked for Opus on this task")
        self.assertEqual(content, json.dumps(pool_policy()))
        self.assertEqual(accepted_content, content)

    def test_legacy_harness_flag_reports_migration(self):
        completed, _ = self.run_cli(
            ["ready", "--harness", "codex"], policy=pool_policy()
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("--harness", completed.stderr)

    def test_v1_policy_cli_reports_migration_and_preserves_file(self):
        raw = json.dumps(v1_policy())
        completed, content = self.run_cli(["validate"], raw_policy=raw)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("convert", completed.stderr)
        self.assertEqual(content, raw)

    def test_convert_cli_prints_review_draft(self):
        completed, content = self.run_cli(["convert"], policy=v1_policy())
        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["migrationRequired"])
        self.assertEqual(payload["proposed"]["version"], 2)
        self.assertEqual(content, json.dumps(v1_policy()))

    def test_propose_requires_snapshot(self):
        completed, _ = self.run_cli(
            ["propose", "--provider-instance-id", "codex", "--model", "gpt-6-astra"],
            policy=pool_policy(),
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("--snapshot", completed.stderr)

    def test_propose_works_without_policy_file(self):
        completed, _ = self.run_cli(
            ["propose", "--provider-instance-id", "codex", "--model", "gpt-6-astra"],
            snapshot=capability_snapshot(),
            missing_policy=True,
        )
        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["model"], "gpt-6-astra")

    def test_propose_works_with_v1_policy_file(self):
        raw = json.dumps(v1_policy())
        completed, content = self.run_cli(
            ["propose", "--provider-instance-id", "codex", "--model", "gpt-6-astra"],
            snapshot=capability_snapshot(),
            raw_policy=raw,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(content, raw)

    def test_propose_malformed_snapshot_model_fails_cleanly(self):
        snapshot = capability_snapshot()
        snapshot["providers"][0]["models"] = ["gpt-6-astra"]
        completed, _ = self.run_cli(
            ["propose", "--provider-instance-id", "codex", "--model", "gpt-6-astra"],
            snapshot=snapshot,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("error", completed.stderr.lower())
        self.assertNotIn("Traceback", completed.stderr)

    def test_propose_reads_stdin_snapshot(self):
        with tempfile.TemporaryDirectory(prefix="pstack-policy-test-") as tmp:
            policy_path = Path(tmp) / "models.json"
            policy_path.write_text(json.dumps(pool_policy()), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--policy",
                    str(policy_path),
                    "--snapshot",
                    "-",
                    "propose",
                    "--provider-instance-id",
                    "codex",
                    "--model",
                    "gpt-6-astra",
                ],
                input=json.dumps(capability_snapshot()),
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["model"], "gpt-6-astra")


if __name__ == "__main__":
    unittest.main()
