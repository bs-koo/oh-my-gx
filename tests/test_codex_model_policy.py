import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from codex_test_support import ROOT, load


policy = load("gx_model_policy", "scripts/codex-model-policy.py")


class ModelPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.capabilities = {
            "models": {
                "gpt-6-astra": ["medium", "high", "xhigh"],
                "gpt-6.1-sol": ["medium", "high"],
            },
            "parent_model": "gpt-6-astra", "parent_reasoning_effort": "xhigh",
        }

    def resolve(self, role="reviewer", **kwargs):
        inputs = {"capabilities": self.capabilities, "cwd": self.project,
                  "pipeline": "gx-tdd", "role": role}
        inputs.update(kwargs)
        return policy.resolve_policy(**inputs)

    def config(self, value):
        path = self.project / ".claude/config.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_complete_role_matrix_uses_installed_tiers_and_pipeline_eco_rules(self):
        expected_base = {
            "architect": "high", "coder": "high", "design-critic": "high",
            "green-coder": "mid", "hacker": "mid", "humanizer-fidelity": "high",
            "humanizer-naturalness": "high", "implementer": "mid", "product-owner": "mid",
            "qa-manager": "mid", "red-writer": "mid", "refactor-coder": "mid",
            "researcher": "mid", "reviewer": "high", "security-auditor": "mid",
            "simplifier": "mid", "test-architect": "high",
        }
        self.assertEqual(set(expected_base), set(policy.read_object(ROOT / policy.ROLE_INDEX)))
        targets = {"gx-dev": {"coder", "design-critic"},
                   "gx-tdd": {"design-critic", "test-architect", "reviewer"},
                   "standalone": set()}
        for pipeline, eco_roles in targets.items():
            for profile in ("standard", "eco"):
                for role, base in expected_base.items():
                    with self.subTest(pipeline=pipeline, profile=profile, role=role):
                        tier = "mid" if profile == "eco" and role in eco_roles else base
                        result = self.resolve(role, pipeline=pipeline, profile=profile)
                        self.assertEqual((result["base_tier"], result["effective_tier"]), (base, tier))
                        self.assertEqual((result["model"], result["reasoning_effort"]),
                                         ("gpt-6-astra", "high") if tier == "high" else ("gpt-6.1-sol", "medium"))

    def test_architect_preserves_high_in_both_eco_pipelines(self):
        for pipeline in ("gx-dev", "gx-tdd"):
            self.assertEqual(self.resolve("architect", pipeline=pipeline, profile="eco")["effective_tier"], "high")

    def test_task_reviewer_is_mid_in_standard_and_eco(self):
        for profile in ("standard", "eco"):
            result = self.resolve(profile=profile, scope="task")
            self.assertEqual(result["base_tier"], "high")
            self.assertEqual(result["effective_tier"], "mid")
        self.assertEqual(self.resolve(scope="phase")["effective_tier"], "high")
        self.assertEqual(self.resolve(pipeline="standalone", scope="task")["effective_tier"], "high")

    def test_implementer_fix_rounds_four_and_five_escalate_independently_of_eco(self):
        for profile in ("standard", "eco"):
            for round_number in range(6):
                with self.subTest(profile=profile, fix_round=round_number):
                    result = self.resolve("implementer", profile=profile, fix_round=round_number)
                    self.assertEqual(result["effective_tier"], "high" if round_number >= 4 else "mid")
        self.assertEqual(self.resolve("implementer", pipeline="standalone", fix_round=5)["effective_tier"], "mid")
        self.assertEqual(self.resolve("red-writer", fix_round=5)["effective_tier"], "mid")

    def test_escalated_implementer_cannot_claim_high_dispatch_while_using_parent_session(self):
        for profile in ("standard", "eco"):
            for round_number in (4, 5):
                with self.subTest(profile=profile, round_number=round_number), self.assertRaisesRegex(ValueError, "fresh agent"):
                    self.resolve("implementer", profile=profile, fix_round=round_number, execution="session")
        self.assertEqual(self.resolve("implementer", fix_round=3, execution="session")["source"], "parent-session")

    def test_scope_and_fix_round_do_not_change_unrelated_role_tiers(self):
        for profile in ("standard", "eco"):
            self.assertEqual(self.resolve("architect", scope="task", profile=profile, fix_round=5)["effective_tier"], "high")
            self.assertEqual(self.resolve("reviewer", scope="task", profile=profile, fix_round=5)["effective_tier"], "mid")
            self.assertEqual(self.resolve("red-writer", scope="task", profile=profile, fix_round=5)["effective_tier"], "mid")

    def test_override_selects_supported_custom_model_and_effort_without_writing_config(self):
        path = self.config({"vcs": "git", "codex": {"modelTiers": {
            "mid": {"model": "team-sol", "reasoning_effort": "low"}}}})
        before = path.read_bytes()
        self.capabilities["models"]["team-sol"] = ["low"]
        result = self.resolve("implementer")
        self.assertEqual((result["model"], result["reasoning_effort"], result["source"]),
                         ("team-sol", "low", "project-config"))
        self.assertEqual(self.resolve("architect")["source"], "default")
        self.assertEqual(path.read_bytes(), before)

    def test_unsupported_override_falls_back_with_explicit_config_reason(self):
        self.config({"codex": {"modelTiers": {"high": {"model": "unavailable", "reasoning_effort": "high"}}}})
        result = self.resolve()
        self.assertEqual((result["model"], result["source"]), ("gpt-6-astra", "fallback"))
        self.assertIn("project-config", result["reason"])
        self.assertIn("unavailable/high", result["reason"])

    def test_candidate_effort_must_be_allowed_and_effort_is_never_silently_downgraded(self):
        self.capabilities["models"] = {"gpt-6-astra": ["medium"], "gpt-6-sol": ["high"]}
        result = self.resolve("architect")
        self.assertEqual((result["model"], result["reasoning_effort"], result["source"]),
                         ("gpt-6-sol", "high", "fallback"))
        self.capabilities["models"] = {"gpt-6-astra": ["medium"]}
        with self.assertRaisesRegex(ValueError, "high"):
            self.resolve("architect")

    def test_mid_fallback_prefers_sol_variants_over_parent_astra(self):
        for available, expected in ((["gpt-6-sol", "gpt-5.6-sol"], "gpt-6-sol"),
                                    (["gpt-5.6-sol"], "gpt-5.6-sol")):
            self.capabilities["models"] = {name: ["medium"] for name in ["gpt-6-astra", *available]}
            result = self.resolve("implementer", profile="eco")
            self.assertEqual(result["model"], expected)

    def test_shared_allowed_model_can_distinguish_tiers_by_effort(self):
        self.capabilities["models"] = {"gpt-6-astra": ["high", "medium"]}
        high = self.resolve("architect", profile="eco")
        mid = self.resolve("implementer", profile="eco")
        self.assertEqual(high["model"], mid["model"])
        self.assertEqual((high["reasoning_effort"], mid["reasoning_effort"]), ("high", "medium"))

    def test_other_allowed_fallback_is_deterministic_and_prefers_allowed_parent(self):
        self.capabilities["models"] = {"z-model": ["high"], "a-model": ["high"]}
        self.capabilities["parent_model"] = "z-model"
        self.assertEqual(self.resolve()["model"], "z-model")
        self.capabilities["parent_model"] = "unlisted-model"
        self.assertEqual(self.resolve()["model"], "a-model")

    def test_empty_allowlist_or_empty_effort_support_blocks_new_dispatch(self):
        for models in ({}, {"gpt-6-astra": []}):
            self.capabilities["models"] = models
            with self.assertRaisesRegex(ValueError, "허용 모델"):
                self.resolve()

    def test_same_override_pair_reports_loss_of_tier_distinction(self):
        pair = {"model": "gpt-6-astra", "reasoning_effort": "high"}
        self.config({"codex": {"modelTiers": {"high": pair, "mid": pair}}})
        result = self.resolve("implementer", profile="eco")
        self.assertEqual(len(result["warnings"]), 1)
        self.assertIn("high/mid", result["warnings"][0])

    def test_distinct_override_candidates_that_fall_back_to_same_pair_report_collapse(self):
        self.config({"codex": {"modelTiers": {
            "high": {"model": "unavailable-high", "reasoning_effort": "high"},
            "mid": {"model": "unavailable-mid", "reasoning_effort": "high"},
        }}})
        self.capabilities["models"] = {"shared-model": ["high"]}
        for role in ("architect", "implementer"):
            with self.subTest(role=role):
                result = self.resolve(role)
                self.assertEqual((result["model"], result["reasoning_effort"]), ("shared-model", "high"))
                self.assertIn("high/mid", result["warnings"][0])

    def test_unsupported_other_tier_does_not_block_current_dispatch(self):
        self.capabilities["models"] = {"gpt-6-astra": ["high"]}
        result = self.resolve("architect")
        self.assertEqual((result["model"], result["reasoning_effort"]), ("gpt-6-astra", "high"))
        self.assertEqual(result["warnings"], [])

    def test_session_returns_parent_even_outside_child_allowlist_and_does_not_spawn(self):
        self.capabilities["models"] = {}
        self.capabilities["parent_model"] = "current-parent-only"
        result = self.resolve("implementer", execution="session", profile="eco")
        self.assertEqual((result["model"], result["reasoning_effort"], result["source"]),
                         ("current-parent-only", "xhigh", "parent-session"))
        self.assertEqual(result["effective_tier"], "mid")
        self.assertIn("eco로 변경되지 않음", result["reason"])
        self.assertIsNone(result["spawn_args"])
        self.assertIsNone(result["fork_turns"])

    def test_session_requires_actual_parent_model_and_effort(self):
        for field in ("parent_model", "parent_reasoning_effort"):
            for value in (None, "", ["high"]):
                caps = dict(self.capabilities, **{field: value})
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.resolve(execution="session", capabilities=caps)

    def test_spawn_arguments_keep_red_isolated_and_do_not_bind_harness_roles(self):
        result = self.resolve("red-writer")
        self.assertEqual(result["spawn_args"], {
            "model": "gpt-6.1-sol", "reasoning_effort": "medium", "fork_turns": "none"})
        self.assertNotIn("agent_type", result)
        self.assertNotIn("agent_type", result["spawn_args"])

    def test_consumer_index_cannot_override_installed_role_tier(self):
        fake = self.project / policy.ROLE_INDEX
        fake.parent.mkdir(parents=True)
        fake.write_text('{"architect":{"tier":"mid"}}', encoding="utf-8")
        self.assertEqual(self.resolve("architect")["base_tier"], "high")

    def test_unknown_role_and_invalid_contract_values_fail(self):
        for kwargs in ({"role": "not-a-gx-role"}, {"pipeline": "other"}, {"profile": "cheap"},
                       {"scope": "other"}, {"execution": "other"}, {"fix_round": -1},
                       {"fix_round": 6}, {"fix_round": True}, {"cwd": self.project / "missing"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.resolve(**kwargs)

    def test_invalid_capabilities_fail_without_guessing_permissions(self):
        for models in (None, [], {"gpt-6-astra": "high"}, {"gpt-6-astra": [None]},
                       {"gpt-6-astra": [""]}, {"": ["high"]}):
            with self.subTest(models=models), self.assertRaises(ValueError):
                self.resolve(capabilities={"models": models})

    def test_invalid_configuration_fails_instead_of_silently_using_defaults(self):
        for value in ([], {"codex": None}, {"codex": {"modelTiers": []}},
                      {"codex": {"modelTiers": {"typo": {}}}},
                      {"codex": {"modelTiers": {"mid": {"model": "x"}}}},
                      {"codex": {"modelTiers": {"high": {"model": "", "reasoning_effort": "high"}}}}):
            with self.subTest(value=value):
                self.config(value)
                with self.assertRaises(ValueError):
                    self.resolve()

    def cli(self, *extra, script=None):
        caps = self.project / "capabilities.json"
        caps.write_text(json.dumps(self.capabilities), encoding="utf-8")
        return subprocess.run([sys.executable, str(script or ROOT / "scripts/codex-model-policy.py"),
                               "--capabilities", str(caps), "--cwd", str(self.project),
                               "--pipeline", "gx-tdd", "--role", "implementer", *extra],
                              cwd=self.project, capture_output=True, text=True, encoding="utf-8")

    def test_cli_json_success_and_policy_failure_exit_two(self):
        result = self.cli("--profile", "eco", "--fix-round", "4")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["effective_tier"], "high")
        self.capabilities["models"] = {}
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("error", json.loads(result.stdout))
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_argument_errors_return_json_and_exit_two(self):
        for args in (("--profile", "wrong"), ("--fix-round", "6"), ("--fix-round", "nan")):
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("error", json.loads(result.stdout))

    def test_cli_relocated_install_uses_its_own_index(self):
        install = self.project / "installed-plugin"
        script = install / "scripts/codex-model-policy.py"
        script.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "scripts/codex-model-policy.py", script)
        index = install / policy.ROLE_INDEX
        index.parent.mkdir(parents=True)
        index.write_text('{"implementer":{"tier":"high"}}', encoding="utf-8")
        result = self.cli(script=script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["base_tier"], "high")
        for tier in ("unknown", None, [], {}):
            with self.subTest(tier=tier):
                index.write_text(json.dumps({"implementer": {"tier": tier}}), encoding="utf-8")
                result = self.cli(script=script)
                self.assertEqual(result.returncode, 2)
                self.assertIn("error", json.loads(result.stdout))

    def test_cli_invalid_config_and_missing_index_are_json_failures(self):
        path = self.config({})
        path.write_text("{invalid-json", encoding="utf-8")
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("error", json.loads(result.stdout))
        with self.assertRaises(OSError):
            self.resolve(plugin_root=self.project / "no-install")


if __name__ == "__main__":
    unittest.main()
