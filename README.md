# KakaoTalk iOS `.ktheme` Engineering MCP 🇰🇷

**한국어로 깊이 있게 카카오톡 iOS 테마 개발을 지원하는 MCP 서버. 디자인에 절대 개입하지 않는 엔지니어링 도구.**

- 사용자와 다른 디자인 AI가 정한 **일러스트 / 색상 / 시안**을 그대로 존중합니다.
- 이 서버는 **기술 코드, CSS 테마 선택자, 에셋 참조, 검증, 오류 해결, `.ktheme` 빌드**만 지원합니다.
- Android `.apk`가 아닌 **iPhone용 `.ktheme`** 전용입니다.
- 파이썬 3.11+ / MCP Python SDK **v2** / stdio 기반.
- **카카오 공식 제품이 아닙니다.** iOS 실기기 적용 성공은 별도 확인해야 합니다.

## 기능

| MCP 도구 | 역할 |
| --- | --- |
| `search_ktheme_docs` | 한글 기술 문서 키워드 검색, 원문 근거 표시 (오프라인) |
| `read_ktheme_doc` | 한국어 심화 매뉴얼 전문 |
| `lookup_ktheme_css_key` | 키의 선택자/용도/출처/확실성, 유사 키 |
| `inspect_ktheme_project` | Manifest/선택자/이미지 참조 기술 분석 |
| `validate_ktheme_project` | CSS/PNG/스케일/누락/인셋 관련 정적 검증 |
| `validate_ktheme_archive` | ZIP 루트/CRC/경로 안전성/이미지 참조 검사 |
| `package_ktheme` | 정적 검사 후 **결정적** `.ktheme` 빌드 |
| `create_ktheme_skeleton` | 디자인 없이 Manifest+폴더만 시작 |
| `diagnose_ktheme_issue` | 설치/말풍선/아이콘/색상 충돌 기술 디버깅 |
| `get_ktheme_references` | 공식/커뮤니티/실측 근거 분리 |
| `get_ktheme_workspace_policy` | 허용 파일 경로 진단 |
| `read_ktheme_css_block` | 테마 CSS의 특정 선택자 선언·이미지 참조 읽기 (오타 시 유사 선택자 제안) |
| `list_ktheme_known_keys` | 검증된 CSS 키 인덱스 검색 (근거 수준 포함) |
| `compare_ktheme_projects` | 두 테마 폴더 비교: 추가/삭제 선택자, 바뀐 선언, 이미지 크기 변화 |
| `build_ktheme_qa_checklist` | 정적 검증 결과 기반 iPhone 실기기 QA 체크리스트 (한국어 Markdown) |
| `fingerprint_ktheme_archive` | `.ktheme`의 SHA-256·항목 목록·검증 결과 기록 (배포본 추적) |
| `verify_ktheme_reproducible_build` | 같은 폴더를 두 번 패키징해 바이트 단위 동일성 확인 |

추가: `ktheme://guide/{topic}` 리소스, `ktheme://sources/all` 리소스, 기술전용/디버깅용 MCP 프롬프트 2개.

총 17개 도구. 모든 도구는 로컬 파일만 읽거나 임시 폴더에 쓰며, 원본 테마 폴더는 변경하지 않습니다.

## 설치

```bash
git clone <이 저장소 주소>
cd kakaotalk-ios-ktheme-mcp
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\\Scripts\\activate
pip install -e .
python -m ktheme_mcp           # stdio MCP 대기. 아무것도 출력되지 않아야 정상
```

또는 `uv sync && uv run ktheme-mcp`. MCP v2 SDK가 설치되지 않은 환경에서는 실행할 수 없습니다. 이 저장소의 자동 테스트는 SDK가 필요 없는 테마 검증 엔진을 테스트하며, 전체 MCP 프로토콜 연결은 별도 통합 테스트가 필요합니다.

**주의:** 연결한 AI 코딩 앱의 MCP 설정에 실제 프로젝트 절대경로를 넣어야 합니다. 예를 들면:

```json
{
  "mcpServers": {
    "kakaotalk-ios-ktheme-ko": {
      "command": "uv",
      "args": ["run", "--project", "/ABSOLUTE/PATH/kakaotalk-ios-ktheme-mcp", "ktheme-mcp"],
      "env": {"KTHEME_ALLOWED_ROOTS": "/ABSOLUTE/PATH/MY_THEMES"}
    }
  }
}
```

`--project` 경로, `KTHEME_ALLOWED_ROOTS`를 본인 기기에 맞게 바꾸세요. Windows에서 경로 목록은 `;`, macOS/Linux는 `:`로 구분합니다. 호스트별 MCP 설정 키 이름이 `mcpServers`가 아니라 `servers`일 수 있으므로 해당 앱 문서를 확인하세요.

## 2분 빠른 워크플로

```text
[AI] ktheme_engineering_only 프롬프트 적용
[AI] search_ktheme_docs("말풍선 cap inset / 스케일")
[AI] create_ktheme_skeleton(theme_dir, theme_id, theme_name, version, author)
[사용자/디자인 AI] CSS에 연결할 실제 PNG 제공, 원하는 디자인 확정
[AI] validate_ktheme_project(theme_dir)
[AI] package_ktheme(theme_dir, output_path)
[AI] validate_ktheme_archive(ktheme_path)
[사용자] iPhone 카카오톡에 적용하여 실기기 테스트
```

스켈레톤만으로는 완성 테마가 **아닙니다**. 정상 작동하는 기준 샘플을 확보해 지원되는 선택자와 에셋 명세를 유지해야 합니다.

## 상세 문서 (100% 한국어)

- [개발 전체 흐름](src/ktheme_mcp/knowledge/개발-전체흐름.md)
- [CSS 기술 명세](src/ktheme_mcp/knowledge/CSS-기술명세.md)
- [에셋·패키징](src/ktheme_mcp/knowledge/에셋-패키징.md)
- [디버깅·호환성](src/ktheme_mcp/knowledge/디버깅-호환성.md)
- [출처·신뢰도](src/ktheme_mcp/knowledge/출처-신뢰도.md)
- [AI 협업 규칙](src/ktheme_mcp/knowledge/AI-협업-규칙.md)

`search_ktheme_docs`는 **실시간 웹 검색이 아닌 로컬 문서 검색**입니다. 외부 자료는 직접 열 수 있는 URL로 반환하며 공식 여부와 자료 작성 시점을 분리해 표시합니다.

## 테스트

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests
```

`tests/test_server.py`는 MCP 프로토콜 수준에서 도구 등록·호출·리소스·프롬프트를 확인합니다(SDK 설치 필요, 미설치 시 건너뜀).

정적 검사만으로 KakaoTalk 로더의 수용 여부는 증명되지 않습니다. 앱 업데이트 이후에는 재적용 테스트를 수행하세요.

## 문서 기준

- [카카오 2018 iOS 사용자 테마 가이드(PDF, 역사적 공식 자료)](https://t1.kakaocdn.net/kakaocorp/Service/Theme/KakaoTalk/iOS_theme_guide_KR_180103.pdf)
- [2026 실측 키 매핑(커뮤니티)](https://github.com/han-hyeonmin/kakaotalk-custom-theme/blob/main/KEYMAP.md)
- [현대 테마 제작 사례(커뮤니티)](https://github.com/han-hyeonmin/kakaotalk-custom-theme)
- [MCP Python SDK v2 공식 문서](https://py.sdk.modelcontextprotocol.io/)

> 카카오톡 및 KakaoTalk 상표는 각각의 권리자에게 귀속됩니다. 본 저장소는 카카오와 제휴하지 않습니다. 타인의 캐릭터·원본 이미지·샘플 에셋은 임의 재배포하지 않습니다.

## 저장소 정보

이 저장소는 GitHub에 이미 올라가 있습니다. 새 저장소를 만들 때는 GitHub 웹이나 `gh repo create`를 직접 사용하세요. 토큰이나 암호를 코드에 포함하지 마세요.
