import hashlib
import os
import struct
import tempfile
import unittest
import zlib
import zipfile
from pathlib import Path

from ktheme_mcp.catalog import KEYS
from ktheme_mcp.engine import (
    archive_fingerprint, build_qa_checklist, compare_projects, image_references,
    inspect_contents, list_known_keys, lookup_key, package_project, parse_css, png_info,
    read_css_block, safe_path, scaffold, validate_archive, validate_project,
    verify_reproducible_build,
)


def make_png(width, height):
    # 외부 라이브러리를 쓰지 않는 유효한 RGB PNG 테스트 픽스처.
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    pixels = (b"\x00" + b"\x00\x00\x00" * width) * height
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


CSS = """ManifestStyle {
  -kakaotalk-theme-id: 'com.test.mcp';
  -kakaotalk-theme-name: '테스트';
  -kakaotalk-theme-version: '1.0.0';
  -kakaotalk-theme-url: 'https://example.org';
  -kakaotalk-author-name: '테스터';
}
BackgroundStyle-ChatRoom {
  -ios-background-image: 'chatroomBgImage.png';
}
"""


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.theme = self.root / "theme"
        (self.theme / "Images").mkdir(parents=True)
        (self.theme / "KakaoTalkTheme.css").write_text(CSS, encoding="utf-8")
        (self.theme / "Images" / "chatroomBgImage@2x.png").write_bytes(make_png(4, 2))
        (self.theme / "Images" / "chatroomBgImage@3x.png").write_bytes(make_png(6, 3))
        (self.theme / "Images" / "commonIcoTheme.png").write_bytes(make_png(162, 162))

    def test_valid_folder(self):
        result = validate_project(str(self.theme))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["manifest"]["-kakaotalk-theme-name"], "'테스트'")
        self.assertEqual(len(result["references"]), 1)

    def test_2x_3x_ratio_warning(self):
        (self.theme / "Images" / "chatroomBgImage@3x.png").write_bytes(make_png(5, 3))
        result = validate_project(str(self.theme))
        self.assertTrue(result["ok"])
        self.assertIn("SCALE_RATIO", [x["code"] for x in result["issues"]])

    def test_missing_reference_error(self):
        (self.theme / "Images" / "chatroomBgImage@2x.png").unlink()
        (self.theme / "Images" / "chatroomBgImage@3x.png").unlink()
        result = validate_project(str(self.theme))
        self.assertFalse(result["ok"])
        self.assertIn("IMAGE_REF_MISSING", [x["code"] for x in result["issues"]])

    def test_invalid_png_error(self):
        (self.theme / "Images" / "commonIcoTheme.png").write_bytes(b"this-is-a-jpeg-renamed")
        result = validate_project(str(self.theme))
        self.assertFalse(result["ok"])
        self.assertIn("IMAGE_INVALID", [x["code"] for x in result["issues"]])

    def test_package_and_validate(self):
        out = self.root / "release.ktheme"
        built = package_project(str(self.theme), str(out))
        self.assertTrue(built["built"], built)
        self.assertTrue(validate_archive(str(out))["ok"])
        with zipfile.ZipFile(out) as z:
            self.assertIn("KakaoTalkTheme.css", z.namelist())
            self.assertIn("Images/commonIcoTheme.png", z.namelist())
            self.assertFalse(any(x.startswith("theme/") for x in z.namelist()))

    def test_reproducible_archive(self):
        a, b = self.root / "a.ktheme", self.root / "b.ktheme"
        package_project(str(self.theme), str(a))
        package_project(str(self.theme), str(b))
        self.assertEqual(hashlib.sha256(a.read_bytes()).digest(), hashlib.sha256(b.read_bytes()).digest())

    def test_nested_root_rejected(self):
        bad = self.root / "nested.ktheme"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("mytheme/KakaoTalkTheme.css", CSS)
        result = validate_archive(str(bad))
        self.assertFalse(result["ok"])
        self.assertIn("ZIP_CSS_ROOT", [x["code"] for x in result["issues"]])

    def test_zip_traversal_rejected(self):
        bad = self.root / "traversal.ktheme"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("KakaoTalkTheme.css", CSS)
            z.writestr("Images/../../pwned.png", make_png(1, 1))
        result = validate_archive(str(bad))
        self.assertFalse(result["ok"])
        self.assertIn("ZIP_TRAVERSAL", [x["code"] for x in result["issues"]])

    def test_refuse_to_package_into_source(self):
        with self.assertRaises(ValueError):
            package_project(str(self.theme), str(self.theme / "test.ktheme"))

    def test_refuse_overwrite_scaffold(self):
        with self.assertRaises(FileExistsError):
            scaffold(str(self.theme), theme_id="com.sample.id", name="A", version="1.0", author="B")

    def test_creates_blank_skeleton(self):
        new = self.root / "new"
        r = scaffold(str(new), theme_id="com.sample.id", name="사용자 이름", version="1.0", author="유저")
        self.assertTrue((new / "Images").is_dir())
        self.assertIn("기술 시작점", (new / "KakaoTalkTheme.css").read_text())
        self.assertIn("스켈레톤", r["status"])

    def test_parse_comment_not_image_reference(self):
        blocks, iss = parse_css("/* -ios-background-image: 'fake.png' */\n" + CSS)
        self.assertEqual(len(image_references(blocks)), 1)

    def test_unknown_css_key_not_rejected(self):
        r = lookup_key("-ios-future-unknown-key")
        self.assertFalse(r["found"])
        self.assertIn("유효하지 않다는 뜻은 아니", r["message"])

    def test_png_info(self):
        result = png_info(make_png(3, 7))
        self.assertEqual((result["width"], result["height"]), (3, 7))

    def test_missing_manifest(self):
        (self.theme / "KakaoTalkTheme.css").write_text("MainViewStyle-Primary { background-color: #fff; }", encoding="utf-8")
        r = validate_project(str(self.theme))
        self.assertFalse(r["ok"])
        self.assertIn("MANIFEST_MISSING", [x["code"] for x in r["issues"]])

    def test_css_duplicate_key_warning(self):
        css = CSS + "MainViewStyle-Primary { background-color: #fff; background-color: #000; }"
        (self.theme / "KakaoTalkTheme.css").write_text(css, encoding="utf-8")
        r = validate_project(str(self.theme))
        self.assertIn("CSS_DUPLICATE", [x["code"] for x in r["issues"]])

    def test_disallow_out_of_root(self):
        with self.assertRaises(ValueError):
            safe_path("/etc/passwd")

    def test_strict_warning_blocks_build(self):
        (self.theme / "Images" / "commonIcoTheme.png").unlink()
        r = package_project(str(self.theme), str(self.root / "blocked.ktheme"), fail_on_warnings=True)
        self.assertFalse(r["built"])

    def test_read_css_block_found_and_suggestion(self):
        found = read_css_block(str(self.theme), "ManifestStyle")
        self.assertTrue(found["found"])
        self.assertIn("-kakaotalk-theme-id", found["declarations"])
        missing = read_css_block(str(self.theme), "ManifestStyl")
        self.assertFalse(missing["found"])
        self.assertIn("ManifestStyle", missing["similar"])

    def test_list_known_keys_filter(self):
        all_keys = list_known_keys()
        self.assertEqual(all_keys["count"], len(KEYS))
        only = list_known_keys("manifeststyle")
        self.assertTrue(only["keys"])
        self.assertTrue(all(k["selector"] == "ManifestStyle" for k in only["keys"]))
        self.assertEqual(list_known_keys("zzz-no-such-text")["count"], 0)

    def test_compare_projects_detects_changes(self):
        other = self.root / "other"
        (other / "Images").mkdir(parents=True)
        (other / "KakaoTalkTheme.css").write_text(
            CSS.replace("'테스트'", "'변경됨'") + "NewStyle-X { -ios-background-image: 'new.png'; }", encoding="utf-8")
        (other / "Images" / "chatroomBgImage@2x.png").write_bytes(make_png(8, 4))
        (other / "Images" / "chatroomBgImage@3x.png").write_bytes(make_png(6, 3))
        r = compare_projects(str(self.theme), str(other))
        self.assertFalse(r["identical"])
        self.assertIn("NewStyle-X", r["selectors_added"])
        self.assertIn("-kakaotalk-theme-name", [c["key"] for c in r["declarations_changed"]])
        self.assertEqual(r["image_size_changed"][0]["image"], "chatroomBgImage@2x.png")
        self.assertTrue(compare_projects(str(self.theme), str(self.theme))["identical"])

    def test_qa_checklist_is_technical_only(self):
        r = build_qa_checklist(str(self.theme), app_version="테스트버전")
        self.assertTrue(r["ok_to_test"])
        self.assertIn("테스트버전", r["markdown"])
        self.assertIn("chatroomBgImage.png", r["markdown"])
        self.assertTrue(all(i["result"] == "미확인" for i in r["items"]))
        self.assertNotIn("색상 추천", r["markdown"])

    def test_qa_checklist_blocks_on_errors(self):
        (self.theme / "Images" / "chatroomBgImage@2x.png").unlink()
        (self.theme / "Images" / "chatroomBgImage@3x.png").unlink()
        r = build_qa_checklist(str(self.theme))
        self.assertFalse(r["ok_to_test"])

    def test_archive_fingerprint(self):
        out = self.root / "fp.ktheme"
        package_project(str(self.theme), str(out))
        fp = archive_fingerprint(str(out))
        self.assertEqual(len(fp["sha256"]), 64)
        self.assertTrue(fp["validation_ok"])
        self.assertIn("KakaoTalkTheme.css", fp["entries"])
        self.assertEqual(fp["size_bytes"], out.stat().st_size)

    def test_verify_reproducible_build(self):
        r = verify_reproducible_build(str(self.theme))
        self.assertTrue(r["built"])
        self.assertTrue(r["reproducible"])

    def test_verify_reproducible_build_reports_invalid_input(self):
        (self.theme / "Images" / "commonIcoTheme.png").write_bytes(b"broken")
        r = verify_reproducible_build(str(self.theme))
        self.assertFalse(r["built"])


if __name__ == "__main__":
    unittest.main()
