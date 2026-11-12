"""MCP 비의존 코어: 경로 통제, CSS/PNG 검사, ZIP 점검 및 재현성 패키징."""
from __future__ import annotations

import difflib
import os
import re
import struct
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from .catalog import KEYS, SOURCES, FAILURES

CSS_NAME = "KakaoTalkTheme.css"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
LEGACY_NAME = "KakaoTalk.css"
META_KEYS = (
    "-kakaotalk-theme-id", "-kakaotalk-theme-name", "-kakaotalk-theme-version",
    "-kakaotalk-theme-url", "-kakaotalk-author-name",
)
IGNORED = {".DS_Store", "Thumbs.db"}
MAX_ENTRY_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 180 * 1024 * 1024
MAX_COUNT = 1000


def allowed_roots() -> list[Path]:
    """사용자가 명시한 경로 + 실행 작업 디렉터리 + 임시 디렉터리만 허용한다."""
    roots = [Path(tempfile.gettempdir()), Path(__file__).resolve().parents[2]]
    if Path.cwd().resolve() != Path("/"):
        roots.append(Path.cwd())
    value = os.getenv("KTHEME_ALLOWED_ROOTS", "")
    roots.extend(Path(p).expanduser() for p in value.split(os.pathsep) if p.strip())
    return [x.resolve() for x in roots]


def safe_path(value: str, *, must_exist: bool = True) -> Path:
    path = Path(value).expanduser().resolve(strict=False)
    if not any(path == root or root in path.parents for root in allowed_roots()):
        raise ValueError(f"허용되지 않은 경로입니다: {path}. KTHEME_ALLOWED_ROOTS를 설정하세요.")
    if must_exist and not path.exists():
        raise FileNotFoundError(str(path))
    return path


def issue(level: str, code: str, message: str, location: str = "", suggestion: str = "") -> dict:
    return {"level": level, "code": code, "message": message, "location": location, "suggestion": suggestion}


def report(issues: list[dict], **extra: Any) -> dict:
    counts = Counter(x["level"] for x in issues)
    return {"ok": counts["error"] == 0, "errors": counts["error"], "warnings": counts["warning"],
            "infos": counts["info"], "issues": issues, **extra}


def is_junk(name: str) -> bool:
    pp = PurePosixPath(name)
    return name.startswith("__MACOSX/") or any(p.startswith("._") for p in pp.parts) or pp.name in IGNORED


def parse_css(css: str) -> tuple[dict[str, dict[str, str]], list[dict]]:
    """엄격한 전체 CSS 파서가 아닌 카카오 테마의 평평한 선택자/선언 리더."""
    issues: list[dict] = []
    clean = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # 주석과 문자열 안의 중괄호까지 완벽 파싱하는 도구가 아님; 진단 불확실성을 보존한다.
    blocks: dict[str, dict[str, str]] = {}
    if clean.count("{") != clean.count("}"):
        issues.append(issue("error", "CSS_BRACES", "중괄호 개수가 일치하지 않습니다.", CSS_NAME))
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", clean, flags=re.S):
        selector = match.group(1).strip()
        if not re.fullmatch(r"[\w.\-]+", selector):
            issues.append(issue("warning", "CSS_SELECTOR", "선택자 파싱이 불확실합니다.", selector[:80]))
            continue
        props = blocks.setdefault(selector, {})
        for part in match.group(2).split(";"):
            if not part.strip():
                continue
            if ":" not in part:
                issues.append(issue("warning", "CSS_DECLARATION", "선언에 ':'가 없습니다.", selector, part.strip()[:80]))
                continue
            name, val = (x.strip() for x in part.split(":", 1))
            if not name or not val:
                issues.append(issue("warning", "CSS_EMPTY_VALUE", "키 또는 값이 비어 있습니다.", f"{selector}::{name}"))
            if name in props:
                issues.append(issue("warning", "CSS_DUPLICATE", "같은 선택자에 키가 중복 선언되었습니다.", f"{selector}::{name}"))
            props[name] = val
    if not blocks:
        issues.append(issue("error", "CSS_NO_BLOCKS", "파싱 가능한 CSS 선택자 블록이 없습니다.", CSS_NAME))
    return blocks, issues


def image_references(blocks: dict[str, dict[str, str]]) -> list[dict]:
    found = []
    for selector, props in blocks.items():
        for key, value in props.items():
            if "image" not in key.lower():
                continue
            # URL/따옴표/무따옴표를 모두 인식하되 파일명만 추출.
            for name in re.findall(r"[\w.\-/@]+\.png", value, flags=re.I):
                found.append({"selector": selector, "key": key, "image": name})
    return found


def png_info(data: bytes, source: str = "") -> dict:
    if len(data) < 24 or not data.startswith(PNG_SIG) or data[12:16] != b"IHDR":
        return {"ok": False, "error": f"PNG 헤더/시그니처가 잘못됨: {source}"}
    width, height = struct.unpack(">II", data[16:24])
    if not (0 < width < 32768 and 0 < height < 32768):
        return {"ok": False, "error": f"PNG 크기가 비정상: {source}"}
    return {"ok": True, "width": width, "height": height}


def _read_images_from_dir(folder: Path) -> tuple[dict[str, tuple[int, int]], list[dict]]:
    dims: dict[str, tuple[int, int]] = {}
    issues = []
    for path in sorted(folder.iterdir()):
        if path.is_symlink():
            issues.append(issue("error", "IMAGE_SYMLINK", "심볼릭 링크 이미지는 금지합니다.", path.name))
            continue
        if path.is_dir():
            issues.append(issue("warning", "IMAGE_SUBDIR", "Images/ 내부 하위 폴더는 샘플과 호환성 확인이 필요합니다.", path.name))
            continue
        if is_junk(path.name):
            continue
        if path.suffix.lower() != ".png":
            issues.append(issue("warning", "IMAGE_NON_PNG", "Images/ 에 PNG 외 파일이 있습니다. 패키징에서 제외됩니다.", path.name))
            continue
        if path.stat().st_size > MAX_ENTRY_BYTES:
            issues.append(issue("error", "IMAGE_TOO_BIG", "단일 이미지 크기 제한(25MiB)을 넘습니다.", path.name))
            continue
        info = png_info(path.read_bytes()[:32], path.name)
        if not info["ok"]:
            issues.append(issue("error", "IMAGE_INVALID", info["error"], path.name))
            continue
        dims[path.name] = (info["width"], info["height"])
    return dims, issues


def inspect_contents(css: str, images: dict[str, tuple[int, int]], *, require_icon: bool = True) -> dict:
    blocks, issues = parse_css(css)
    if "ManifestStyle" not in blocks:
        issues.append(issue("error", "MANIFEST_MISSING", "ManifestStyle 블록이 없습니다.", CSS_NAME))
    else:
        for key in META_KEYS:
            value = blocks["ManifestStyle"].get(key, "").strip()
            if not value:
                issues.append(issue("error", "MANIFEST_FIELD", "필수 메타데이터가 비어 있습니다.", key))
        theme_id = blocks["ManifestStyle"].get("-kakaotalk-theme-id", "")
        if " " in theme_id.strip("'\" "):
            issues.append(issue("warning", "MANIFEST_ID_SPACE", "ID에 공백이 포함되었습니다.", "ManifestStyle"))
    refs = image_references(blocks)
    for ref in refs:
        name = PurePosixPath(ref["image"]).name
        if ".." in PurePosixPath(ref["image"]).parts or "/" in ref["image"]:
            issues.append(issue("error", "IMAGE_REF_PATH", "이미지 참조는 파일명만 사용하세요.", ref["image"]))
            continue
        if name in images:
            continue
        if "@2x" in name or "@3x" in name:
            issues.append(issue("warning", "IMAGE_REF_SCALE", "CSS에는 보통 배율 접미사 없는 베이스 이름을 참조합니다.", name))
        stem = name[:-4]
        if not any(c in images for c in (f"{stem}@2x.png", f"{stem}@3x.png")):
            issues.append(issue("error", "IMAGE_REF_MISSING", "CSS에서 참조한 PNG를 찾지 못했습니다.", name,
                                "Images/ 폴더의 정확한 이름 또는 대응하는 @2x/@3x 에셋을 확인하세요."))
    # 2x,3x 쌍 존재 및 2:3 픽셀 비율 확인. 모두에 강요하지 않고 발견한 쌍만 체크.
    for name, (w, h) in images.items():
        if "@2x.png" not in name:
            continue
        partner = name.replace("@2x.png", "@3x.png")
        if partner not in images:
            issues.append(issue("warning", "SCALE_PAIR_MISSING", "2x 에셋만 있습니다. 현재 샘플의 스케일 요구를 확인하세요.", name))
        else:
            w3, h3 = images[partner]
            if 3*w != 2*w3 or 3*h != 2*h3:
                issues.append(issue("warning", "SCALE_RATIO", "2x/3x 해상도가 정확히 2:3이 아닙니다.", name,
                                    f"2x={w}x{h}, 3x={w3}x{h3}"))
    for name in images:
        if "@3x.png" in name and name.replace("@3x.png", "@2x.png") not in images:
            issues.append(issue("warning", "SCALE_PAIR_MISSING", "3x 에셋만 있습니다. 현재 샘플의 스케일 요구를 확인하세요.", name))
    if require_icon and not any(x in images for x in ("commonIcoTheme.png", "commonIcoTheme@2x.png", "commonIcoTheme@3x.png")):
        issues.append(issue("warning", "ICON_MISSING", "테마 목록 아이콘이 없습니다. 공식 구형 가이드는 commonIcoTheme.png를 명시합니다.", "Images/"))
    if "commonIcoTheme.png" in images and images["commonIcoTheme.png"] != (162, 162):
        issues.append(issue("warning", "ICON_SIZE", "공식 2018 가이드의 아이콘 크기는 162×162px입니다. 사용하는 샘플에서 확인하세요.", "commonIcoTheme.png"))
    for selector, props in blocks.items():
        for key, raw in props.items():
            val = raw.strip().strip("'\"")
            if key.endswith("-alpha") or key in {"opacity", "border-alpha"}:
                try:
                    number = float(val)
                    if not 0 <= number <= 1:
                        issues.append(issue("warning", "ALPHA_RANGE", "투명도는 일반적으로 0~1입니다.", f"{selector}::{key}"))
                except ValueError:
                    issues.append(issue("warning", "ALPHA_INVALID", "투명도를 숫자로 파싱할 수 없습니다.", f"{selector}::{key}"))
            if key.endswith("-color") or key in ("background-color", "border-color"):
                if val and val.startswith("#") and not re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?", val):
                    issues.append(issue("warning", "COLOR_HEX", "HEX 색상 문법이 이상합니다.", f"{selector}::{key}"))
            if key.startswith("-ios-") and key not in KEYS and not any(k in key for k in ("color", "alpha", "image", "inset", "offset")):
                # 모든 사용자 정의 키를 오류로 다루지 않는다.
                pass
    return report(issues, selectors=sorted(blocks), manifest=blocks.get("ManifestStyle", {}), references=refs,
                  images={name: {"width": v[0], "height": v[1]} for name, v in sorted(images.items())},
                  caveat="정적 구조 검사입니다. 실제 카카오톡 설치·화면 적용 성공을 증명하지 않습니다.")


def validate_project(folder: str) -> dict:
    root = safe_path(folder)
    issues = []
    if not root.is_dir():
        return report([issue("error", "NOT_DIRECTORY", "폴더가 아닙니다.", str(root))])
    css_path, img_path = root / CSS_NAME, root / "Images"
    if not css_path.is_file():
        if (root / LEGACY_NAME).exists():
            issues.append(issue("error", "LEGACY_CSS", "레거시 KakaoTalk.css만 있습니다. 현대 샘플과 파일명/스키마를 대조하세요.", str(root)))
        else:
            issues.append(issue("error", "CSS_MISSING", f"{CSS_NAME} 파일이 없습니다.", str(root)))
    if not img_path.is_dir():
        issues.append(issue("error", "IMAGES_MISSING", "Images/ 폴더가 없습니다.", str(root)))
    if css_path.is_symlink() or img_path.is_symlink():
        issues.append(issue("error", "SYMLINK", "CSS/Images 경로가 심볼릭 링크입니다.", str(root)))
    if any(x["level"] == "error" for x in issues):
        return report(issues, path=str(root))
    if css_path.stat().st_size > 4 * 1024 * 1024:
        return report([issue("error", "CSS_TOO_BIG", "CSS 크기가 비정상입니다.", str(css_path))], path=str(root))
    css = css_path.read_text(encoding="utf-8-sig", errors="replace")
    images, image_issues = _read_images_from_dir(img_path)
    result = inspect_contents(css, images)
    return report(issues + image_issues + result["issues"], path=str(root),
                  selectors=result["selectors"], manifest=result["manifest"], references=result["references"],
                  images=result["images"], caveat=result["caveat"])


def validate_archive(archive: str) -> dict:
    path = safe_path(archive)
    issues: list[dict] = []
    if path.suffix.lower() != ".ktheme":
        issues.append(issue("error", "EXTENSION", "파일 확장자는 .ktheme 이어야 합니다.", str(path)))
    try:
        with zipfile.ZipFile(path) as zf:
            members = zf.infolist()
            if len(members) > MAX_COUNT:
                issues.append(issue("error", "ZIP_COUNT", "압축 항목이 너무 많습니다.", str(path)))
                return report(issues)
            names = [x.filename for x in members]
            if len(names) != len(set(names)):
                issues.append(issue("error", "ZIP_DUPLICATE", "ZIP에 동일 경로가 중복되었습니다.", str(path)))
            for member in members:
                filename = member.filename
                parts = PurePosixPath(filename).parts
                if filename.startswith("/") or ".." in parts or "\\" in filename or re.match(r"^[a-zA-Z]:", filename):
                    issues.append(issue("error", "ZIP_TRAVERSAL", "압축 내부 경로 탈출 요소가 있습니다.", filename))
                if member.external_attr >> 16 & 0o170000 == 0o120000:
                    issues.append(issue("error", "ZIP_SYMLINK", "ZIP 심볼릭 링크가 있습니다.", filename))
                if member.file_size > MAX_ENTRY_BYTES:
                    issues.append(issue("error", "ZIP_ENTRY_BIG", "과도하게 큰 항목이 있습니다.", filename))
                if is_junk(filename):
                    issues.append(issue("warning", "ZIP_JUNK", "macOS 메타파일이 포함되었습니다.", filename))
            if sum(x.file_size for x in members) > MAX_TOTAL_BYTES:
                issues.append(issue("error", "ZIP_TOTAL_BIG", "압축 원본 총 크기가 제한을 초과합니다.", str(path)))
            if CSS_NAME not in names:
                issues.append(issue("error", "ZIP_CSS_ROOT", "ZIP 최상위에 KakaoTalkTheme.css가 없습니다. 상위 폴더째 압축했을 수 있습니다."))
            image_names = [n[len("Images/"):] for n in names if n.startswith("Images/") and n.endswith(".png")]
            if not image_names:
                issues.append(issue("warning", "ZIP_IMAGES_EMPTY", "Images/ PNG가 없습니다. 실제 설치용이라면 이미지 에셋을 확인하세요."))
            if any(x["level"] == "error" for x in issues):
                return report(issues, path=str(path), entries=names)
            bad = zf.testzip()
            if bad:
                issues.append(issue("error", "ZIP_CRC", "압축 CRC가 일치하지 않습니다.", bad))
            images: dict[str, tuple[int, int]] = {}
            for n in names:
                if n.startswith("Images/") and n.lower().endswith(".png"):
                    entry = zf.getinfo(n)
                    if entry.file_size > MAX_ENTRY_BYTES:
                        continue
                    meta = png_info(zf.read(n)[:32], n)
                    if meta["ok"]:
                        images[n[7:]] = (meta["width"], meta["height"])
                    else:
                        issues.append(issue("error", "ZIP_PNG_INVALID", meta["error"], n))
            css = zf.read(CSS_NAME).decode("utf-8-sig", errors="replace")
            inner = inspect_contents(css, images)
            return report(issues + inner["issues"], path=str(path), entries=names,
                          manifest=inner["manifest"], caveat=inner["caveat"])
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        return report([issue("error", "ZIP_INVALID", f"압축을 읽을 수 없습니다: {type(exc).__name__}", str(path))])


def package_project(folder: str, destination: str, *, fail_on_warnings: bool = False) -> dict:
    root = safe_path(folder)
    out = safe_path(destination, must_exist=False)
    if out.suffix.lower() != ".ktheme":
        raise ValueError("출력 파일 확장자는 .ktheme이어야 합니다.")
    if out == root or root in out.parents:
        raise ValueError("출력 파일은 입력 테마 폴더 밖에 둬야 합니다(재귀 압축 방지).")
    checked = validate_project(str(root))
    if not checked["ok"] or (fail_on_warnings and checked["warnings"]):
        return {"built": False, "validation": checked, "reason": "입력 검증 실패. 출력하지 않았습니다."}
    out.parent.mkdir(parents=True, exist_ok=True)
    entries = [(CSS_NAME, root / CSS_NAME)]
    for path in sorted((root / "Images").iterdir()):
        if path.is_symlink() or path.is_dir() or is_junk(path.name) or path.suffix.lower() != ".png":
            continue
        entries.append((f"Images/{path.name}", path))
    fd, temp_name = tempfile.mkstemp(prefix=".ktheme-", suffix=".tmp", dir=out.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for name, path in entries:
                zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o100644 << 16
                zf.writestr(zi, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        # 출력 갱신 전에도 검증: 임시 파일은 .tmp 이므로 확장자 검증만 예외
        with zipfile.ZipFile(temp_name) as zf:
            if zf.testzip():
                raise ValueError("생성된 ZIP CRC가 잘못되었습니다.")
        os.replace(temp_name, out)
        final = validate_archive(str(out))
        return {"built": final["ok"], "path": str(out), "size_bytes": out.stat().st_size,
                "entries": [name for name, _ in entries], "validation": final}
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def scaffold(folder: str, *, theme_id: str, name: str, version: str, author: str) -> dict:
    target = safe_path(folder, must_exist=False)
    if not all([theme_id.strip(), name.strip(), version.strip(), author.strip()]):
        raise ValueError("ID/이름/버전/제작자 값은 비워둘 수 없습니다.")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", theme_id):
        raise ValueError("테마 ID는 영문·숫자·.·_·-만 허용합니다.")
    if any("'" in x or "\n" in x or "\r" in x or "\\" in x for x in (theme_id, name, version, author)):
        raise ValueError("테마 메타데이터에 따옴표/개행/역슬래시를 사용할 수 없습니다.")
    if target.exists() and any(target.iterdir()):
        raise FileExistsError("기존 파일이 있는 폴더는 덮어쓰지 않습니다.")
    target.mkdir(parents=True, exist_ok=True)
    (target / "Images").mkdir(exist_ok=True)
    template = f"""/* 사용자/AI가 디자인을 결정합니다. MCP는 기술 구조만 마련합니다. */
ManifestStyle {{
    -kakaotalk-theme-id: '{theme_id}';
    -kakaotalk-theme-name: '{name}';
    -kakaotalk-theme-version: '{version}';
    -kakaotalk-theme-url: 'https://example.invalid';
    -kakaotalk-author-name: '{author}';
}}
/* 여기부터 기준 샘플 테마의 실제 선택자와 키를 복사해 수정하세요.
 * 아래 파일은 기술 시작점이며 완성·적용 보장 테마가 아닙니다.
 * 예제 그림/색상/이미지는 의도적으로 넣지 않습니다. */
"""
    (target / CSS_NAME).write_text(template, encoding="utf-8")
    return {"created": str(target), "css": str(target / CSS_NAME), "images": str(target / "Images"),
            "status": "스켈레톤만 생성됨. 실제 배포 전 기준 샘플의 선택자·에셋을 추가하고 실기기로 검증하세요."}


def lookup_key(key: str) -> dict:
    k = key.strip()
    if k not in KEYS:
        guesses = difflib.get_close_matches(k, KEYS.keys(), n=4)
        return {"found": False, "key": k, "similar": guesses,
                "message": "이 인덱스에 없는 키입니다. 유효하지 않다는 뜻은 아니며 현재 기준 샘플을 먼저 확인하세요."}
    selector, usage, source_id, confidence = KEYS[k]
    return {"found": True, "key": k, "selector": selector, "usage": usage,
            "evidence_level": confidence, "source": SOURCES[source_id],
            "disclaimer": "도구는 전체 CSS 명세가 아니며 런타임 효과는 버전별 실기기 확인이 필요합니다."}


def troubleshoot(keyword: str) -> dict:
    candidates = [k for k in FAILURES if keyword.strip() in k or k in keyword]
    if not candidates:
        candidates = difflib.get_close_matches(keyword, FAILURES, n=3, cutoff=0.1)
    return {"query": keyword, "matched": {k: FAILURES[k] for k in candidates},
            "rule": "미확인 기능을 확정적으로 말하지 말고, 문제 발생 경로와 실제 iOS 앱 버전을 기록하세요."}
