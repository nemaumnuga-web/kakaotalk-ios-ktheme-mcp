"""MCP 프로토콜 수준 통합 테스트: 도구 등록, 도구 호출, 리소스, 프롬프트를 실제 서버 객체로 검증한다.

SDK가 설치되지 않은 환경에서는 건너뛴다(엔진 테스트는 SDK 없이도 돈다).
"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

try:
    from ktheme_mcp import server as ktheme_server
    HAVE_SDK = True
except ImportError:  # pragma: no cover - SDK 미설치 환경
    HAVE_SDK = False

from test_engine import CSS, make_png

EXPECTED_TOOLS = {
    "search_ktheme_docs", "read_ktheme_doc", "lookup_ktheme_css_key", "inspect_ktheme_project",
    "validate_ktheme_project", "validate_ktheme_archive", "package_ktheme",
    "create_ktheme_skeleton", "diagnose_ktheme_issue", "get_ktheme_references",
    "get_ktheme_workspace_policy", "read_ktheme_css_block", "list_ktheme_known_keys",
    "compare_ktheme_projects", "build_ktheme_qa_checklist", "fingerprint_ktheme_archive",
    "verify_ktheme_reproducible_build",
}


def _payload(result):
    """CallToolResult에서 구조화된 dict를 꺼낸다. 없으면 텍스트 JSON을 파싱한다."""
    structured = getattr(result, "structured_content", None)
    if structured:
        return structured.get("result", structured) if isinstance(structured, dict) else structured
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    raise AssertionError(f"도구 결과를 읽을 수 없습니다: {result!r}")


@unittest.skipUnless(HAVE_SDK, "mcp SDK가 설치되지 않음")
class ServerProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.theme = Path(self.temp.name) / "theme"
        (self.theme / "Images").mkdir(parents=True)
        (self.theme / "KakaoTalkTheme.css").write_text(CSS, encoding="utf-8")
        (self.theme / "Images" / "chatroomBgImage@2x.png").write_bytes(make_png(4, 2))
        (self.theme / "Images" / "chatroomBgImage@3x.png").write_bytes(make_png(6, 3))
        (self.theme / "Images" / "commonIcoTheme.png").write_bytes(make_png(162, 162))

    def call(self, name, **arguments):
        return asyncio.run(ktheme_server.mcp.call_tool(name, arguments))

    def test_all_expected_tools_registered(self):
        tools = asyncio.run(ktheme_server.mcp.list_tools())
        names = {t.name for t in tools}
        self.assertTrue(EXPECTED_TOOLS <= names, f"누락된 도구: {EXPECTED_TOOLS - names}")
        for tool in tools:
            self.assertTrue(tool.description, f"설명 없음: {tool.name}")

    def test_resources_and_prompts_registered(self):
        templates = asyncio.run(ktheme_server.mcp.list_resource_templates())
        resources = asyncio.run(ktheme_server.mcp.list_resources())
        prompts = asyncio.run(ktheme_server.mcp.list_prompts())
        uris = {r.uri for r in resources} | {t.uri_template for t in templates}
        self.assertIn("ktheme://sources/all", uris)
        self.assertIn("ktheme://guide/{topic}", uris)
        self.assertEqual({p.name for p in prompts},
                         {"ktheme_engineering_only", "ktheme_debug_assistant"})

    def test_validate_project_via_tool(self):
        data = _payload(self.call("validate_ktheme_project", theme_dir=str(self.theme)))
        self.assertTrue(data["ok"], data)

    def test_read_css_block_via_tool(self):
        data = _payload(self.call("read_ktheme_css_block", theme_dir=str(self.theme), selector="ManifestStyle"))
        self.assertTrue(data["found"])

    def test_list_known_keys_via_tool(self):
        data = _payload(self.call("list_ktheme_known_keys", text="inset"))
        self.assertIsInstance(data["count"], int)

    def test_build_qa_checklist_via_tool(self):
        data = _payload(self.call("build_ktheme_qa_checklist", theme_dir=str(self.theme), app_version="X"))
        self.assertTrue(data["ok_to_test"])
        self.assertIn("# 실기기 QA 체크리스트", data["markdown"])

    def test_package_fingerprint_and_reproducible_via_tools(self):
        out = Path(self.temp.name) / "out" / "theme.ktheme"
        built = _payload(self.call("package_ktheme", theme_dir=str(self.theme), output_path=str(out)))
        self.assertTrue(built["built"], built)
        fp = _payload(self.call("fingerprint_ktheme_archive", ktheme_path=str(out)))
        self.assertEqual(len(fp["sha256"]), 64)
        repro = _payload(self.call("verify_ktheme_reproducible_build", theme_dir=str(self.theme)))
        self.assertTrue(repro["reproducible"])

    def test_compare_projects_via_tool(self):
        data = _payload(self.call("compare_ktheme_projects", theme_dir_a=str(self.theme),
                                  theme_dir_b=str(self.theme)))
        self.assertTrue(data["identical"])

    def test_unsafe_path_is_refused(self):
        with self.assertRaises(Exception):
            self.call("validate_ktheme_project", theme_dir="/etc")

    def test_guide_resource_reads_korean_doc(self):
        contents = asyncio.run(ktheme_server.mcp.read_resource("ktheme://guide/CSS-기술명세"))
        text = " ".join(getattr(c, "content", "") or getattr(c, "text", "") for c in contents)
        self.assertTrue(text.strip())


if __name__ == "__main__":
    unittest.main()
