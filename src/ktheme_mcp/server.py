"""MCP v2 stdio 서버. 한국어 개발 지원 전용 / 시각 디자인 불개입."""
from __future__ import annotations

import re
from importlib.resources import files
from typing import Any

from mcp.server import MCPServer

from .catalog import SOURCES
from .engine import (
    allowed_roots, archive_fingerprint, build_qa_checklist, compare_projects, list_known_keys,
    lookup_key, package_project, read_css_block, safe_path, scaffold, troubleshoot,
    validate_archive, validate_project, verify_reproducible_build,
)

mcp = MCPServer("KakaoTalk-iOS-KTheme-Engineering-KO")
DOC_NAMES = ("개발-전체흐름", "CSS-기술명세", "에셋-패키징", "디버깅-호환성", "출처-신뢰도", "AI-협업-규칙")


def _doc(name: str) -> str:
    if name not in DOC_NAMES:
        raise ValueError(f"없는 문서입니다. 선택 가능한 문서: {', '.join(DOC_NAMES)}")
    return files("ktheme_mcp").joinpath("knowledge", f"{name}.md").read_text(encoding="utf-8")


@mcp.tool()
def search_ktheme_docs(query: str, limit: int = 5) -> dict[str, Any]:
    """한국어 iOS .ktheme 기술 문서를 검색한다. 디자인 취향 조언/이미지 생성은 제외한다.

    인터넷 실시간 검색이 아니라 이 저장소에 큐레이션한 문서의 로컬 검색이다.
    문서명을 명시하고 원 출처 URL을 함께 돌려준다.
    """
    terms = [x.casefold() for x in re.findall(r"[가-힣A-Za-z0-9@._-]+", query) if len(x) > 1]
    matches = []
    for name in DOC_NAMES:
        text = _doc(name)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            score = sum(3 if term in line.casefold() else 0 for term in terms)
            score += sum(1 for term in terms if term in " ".join(lines[max(0, i-2):i+3]).casefold())
            if score:
                excerpt = "\n".join(lines[max(0, i-2):min(len(lines), i+3)])[:900]
                matches.append({"doc": name, "line": i+1, "score": score, "excerpt": excerpt})
    matches.sort(key=lambda x: (-x["score"], x["doc"], x["line"]))
    return {"query": query, "matches": matches[:max(1, min(limit, 20))],
            "scope": "저장소 내 한국어 기술 문서 검색이며 실시간 웹 검색이 아님", "sources": SOURCES}


@mcp.tool()
def read_ktheme_doc(topic: str) -> dict[str, str]:
    """기술 문서 전문을 한국어로 읽는다: 개발-전체흐름/CSS-기술명세/에셋-패키징/디버깅-호환성/출처-신뢰도/AI-협업-규칙."""
    return {"topic": topic, "content": _doc(topic)}


@mcp.tool()
def lookup_ktheme_css_key(key: str) -> dict[str, Any]:
    """CSS 키의 용도·선택자·근거·불확실성을 확인한다. 없는 키를 곧바로 무효로 판정하지 않는다."""
    return lookup_key(key)


@mcp.tool()
def inspect_ktheme_project(theme_dir: str) -> dict[str, Any]:
    """테마의 CSS 메타데이터·선택자·PNG 참조 목록과 정적 경고를 확인한다. 파일은 변경하지 않는다."""
    return validate_project(theme_dir)


@mcp.tool()
def validate_ktheme_project(theme_dir: str) -> dict[str, Any]:
    """실제 테마 폴더에서 CSS, Manifest, 참조 이미지, PNG 시그니처, @2x/@3x 관계를 정적 검증한다."""
    return validate_project(theme_dir)


@mcp.tool()
def validate_ktheme_archive(ktheme_path: str) -> dict[str, Any]:
    """.ktheme ZIP의 루트/중복/경로탈출/메타파일/CRC/이미지 참조를 검증한다. iOS 적용은 별도 테스트."""
    return validate_archive(ktheme_path)


@mcp.tool()
def package_ktheme(theme_dir: str, output_path: str, fail_on_warnings: bool = False) -> dict[str, Any]:
    """사용자 제공 CSS와 PNG를 재현 가능한 .ktheme으로 패키징한다. 미술 이미지나 색상을 만들지 않는다.

    허용 경로 내에서만 실행하며 경고를 실패로 취급하려면 fail_on_warnings=True.
    """
    return package_project(theme_dir, output_path, fail_on_warnings=fail_on_warnings)


@mcp.tool()
def create_ktheme_skeleton(theme_dir: str, theme_id: str, theme_name: str, version: str, author: str) -> dict[str, Any]:
    """실제 디자인 없는 기술 시작용 파일 구조와 Manifest만 생성한다. 기존 파일을 덮어쓰지 않는다."""
    return scaffold(theme_dir, theme_id=theme_id, name=theme_name, version=version, author=author)


@mcp.tool()
def diagnose_ktheme_issue(symptom: str) -> dict[str, Any]:
    """설치 실패/이미지 미표시/말풍선 오류/색상 중첩/업데이트 실패에 대한 기술 진단 순서를 제시한다."""
    return troubleshoot(symptom)


@mcp.tool()
def get_ktheme_references() -> dict[str, Any]:
    """근거 출처별 작성 시점, 공식 여부, 신뢰도 한계, 원본 URL을 돌려준다."""
    return {"references": SOURCES, "policy": "새 CSS 키를 추정해 만들지 말 것. 기준 샘플과 앱 버전을 확인할 것."}


@mcp.tool()
def get_ktheme_workspace_policy() -> dict[str, Any]:
    """개발에 접근 가능한 로컬 디렉터리와 파일 변경 제한을 알려준다."""
    return {"allowed_roots": [str(x) for x in allowed_roots()],
            "access": "로컬 읽기/패키징만. 지정 범위 밖 접근 거부. 네트워크 호출·디자인 생성 없음.",
            "setup": "KTHEME_ALLOWED_ROOTS 환경변수를 OS 경로구분자로 추가하세요."}


@mcp.tool()
def read_ktheme_css_block(theme_dir: str, selector: str) -> dict[str, Any]:
    """테마 CSS에서 선택자 하나의 선언과 이미지 참조를 읽는다. 오타가 있으면 비슷한 선택자를 제안한다."""
    return read_css_block(theme_dir, selector)


@mcp.tool()
def list_ktheme_known_keys(text: str = "") -> dict[str, Any]:
    """검증된 CSS 키 인덱스를 검색한다(선택자·용도 문자열 포함). 빈 값이면 전체 목록."""
    return list_known_keys(text)


@mcp.tool()
def compare_ktheme_projects(theme_dir_a: str, theme_dir_b: str) -> dict[str, Any]:
    """두 테마 폴더를 비교해 추가/삭제된 선택자, 바뀐 선언, 이미지 변화를 보여준다(a → b). 파일은 변경하지 않는다."""
    return compare_projects(theme_dir_a, theme_dir_b)


@mcp.tool()
def build_ktheme_qa_checklist(theme_dir: str, app_version: str = "미확인") -> dict[str, Any]:
    """정적 검증 결과를 바탕으로 iPhone 실기기 확인용 한국어 체크리스트를 만든다. 디자인 판단은 하지 않는다."""
    return build_qa_checklist(theme_dir, app_version)


@mcp.tool()
def fingerprint_ktheme_archive(ktheme_path: str) -> dict[str, Any]:
    """.ktheme 파일의 SHA-256, 크기, 항목 목록, 검증 결과를 돌려준다. 배포본 기록용."""
    return archive_fingerprint(ktheme_path)


@mcp.tool()
def verify_ktheme_reproducible_build(theme_dir: str) -> dict[str, Any]:
    """같은 테마 폴더를 두 번 패키징해 해시가 같은지 확인한다. 원본 폴더는 건드리지 않는다."""
    return verify_reproducible_build(theme_dir)


@mcp.resource("ktheme://guide/{topic}")
def technical_guide(topic: str) -> str:
    """한국어 테마 개발 기술 문서 리소스 템플릿."""
    return _doc(topic)


@mcp.resource("ktheme://sources/all")
def evidence_index() -> str:
    """공식 자료/실기기 사례 구분이 된 출처 목록."""
    return "\n".join(f"[{k}] {v['kind']} · {v['title']}\n{v['url']}\n주의: {v['warning']}" for k,v in SOURCES.items())


@mcp.prompt()
def ktheme_engineering_only() -> str:
    """사용자의 그림/색/캐릭터 결정에 개입하지 않고 iOS 테마 코딩만 수행하도록 AI를 설정한다."""
    return ("너는 iOS 카카오톡 .ktheme의 기술 엔지니어다. 모든 답변은 한국어로 한다. "
            "일러스트 제작, 캐릭터 추천, 미적 평가, 임의 색상 및 분위기 제안은 하지 않는다. "
            "사용자가 제공한 디자인 값/에셋만 코드로 연결한다. 파일명, CSS 키, 포맷, 패키징, 디버깅, "
            "테스트 계획은 적극 지원한다. 근거는 공식 2018 문서와 2026 실측을 구분한다. "
            "검증 성공을 설치 성공이라 표현하지 않는다. 불확실한 키는 추측해 확정하지 않는다.")


@mcp.prompt()
def ktheme_debug_assistant(problem: str, app_version: str = "미확인") -> str:
    """오류 상황에서 에셋/선택자/패키징 검증 우선순위를 강제하는 디버깅 프롬프트."""
    return (f"문제: {problem}\n카카오톡 앱 버전: {app_version}\n"
            "디자인에는 개입하지 말고, 1) 재현 조건 2) 해당 CSS 키·선택자 3) 이미지 경로·배율 "
            "4) ZIP 루트/CRC 5) 실기기 확인 순서로 분석하라. 유효성 검사와 호환성 테스트를 구분하라.")


def main() -> None:
    """stdio 통신: stdout에 디버그 print 금지."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
