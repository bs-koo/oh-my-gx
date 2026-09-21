import importlib.util
import json
import os
import shutil
import stat
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "render_archify.py"
TO_ARCHIFY = REPO / ".claude" / "skills" / "gx-visualize" / "scripts" / "to_archify.py"

REQUIRED_TOP_LEVEL = {"schema_version", "diagram_type", "meta", "components"}
NODE_KEY = "components"
EDGE_KEY = "connections"

TEST_REPOSITORY = {
    "url": "https://github.com/example/repo.git",
    "revision": "a" * 40,
    "link_mode": "local-only",
}

KIND_TO_TYPE_AND_COL = {
    "screen": ("frontend", 0),
    "api": ("backend", 1),
    "service": ("backend", 2),
    "repository": ("backend", 3),
    "table": ("database", 4),
}


TRACE_IR = {
    "schema_version": 1,
    "view": "trace",
    "locale": "ko-KR",
    "title": "추적 맵",
    "nodes": [{"id": "n1", "kind": "requirement", "label": "요구사항", "status": "verified", "evidence": []}],
    "edges": [],
}

SEQUENCE_IR = {
    "schema_version": 1,
    "view": "sequence",
    "locale": "ko-KR",
    "title": "호출 순서",
    "nodes": [{"id": "n1", "kind": "participant", "label": "클라이언트", "status": "verified", "evidence": []}],
    "edges": [],
}


def _single_node_ir(kind: str) -> dict:
    return {
        "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
        "nodes": [{"id": "n", "kind": kind, "label": "라벨", "evidence": []}],
        "edges": [],
    }


def _ir_with_label(label: str, technical: str | None = None) -> dict:
    node: dict = {"id": "n", "kind": "api", "label": label, "evidence": []}
    if technical is not None:
        node["technical_label"] = technical
    return {
        "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
        "nodes": [node],
        "edges": [],
    }


def _text_units(text: str) -> int:
    # render-architecture.mjs가 위임하는 renderers/shared/utils.mjs의 textUnits()를
    # 독립적으로 재현한 테스트 전용 계측기다 — 한글 등 전각 문자는 2, 그 외는 1.
    units = 0
    for ch in text:
        codepoint = ord(ch)
        units += 2 if 0xAC00 <= codepoint <= 0xD7A3 or 0x1100 <= codepoint <= 0x115F else 1
    return units


LINEAR_CHAIN_IR = {
    "schema_version": 1,
    "view": "service",
    "locale": "ko-KR",
    "title": "체인",
    "nodes": [
        {"id": "c-screen", "kind": "screen", "label": "화면", "evidence": []},
        {"id": "c-api", "kind": "api", "label": "API", "evidence": []},
        {"id": "c-service", "kind": "service", "label": "서비스", "evidence": []},
        {"id": "c-repo", "kind": "repository", "label": "저장소", "evidence": []},
        {"id": "c-table", "kind": "table", "label": "테이블", "evidence": []},
    ],
    "edges": [
        {"id": "e1", "source": "c-screen", "target": "c-api", "relation": "requests"},
        {"id": "e2", "source": "c-api", "target": "c-service", "relation": "calls"},
        {"id": "e3", "source": "c-service", "target": "c-repo", "relation": "calls"},
        {"id": "e4", "source": "c-repo", "target": "c-table", "relation": "reads"},
    ],
}

# id 알파벳 순서와 실제 연결이 어긋나도록 일부러 엇갈리게 짠 두 갈래 체인이다:
# s-alpha -> a-zulu, s-zulu -> a-alpha. id로만 행을 매기면(과거 버그) 잘못 짝지어진다 —
# 연결의 source 행을 따라가야만 s-alpha/a-zulu가, s-zulu/a-alpha가 각각 같은 행에 놓인다.
CROSSED_CHAINS_IR = {
    "schema_version": 1,
    "view": "service",
    "locale": "ko-KR",
    "title": "교차 체인",
    "nodes": [
        {"id": "s-alpha", "kind": "screen", "label": "화면A", "evidence": []},
        {"id": "s-zulu", "kind": "screen", "label": "화면Z", "evidence": []},
        {"id": "a-alpha", "kind": "api", "label": "APIA", "evidence": []},
        {"id": "a-zulu", "kind": "api", "label": "APIZ", "evidence": []},
    ],
    "edges": [
        {"id": "e-a", "source": "s-alpha", "target": "a-zulu", "relation": "requests"},
        {"id": "e-b", "source": "s-zulu", "target": "a-alpha", "relation": "requests"},
    ],
}

def _ir_same_layer_chain() -> dict:
    # service -> service, repository -> repository는 실제로 존재한다(설계서 5.7.1,
    # 실측: RefreshTokenRepository -> RefreshTokenMapper). 같은 열에 놓이므로
    # KIND_TO_COL만으로는 방향을 구분할 수 없다.
    return {
        "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
        "nodes": [
            {"id": "svc-a", "kind": "service", "label": "서비스A", "evidence": []},
            {"id": "svc-b", "kind": "service", "label": "서비스B", "evidence": []},
        ],
        "edges": [{"id": "e1", "source": "svc-a", "target": "svc-b", "relation": "calls"}],
    }


def _ir_normal_chain() -> dict:
    return {
        "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
        "nodes": [
            {"id": "api-a", "kind": "api", "label": "API", "evidence": []},
            {"id": "svc-a", "kind": "service", "label": "서비스", "evidence": []},
        ],
        "edges": [{"id": "e1", "source": "api-a", "target": "svc-a", "relation": "calls"}],
    }


VALID_IR = {
    "schema_version": 1,
    "view": "service",
    "locale": "ko-KR",
    "title": "서비스 구조",
    "nodes": [
        {"id": "n1", "kind": "api", "label": "로그인", "status": "unknown",
         "evidence": [{"kind": "code", "file": "a.java", "line": 1}]}
    ],
    "edges": [],
}


def _module():
    spec = importlib.util.spec_from_file_location("gx_render_archify", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _converter():
    spec = importlib.util.spec_from_file_location("gx_to_archify", TO_ARCHIFY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_archify(directory: Path) -> Path:
    """Record argv to argv.log; succeed validate but fail deliver so the adapter falls back.

    render_archify() short-circuits to fallback as soon as validate fails, so a fake
    that always exits 1 would never invoke deliver and argv.log would only ever gain
    one line. Phase-aware exit codes let both commands run and be recorded.
    """
    script = directory / "fake_archify.py"
    script.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "log = Path(__file__).with_name('argv.log')\n"
        "with log.open('a', encoding='utf-8') as handle:\n"
        "    handle.write(json.dumps(sys.argv[1:], ensure_ascii=False) + '\\n')\n"
        "sys.exit(0 if sys.argv[1] == 'validate' else 1)\n",
        encoding="utf-8",
    )
    return script


def _init_git_repo(root: Path, origin: str | None = None) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "a.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "a.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)
    if origin is not None:
        subprocess.run(["git", "remote", "add", "origin", origin], cwd=root, check=True)


class ArchifyCommandTests(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_service_view_maps_to_architecture_diagram_type(self):
        self.assertEqual("architecture", self.m.diagram_type("service"))

    def test_sequence_view_has_no_diagram_type(self):
        # sequence는 archify participants/messages 변환기가 없다 — 이 계획 범위 밖으로
        # 미뤄졌으므로(리뷰 라운드 1), architecture 문서를 잘못 보내지 않도록 None을 반환한다.
        self.assertIsNone(self.m.diagram_type("sequence"))

    def test_non_service_or_sequence_views_have_no_diagram_type(self):
        # Archify는 service만 실제로 지원한다 — 나머지 뷰는 애초에 시도 대상이 아니다.
        for view in ("trace", "progress", "impact"):
            self.assertIsNone(self.m.diagram_type(view))

    def test_non_service_view_skips_archify_subprocess_entirely(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ir_path = root / "trace.json"
            ir_path.write_text(json.dumps(TRACE_IR, ensure_ascii=False), encoding="utf-8")
            fake = _fake_archify(root)
            out = root / "out"
            self.m.render_archify(ir_path, out, ["python", str(fake)], project_root=root)

            # fake_archify.py는 실행될 때만 argv.log를 만든다 — 파일이 없다는 것 자체가
            # subprocess가 한 번도 뜨지 않았다는 증거다.
            self.assertFalse((root / "argv.log").exists())

            receipt = json.loads((out / "trace.receipt.json").read_text(encoding="utf-8"))
            self.assertEqual("not_applicable", receipt["status"])
            self.assertEqual("not_applicable", receipt["attempts"][0]["status"])
            self.assertIsNone(receipt["attempts"][0]["command"])

    def test_sequence_view_skips_archify_subprocess_entirely(self):
        # sequence도 diagram_type()이 None이므로 trace와 같은 skip 경로를 탄다 —
        # archify가 이해 못 하는 architecture 문서를 보내 두 번 실패시키지 않는다.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ir_path = root / "sequence.json"
            ir_path.write_text(json.dumps(SEQUENCE_IR, ensure_ascii=False), encoding="utf-8")
            fake = _fake_archify(root)
            out = root / "out"
            self.m.render_archify(ir_path, out, ["python", str(fake)], project_root=root)

            self.assertFalse((root / "argv.log").exists())
            receipt = json.loads((out / "sequence.receipt.json").read_text(encoding="utf-8"))
            self.assertEqual("not_applicable", receipt["status"])

    def test_validate_and_deliver_use_real_archify_signature(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.java").write_text("class A {}", encoding="utf-8")
            ir_path = root / "service.json"
            ir_path.write_text(json.dumps(VALID_IR, ensure_ascii=False), encoding="utf-8")
            fake = _fake_archify(root)
            out = root / "out"
            self.m.render_archify(ir_path, out, ["python", str(fake)], project_root=root)

            # root is a plain tmp dir (not a git checkout), so no repository evidence is
            # available and the payload carries no --repo-root flag (see to_archify.py).
            archify_payload = out / "service.archify.json"
            calls = [json.loads(line) for line in (root / "argv.log").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(["validate", "architecture", str(archify_payload), "--json"], calls[0])
            self.assertEqual(
                ["deliver", "architecture", str(archify_payload), str(out / "service.html"), "--json"], calls[1]
            )

    def test_failed_archify_still_produces_fallback_html(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.java").write_text("class A {}", encoding="utf-8")
            ir_path = root / "service.json"
            ir_path.write_text(json.dumps(VALID_IR, ensure_ascii=False), encoding="utf-8")
            out = root / "out"
            result = self.m.render_archify(ir_path, out, ["python", str(_fake_archify(root))], project_root=root)
            self.assertTrue(Path(result["html_path"]).is_file())
            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual("fallback", receipt["status"])
            self.assertNotEqual("archify", receipt["backend"])

    def test_git_absent_yields_no_repository_evidence(self):
        # subprocess.run 자체가 없는 환경(git 미설치)을 흉내낸다.
        with TemporaryDirectory() as tmp:
            with mock.patch.object(self.m.subprocess, "run", side_effect=FileNotFoundError):
                self.assertIsNone(self.m._git_repository_evidence(Path(tmp), ["a.java"]))

    def test_no_cited_paths_yields_no_repository_evidence(self):
        # 인용할 파일이 없으면 검증할 대상 자체가 없다 — git을 아예 조회하지 않는다.
        # (to_archify도 sources 없이 meta.repository만 싣는 문서는 만들지 않는다: Archify가
        # referenceCount 0인 repository 선언을 거부하기 때문이다.)
        with TemporaryDirectory() as tmp:
            with mock.patch.object(self.m.subprocess, "run") as run:
                self.assertIsNone(self.m._git_repository_evidence(Path(tmp), []))
                run.assert_not_called()

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_git_repo_without_origin_yields_no_repository_evidence(self):
        # origin이 없는 리포지토리(갓 init했거나 SVN에서 옮겨온 경우)도 sources 생략으로
        # 안전하게 떨어져야 한다 — 실측: origin 조회가 실패하면 repository=None.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root)
            self.assertIsNone(self.m._git_repository_evidence(root, ["a.txt"]))

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_git_repo_with_origin_yields_repository_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root, origin="https://github.com/example/repo.git")
            evidence = self.m._git_repository_evidence(root, ["a.txt"])
            self.assertEqual("https://github.com/example/repo.git", evidence["url"])
            self.assertRegex(evidence["revision"], r"^[0-9a-f]{40}$")
            self.assertEqual("local-only", evidence["link_mode"])

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_modified_cited_path_yields_no_repository_evidence(self):
        # 인용된 파일이 커밋 이후 수정됐으면 그 줄이 커밋 시점과 다를 수 있다 —
        # Archify는 커밋된 리비전만 검증하므로 잘못된 근거를 정직해 보이게 만들 위험이 있다.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root, origin="https://github.com/example/repo.git")
            (root / "a.txt").write_text("modified after commit", encoding="utf-8")
            self.assertIsNone(self.m._git_repository_evidence(root, ["a.txt"]))

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_dirt_outside_cited_paths_does_not_suppress_evidence(self):
        # 인용되지 않은 파일이 바뀌거나 새로 생겨도(gx-visualize 자신의 .dev/ 산출물처럼)
        # 인용된 파일이 클린하면 repository는 그대로 나와야 한다 — 리뷰 라운드 2의 핵심.
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root, origin="https://github.com/example/repo.git")
            (root / "a.txt").write_text("modified after commit", encoding="utf-8")  # not cited
            (root / "untracked.txt").write_text("new file", encoding="utf-8")  # not cited
            (root / "cited.java").write_text("class Cited {}", encoding="utf-8")
            subprocess.run(["git", "add", "cited.java"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "add cited file"], cwd=root, check=True)

            evidence = self.m._git_repository_evidence(root, ["cited.java"])
            self.assertIsNotNone(evidence)
            self.assertEqual("https://github.com/example/repo.git", evidence["url"])

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_repo_root_flag_is_passed_to_validate_and_deliver(self):
        # deliver_command에서 *repo_root_args를 지워도 통과하던 기존 테스트들은 전부
        # non-git tmpdir(플래그 부재)만 확인했다 — 여기서는 실제로 붙는 경우를 확인한다.
        # project_root(git 체크아웃)와 ir_path/출력 디렉터리를 분리해 --repo-root 부착
        # 자체를 dirty-tree 경로 스코프 로직과 무관하게 최소 형태로 pin한다. 실제 프로젝트
        # 모양(IR/출력이 같은 저장소 안)은 아래 test_repo_root_flag_survives_in_repo_output에서 확인한다.
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            project_root = tmp_root / "project"
            project_root.mkdir()
            _init_git_repo(project_root, origin="https://github.com/example/repo.git")
            (project_root / "a.java").write_text("class A {}", encoding="utf-8")
            subprocess.run(["git", "add", "a.java"], cwd=project_root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "add evidence"], cwd=project_root, check=True)

            work = tmp_root / "work"
            work.mkdir()
            ir_path = work / "service.json"
            ir_path.write_text(json.dumps(VALID_IR, ensure_ascii=False), encoding="utf-8")
            fake = _fake_archify(work)
            out = work / "out"
            self.m.render_archify(ir_path, out, ["python", str(fake)], project_root=project_root)

            calls = [json.loads(line) for line in (work / "argv.log").read_text(encoding="utf-8").splitlines()]
            self.assertIn("--repo-root", calls[0])
            self.assertEqual(str(project_root), calls[0][calls[0].index("--repo-root") + 1])
            self.assertIn("--repo-root", calls[1])

    @unittest.skipUnless(shutil.which("git"), "git not available on PATH")
    def test_repo_root_flag_survives_in_repo_output(self):
        # 실제 통합 모양: IR과 산출물이 프로젝트 저장소 안(.dev/{branch}/visual/ 같은 경로)에
        # 쓰인다. render_archify 자신이 만드는 fake_archify.py/argv.log/영수증/HTML은 인용된
        # 파일이 아니므로 dirty해도 무방해야 한다 — path scoping(리뷰 라운드 2)이 실제
        # 통합 경로에서도 동작하는지 여기서 확인한다 (라운드 1의 test_repo_root_flag_is_
        # passed_to_validate_and_deliver는 project_root와 출력을 분리한 최소 형태로 남겨둔다).
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            _init_git_repo(project_root, origin="https://github.com/example/repo.git")
            (project_root / "a.java").write_text("class A {}", encoding="utf-8")
            subprocess.run(["git", "add", "a.java"], cwd=project_root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "add evidence"], cwd=project_root, check=True)

            dev_dir = project_root / ".dev" / "feat-x" / "visual"
            dev_dir.mkdir(parents=True)
            ir_path = dev_dir / "service.json"
            ir_path.write_text(json.dumps(VALID_IR, ensure_ascii=False), encoding="utf-8")
            fake = _fake_archify(dev_dir)
            out = dev_dir / "out"
            self.m.render_archify(ir_path, out, ["python", str(fake)], project_root=project_root)

            calls = [json.loads(line) for line in (dev_dir / "argv.log").read_text(encoding="utf-8").splitlines()]
            self.assertIn("--repo-root", calls[0])
            self.assertIn("--repo-root", calls[1])

            payload = json.loads((out / "service.archify.json").read_text(encoding="utf-8"))
            self.assertEqual([{"path": "a.java", "line": 1}], payload["components"][0]["sources"])
            self.assertIn("repository", payload["meta"])

class ToArchifyTests(unittest.TestCase):
    def setUp(self):
        module = _converter()
        self.to_archify = module.to_archify
        self.cited_paths = module.cited_paths

    def test_output_carries_required_top_level_keys(self):
        # REQUIRED_TOP_LEVEL은 docs/reports/2026-09-18-archify-ir-schema.md에 기록한 실제 키 집합이다.
        from_schema = set(REQUIRED_TOP_LEVEL)
        self.assertTrue(from_schema.issubset(set(self.to_archify(VALID_IR, "architecture"))))

    def test_node_ids_are_preserved_verbatim(self):
        out = self.to_archify(VALID_IR, "architecture")
        self.assertEqual(["n1"], [n["id"] for n in out[NODE_KEY]])

    def test_korean_labels_survive_conversion(self):
        out = self.to_archify(VALID_IR, "architecture")
        self.assertEqual("로그인", out[NODE_KEY][0]["label"])

    def test_gx_evidence_maps_to_archify_sources(self):
        out = self.to_archify(VALID_IR, "architecture", repository=TEST_REPOSITORY)
        component = out[NODE_KEY][0]
        self.assertEqual([{"path": "a.java", "line": 1}], component["sources"])
        self.assertEqual(TEST_REPOSITORY, out["meta"]["repository"])

    def test_missing_repository_omits_sources_and_meta_repository(self):
        # sources를 실으면 Archify가 meta.repository{url, revision}과 --repo-root를 요구하고
        # 실제 리포지토리로 경로 존재를 검증한다 (실측 보고 §3.3). repository가 없으면 둘 다 비운다.
        out = self.to_archify(VALID_IR, "architecture")
        self.assertNotIn("sources", out[NODE_KEY][0])
        self.assertNotIn("repository", out["meta"])

    def test_gx_only_fields_are_not_leaked(self):
        # 최상위가 additionalProperties: false이므로 GX 전용 필드는 반드시 빠져야 한다.
        blob = json.dumps(self.to_archify(VALID_IR, "architecture"), ensure_ascii=False)
        for gx_only in ("evidence", "technical_label", "status", '"view"', "ko-KR"):
            self.assertNotIn(gx_only, blob)

    def test_inferred_evidence_is_dropped(self):
        ir = json.loads(json.dumps(VALID_IR))
        ir["nodes"][0]["evidence"] = [{"kind": "inferred"}]
        out = self.to_archify(ir, "architecture", repository=TEST_REPOSITORY)
        self.assertNotIn("sources", out[NODE_KEY][0])

    def test_sources_are_capped_at_three(self):
        ir = json.loads(json.dumps(VALID_IR))
        ir["nodes"][0]["evidence"] = [
            {"kind": "code", "file": f"f{n}.java", "line": n} for n in range(1, 6)
        ]
        out = self.to_archify(ir, "architecture", repository=TEST_REPOSITORY)
        self.assertEqual(3, len(out[NODE_KEY][0]["sources"]))

    def test_conversion_is_deterministic(self):
        self.assertEqual(self.to_archify(VALID_IR, "architecture"), self.to_archify(VALID_IR, "architecture"))

    def test_kind_maps_to_reported_type_and_col(self):
        # 실측 보고 §3.2의 kind→type/col 표를 하드코딩해 대조한다.
        for kind, (expected_type, expected_col) in KIND_TO_TYPE_AND_COL.items():
            component = self.to_archify(_single_node_ir(kind), "architecture")[NODE_KEY][0]
            self.assertEqual(expected_type, component["type"], kind)
            self.assertEqual(expected_col, component["col"], kind)

    def test_linear_chain_bands_in_one_row(self):
        out = self.to_archify(LINEAR_CHAIN_IR, "architecture")
        by_id = {c["id"]: c for c in out[NODE_KEY]}
        chain = ["c-screen", "c-api", "c-service", "c-repo", "c-table"]
        self.assertEqual({0}, {by_id[node_id]["row"] for node_id in chain})
        self.assertEqual([0, 1, 2, 3, 4], [by_id[node_id]["col"] for node_id in chain])

    def test_row_follows_connection_source_not_id_order(self):
        # id 정렬만으로 행을 매기면 s-alpha/a-alpha, s-zulu/a-zulu가 잘못 짝지어진다.
        # 실제 연결은 s-alpha->a-zulu, s-zulu->a-alpha이므로 그 짝이 같은 행에 있어야 한다.
        out = self.to_archify(CROSSED_CHAINS_IR, "architecture")
        by_id = {c["id"]: c for c in out[NODE_KEY]}
        self.assertEqual(by_id["s-alpha"]["row"], by_id["a-zulu"]["row"])
        self.assertEqual(by_id["s-zulu"]["row"], by_id["a-alpha"]["row"])
        self.assertNotEqual(by_id["s-alpha"]["row"], by_id["s-zulu"]["row"])

    def test_row_and_col_assignment_is_deterministic(self):
        first = self.to_archify(CROSSED_CHAINS_IR, "architecture")
        second = self.to_archify(CROSSED_CHAINS_IR, "architecture")
        self.assertEqual(first, second)

    def test_same_column_edge_gets_explicit_sides(self):
        # service -> service, repository -> repository 는 실제로 존재한다(설계서 5.7.1).
        conn = self.to_archify(_ir_same_layer_chain(), "architecture")[EDGE_KEY][0]
        self.assertEqual(conn["fromSide"], "bottom")
        self.assertEqual(conn["toSide"], "top")

    def test_cross_column_edge_has_no_explicit_sides(self):
        conn = self.to_archify(_ir_normal_chain(), "architecture")[EDGE_KEY][0]
        self.assertNotIn("fromSide", conn)

    def test_cited_paths_collects_and_dedupes_code_evidence_files(self):
        # render_archify가 git dirty 검사를 이 목록에만 국한하므로(ruling 4, 라운드 2),
        # to_archify()가 실제로 sources에 실을 파일과 정확히 같아야 한다.
        ir = {
            "schema_version": 1, "view": "service", "locale": "ko-KR", "title": "t",
            "nodes": [
                {"id": "n1", "kind": "api", "label": "a", "evidence": [
                    {"kind": "code", "file": "b.java", "line": 1},
                    {"kind": "code", "file": "a.java", "line": 2},
                ]},
                {"id": "n2", "kind": "service", "label": "b", "evidence": [
                    {"kind": "code", "file": "a.java", "line": 9},
                    {"kind": "inferred"},
                ]},
            ],
            "edges": [],
        }
        self.assertEqual(["a.java", "b.java"], self.cited_paths(ir))

    def test_cited_paths_respects_per_node_source_cap(self):
        ir = json.loads(json.dumps(VALID_IR))
        ir["nodes"][0]["evidence"] = [
            {"kind": "code", "file": f"f{n}.java", "line": n} for n in range(1, 6)
        ]
        self.assertEqual(3, len(self.cited_paths(ir)))

    def test_cited_paths_is_empty_when_no_code_evidence(self):
        self.assertEqual([], self.cited_paths(TRACE_IR))

    def test_long_korean_label_gets_explicit_size(self):
        # "에너지 사용량 조회 API" = 11자 → 기본 120px를 넘는다
        ir = _ir_with_label("에너지 사용량 조회 API")
        component = self.to_archify(ir, "architecture")[NODE_KEY][0]
        self.assertIn("size", component)
        width = component["size"][0]
        self.assertGreaterEqual(width + 8, _text_units("에너지 사용량 조회 API") * 6.6)

    def test_short_label_omits_size(self):
        # 기본 박스에 들어가면 size를 내보내지 않는다 — 불필요한 필드를 만들지 않는다
        self.assertNotIn("size", self.to_archify(_ir_with_label("로그인"), "architecture")[NODE_KEY][0])

    def test_long_sublabel_widens_the_box(self):
        # sublabel은 6px까지만 줄고 그 아래로는 Archify가 문서를 거부한다.
        ir = _ir_with_label("조회", technical="GET /adm/v1/reb/versions/{targetGrcodeCd}/download/by-building-pk")
        c = self.to_archify(ir, "architecture")[NODE_KEY][0]
        self.assertGreaterEqual(c["size"][0] - 8, _text_units(c["sublabel"]) * 6 * 0.6)

    def test_short_sublabel_does_not_widen(self):
        ir = _ir_with_label("조회", technical="GET /a")
        self.assertNotIn("size", self.to_archify(ir, "architecture")[NODE_KEY][0])

    def test_size_is_deterministic(self):
        ir = _ir_with_label("에너지 사용량 조회 API")
        self.assertEqual(self.to_archify(ir, "architecture"), self.to_archify(ir, "architecture"))

    def test_very_long_label_widens_grid_step_to_keep_separation(self):
        # 한글 25자 라벨 → cellW(150)+gapX(90)-8=232px 상한을 넘으므로 cellW가 함께 올라가야
        # 같은 행 옆 칸 컴포넌트와 8px 미만으로 겹치는 rectsOverlap 실패를 피한다.
        ir = _ir_with_label("가" * 25)
        out = self.to_archify(ir, "architecture")
        layout = out["layout"]
        for component in out[NODE_KEY]:
            width = component["size"][0] if "size" in component else 120
            self.assertGreaterEqual(layout["cellW"] + layout["gapX"] - width, 8)


if __name__ == "__main__":
    unittest.main()
