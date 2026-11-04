# Test selection and evidence validation

Owner: test-efficiency implementation subagent. No full repository suite executed during iteration; final required aggregate checks are the parent agent's responsibility.

## RED evidence

- `python -m unittest discover -s tests -p test_gx_test_plan.py -v`: initial behavior assertions failed because `scripts/gx-test-plan.py` did not exist (14 assertion failures; one test utility naming collision also identified and corrected).
- Ownership-file test: failed because `--ownership-file` was unsupported before implementation.
- Shared contract test: failed because review/verify did not reference `test-execution.md` and still prohibited all same-run reuse.
- Explicit full request test: failed because `--full` was unsupported.
- Selection edge tests: empty mapping incorrectly returned no test command; unsupported Java template retained `{pattern}`; built-in related runner mixed required test paths with source paths. Each failed against the previous implementation before correction.
- Gradle cache refresh test: failed because `--rerun-tests` was unsupported.

## GREEN evidence

- Behavior group: 12 tests passed in 269.962 seconds on Windows, including per-project mappings, multi-project fallback, dependency/crosscutting fallback, known Vitest related mode, missing mapped test fallback, Gradle build conversion, same-run proof reuse, changed fingerprint/config/command/scope/log rejection, and failure/zero/unconfirmed count rejection.
- Explicit full request: 1 passed in 10.092 seconds.
- Selection edges: 3 passed in 0.105 seconds after targeted fixes.
- Gradle cache refresh: 1 passed in 15.387 seconds; only Gradle test command receives `--rerun-tasks`, Node command stays unchanged.
- Shared contract after final documentation updates: 1 passed in 0.658 seconds.

This was the owner's initial 18-test handoff. The final file contains 31 tests after the parent's selection edge cases and six current-task focused cases; the composite final results are in verification.md. The helper never runs generated shell commands. Automated fixtures validate planning/proof matching, not an authenticated Codex session or a real consumer build.
