import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "build_map.py"
GIT = shutil.which("git")


def _load():
    spec = importlib.util.spec_from_file_location("gx_build_map_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(root, relative, text):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _user_controller(endpoints):
    methods = "".join(
        f'\n    @GetMapping("/{name}")\n    public String {name}() {{\n        return userService.list();\n    }}\n'
        for name in endpoints
    )
    return (
        'package com.sqi.user.controller;\n\n@RestController\n@RequestMapping("/api/users")\n'
        f"public class UserController {{\n    private final UserService userService;\n{methods}}}\n"
    )


def _project(root, user_endpoints=("list", "detail")):
    """user(컨트롤러·서비스·매퍼·XML → TB_USER)와 code(컨트롤러·서비스) 두 도메인."""
    _write(root, "src/main/java/com/sqi/user/controller/UserController.java", _user_controller(user_endpoints))
    _write(root, "src/main/java/com/sqi/user/service/UserService.java", textwrap.dedent("""\
        package com.sqi.user.service;

        @Service
        public class UserService {
            private final UserMapper userMapper;

            public String list() {
                return userMapper.list();
            }
        }
        """))
    _write(root, "src/main/java/com/sqi/user/mapper/UserMapper.java", textwrap.dedent("""\
        package com.sqi.user.mapper;

        @Mapper
        public interface UserMapper {
            String list();
        }
        """))
    _write(root, "src/main/resources/mapper/user/UserMapper.xml", textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <mapper namespace="com.sqi.user.mapper.UserMapper">
            <select id="list">SELECT USER_ID FROM TB_USER</select>
        </mapper>
        """))
    _write(root, "src/main/java/com/sqi/code/controller/CodeController.java", textwrap.dedent("""\
        package com.sqi.code.controller;

        @RestController
        public class CodeController {
            private final CodeService codeService;

            @GetMapping("/api/codes")
            public String codes() {
                return codeService.codes();
            }
        }
        """))
    _write(root, "src/main/java/com/sqi/code/service/CodeService.java", textwrap.dedent("""\
        package com.sqi.code.service;

        @Service
        public class CodeService {
            public String codes() {
                return "";
            }
        }
        """))


def _git(root, *args):
    subprocess.run(
        [
            "git", "-c", "user.name=gx", "-c", "user.email=gx@example.com",
            "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args,
        ],
        cwd=root, check=True, capture_output=True,
    )


def _fake_archify(root, validation_exit=0):
    script = Path(root) / "fake_archify.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import pathlib
            import sys

            phase = sys.argv[1]
            if phase == "doctor":
                raise SystemExit(0)
            if phase == "validate":
                print("validated")
                raise SystemExit({validation_exit})
            if phase == "deliver":
                output = pathlib.Path(sys.argv[-2])
                output.write_text('<html lang="ko"><body>Archify 결과</body></html>', encoding="utf-8")
                raise SystemExit(0)
            raise SystemExit(64)
            """
        ).strip() + "\n",
        encoding="utf-8",
    )
    return [sys.executable, str(script)]


class BuildMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.root = self.work / "project"
        self.map_dir = self.work / "map"
        self.command = _fake_archify(self.work)

    def build(self, **kwargs):
        return self.module.build_map(self.root, self.map_dir, archify_command=self.command, **kwargs)

    def read(self, relative):
        return (self.map_dir / relative).read_text(encoding="utf-8")

    def test_builds_index_and_one_page_per_domain(self):
        _project(self.root)
        report = self.build()
        self.assertEqual(report["validation_status"], "verified")
        self.assertEqual([entry["domain"] for entry in report["domains"]], ["code", "user"])
        self.assertTrue(report["index_path"].endswith("아키텍처-맵.html"))
        for relative in ("아키텍처-맵.html", "domains/user.html", "domains/code.html",
                         "ir/user.ir.json", "receipts/user.receipt.json"):
            self.assertTrue((self.map_dir / relative).is_file(), relative)
        self.assertIsNone(report["changes"])
        self.assertEqual(report["cross_domain_edge_count"], 0)

    def test_archify_failure_falls_back_to_a_drawn_mermaid_and_keeps_the_fallback_receipt(self):
        _project(self.root)
        self.command = _fake_archify(self.work, validation_exit=1)
        assets = self.map_dir / "assets"
        assets.mkdir(parents=True)
        (assets / "mermaid.min.js").write_bytes(b"/*mermaid*/" + b" " * 600_000)  # 다운로드 없이 확보된 상태
        report = self.build()
        self.assertEqual(report["validation_status"], "fallback")
        self.assertEqual({entry["backend"] for entry in report["domains"]}, {"mermaid"})
        self.assertTrue(report["mermaid_asset"]["available"])
        html_text = self.read("domains/user.html")
        self.assertIn('<pre class="mermaid">', html_text)
        self.assertIn("../assets/mermaid.min.js", html_text)
        receipt = json.loads(self.read("receipts/user.receipt.json"))
        self.assertEqual(receipt["status"], "fallback")
        self.assertIn("failed", [attempt["status"] for attempt in receipt["attempts"] if attempt["backend"] == "archify"])
        self.assertIn("폴백", self.read("아키텍처-맵.html"))

    def test_empty_project_fails_without_writing_ir(self):
        self.root.mkdir()
        report = self.build()
        self.assertEqual(report["validation_status"], "failed")
        self.assertEqual(report["missing_inputs"], ["entrypoint-scan"])
        self.assertIsNone(report["index_path"])
        self.assertFalse((self.map_dir / "ir").exists())

    def test_unknown_domain_fails_and_lists_found_domains(self):
        _project(self.root)
        report = self.build(domain="nope")
        self.assertEqual(report["validation_status"], "failed")
        self.assertIn("code, user", report["reason"])

    def test_single_domain_run_keeps_other_domains(self):
        _project(self.root)
        self.build()
        report = self.build(domain="user")
        self.assertEqual([entry["domain"] for entry in report["domains"]], ["user"])
        self.assertTrue((self.map_dir / "domains" / "code.html").is_file())

    def test_stale_domain_outputs_are_removed_on_full_run(self):
        _project(self.root)
        for relative in ("ir/old.ir.json", "domains/old.html", "receipts/old.receipt.json"):
            _write(self.map_dir, relative, "{}")
        self.build()
        for relative in ("ir/old.ir.json", "domains/old.html", "receipts/old.receipt.json"):
            self.assertFalse((self.map_dir / relative).exists(), relative)
        self.assertNotIn("<h3>old</h3>", self.read("아키텍처-맵.html"))

    def test_rerun_is_stable(self):
        _project(self.root)
        first = self.build()
        first_ir = self.read("ir/user.ir.json")
        second = self.build()
        self.assertEqual(self.read("ir/user.ir.json"), first_ir)
        self.assertEqual(
            [(entry["domain"], entry["backend"]) for entry in first["domains"]],
            [(entry["domain"], entry["backend"]) for entry in second["domains"]],
        )

    def test_labels_apply_only_on_exact_match(self):
        _project(self.root)
        report = self.build(labels={"UserService": "사용자 서비스", "User": "지어낸 라벨"})
        self.assertEqual(report["labels_applied"], 1)
        nodes = json.loads(self.read("ir/user.ir.json"))["nodes"]
        service = next(node for node in nodes if node["label"] == "사용자 서비스")
        self.assertEqual(service["technical_label"], "UserService")
        self.assertNotIn("지어낸 라벨", [node["label"] for node in nodes])

    def test_changed_since_outside_git_still_builds_the_map(self):
        _project(self.root)
        report = self.build(changed_since="main")
        self.assertEqual(report["validation_status"], "verified")
        self.assertFalse(report["changes"]["available"])
        self.assertIn("변경 표시를 생략했습니다", self.read("아키텍처-맵.html"))

    @unittest.skipUnless(GIT, "git not available on PATH")
    def test_changed_since_marks_a_new_endpoint_end_to_end(self):
        _project(self.root, user_endpoints=("list",))
        _git(self.root, "init", "-q")
        _git(self.root, "symbolic-ref", "HEAD", "refs/heads/main")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "base")
        _git(self.root, "checkout", "-q", "-b", "feature")
        _write(self.root, "src/main/java/com/sqi/user/controller/UserController.java", _user_controller(("list", "detail")))
        _git(self.root, "commit", "-q", "-am", "detail 추가")

        report = self.build(changed_since="main")

        self.assertTrue(report["changes"]["available"])
        self.assertEqual(report["changes"]["added"], 1)
        user = next(entry for entry in report["domains"] if entry["domain"] == "user")
        self.assertEqual((user["added"], user["changed"]), (1, 0))
        nodes = json.loads(self.read("ir/user.ir.json"))["nodes"]
        self.assertEqual(next(node for node in nodes if node["label"] == "UserController.detail")["change"], "added")
        self.assertIn("기준 main (", self.read("domains/user.html"))
        self.assertIn("신규 1개", self.read("domains/user.html"))
        self.assertIn("구조 변경이 없습니다", self.read("domains/code.html"))
        self.assertIn('id="changes-title"', self.read("아키텍처-맵.html"))

    @unittest.skipUnless(GIT, "git not available on PATH")
    def test_labels_do_not_turn_into_changes(self):
        # Review Focus 3: 라벨을 먼저 붙이면 technical_label이 기준 스캔과 달라져 전부 "변경"이 된다.
        _project(self.root)
        _git(self.root, "init", "-q")
        _git(self.root, "symbolic-ref", "HEAD", "refs/heads/main")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "base")
        report = self.build(changed_since="main", labels={"UserService": "사용자 서비스"})
        self.assertEqual(report["labels_applied"], 1)
        self.assertEqual((report["changes"]["added"], report["changes"]["changed"]), (0, 0))

    def test_cli_prints_json_report_and_exit_code(self):
        report = {"view": "service", "validation_status": "failed", "domains": [], "reason": "없음 — 테스트"}
        with mock.patch.object(self.module, "build_map", return_value=report) as build, \
                mock.patch.object(sys, "argv", ["build_map.py", "some/root", "--changed-since", "main"]), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = self.module.main()
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["reason"], "없음 — 테스트")
        self.assertEqual(build.call_args.args[2], "main")

    def test_cli_rejects_labels_that_are_not_an_object(self):
        labels = self.work / "labels.json"
        labels.write_text("[1, 2]", encoding="utf-8")
        with mock.patch.object(sys, "argv", ["build_map.py", str(self.work), "--labels", str(labels)]), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self.module.main()
        self.assertEqual(raised.exception.code, 2)

    def test_archify_discovery_runs_once_per_run_not_once_per_domain(self):
        # 2026-09-28 최종 리뷰 I1: archify_command를 생략(기본 경로)하면 도메인 루프
        # 전에 ensure_archify()를 한 번만 부르고, 그 결과를 모든 도메인이 공유한다.
        _project(self.root)
        assets = self.map_dir / "assets"
        assets.mkdir(parents=True)
        (assets / "mermaid.min.js").write_bytes(b"/*mermaid*/" + b" " * 600_000)  # 다운로드 없이 확보된 상태
        blocked = {
            "available": False,
            "command": None,
            "attempts": [{"phase": "install", "command": ["npx"], "exit_code": 1, "stderr": "blocked"}],
        }
        with mock.patch.object(self.module.backend_detector, "ensure_archify", return_value=blocked) as ensure:
            report = self.module.build_map(self.root, self.map_dir)
        ensure.assert_called_once()
        self.assertEqual({entry["domain"] for entry in report["domains"]}, {"code", "user"})
        for entry in report["domains"]:
            self.assertNotEqual(entry["backend"], "archify")
            receipt = json.loads((self.map_dir / "receipts" / f"{entry['domain']}.receipt.json").read_text(encoding="utf-8"))
            self.assertIn("archify-discovery", [attempt["backend"] for attempt in receipt["attempts"]])


if __name__ == "__main__":
    unittest.main()
