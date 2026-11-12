"""검증된 일부 키의 근거와 한계를 수록한 기술 인덱스 (전체 스키마가 아님)."""

SOURCES = {
    "kakao_2018": {
        "title": "카카오 iOS 사용자 테마 가이드 (2018-01-03, 레거시)",
        "url": "https://t1.kakaocdn.net/kakaocorp/Service/Theme/KakaoTalk/iOS_theme_guide_KR_180103.pdf",
        "kind": "공식·역사적 자료",
        "warning": "2018년 문서이며 현재 카카오톡의 CSS 파일명/선택자와 다를 수 있음",
    },
    "community_sample": {
        "title": "최근 iOS KakaoTalkTheme.css 구조 예시 (커뮤니티)",
        "url": "https://github.com/han-hyeonmin/kakaotalk-custom-theme",
        "kind": "커뮤니티 실제 프로젝트",
        "warning": "카카오 공식 보증이 아님. 대상 앱 버전에 따라 동작 변화 가능",
    },
    "community_keymap": {
        "title": "2026-09-15 실제 기기 기반 키 매핑 리포트",
        "url": "https://github.com/han-hyeonmin/kakaotalk-custom-theme/blob/main/KEYMAP.md",
        "kind": "커뮤니티 실측·범위 제한",
        "warning": "측정 화면·앱 버전에 의존하며 모든 카카오톡 화면을 대표하지 않음",
    },
    "community_mcp": {
        "title": "iOS 테마 리소스 이름·구조에 대한 커뮤니티 안내",
        "url": "https://github.com/jkaae93/kakaotalk_theme_mcp/blob/main/design.md",
        "kind": "커뮤니티 참고자료",
        "warning": "반드시 기준 샘플의 실제 파일명과 비교",
    },
    "mcp_sdk": {
        "title": "MCP Python SDK v2 공식 문서",
        "url": "https://py.sdk.modelcontextprotocol.io/",
        "kind": "SDK 공식 문서",
        "warning": "MCP 라이브러리 API 변경 시 다시 확인",
    },
}

# 지원키 전체가 아님. 각 키는 구버전 문서와 현대 샘플의 차이를 주석에 기록해야 한다.
KEYS = {
    "-kakaotalk-theme-id": ("ManifestStyle", "테마 식별자. 충돌하지 않는 ID를 사용", "kakao_2018", "확인된 문서 키"),
    "-kakaotalk-theme-name": ("ManifestStyle", "카카오톡 테마 화면에 노출되는 이름", "kakao_2018", "확인된 문서 키"),
    "-kakaotalk-theme-version": ("ManifestStyle", "업데이트용 버전 문자열", "kakao_2018", "확인된 문서 키"),
    "-kakaotalk-theme-url": ("ManifestStyle", "테마 소개 URL", "kakao_2018", "확인된 문서 키"),
    "-kakaotalk-author-name": ("ManifestStyle", "제작자 표시", "kakao_2018", "확인된 문서 키"),
    "-ios-background-image": ("여러 선택자", "이미지 베이스 이름 참조, 샘플 기준", "kakao_2018", "선택자에 따라 다름"),
    "-ios-text-color": ("여러 선택자", "전역 단일 키가 아니라 선택자별 의미가 다름", "community_keymap", "실기기 측정 사례"),
    "-ios-paragraph-text-color": ("MainViewStyle-Primary", "목록 마지막 메시지/날짜 영향 사례", "community_keymap", "실기기 측정 사례"),
    "-ios-description-text-color": ("MainViewStyle-Primary", "목록 상태 메시지 영향 사례", "community_keymap", "실기기 측정 사례"),
    "-ios-friends-normal-icon-image": ("TabBarStyle-Main", "친구 탭 기본 이미지", "community_mcp", "현대 샘플과 대조 필요"),
    "-ios-chats-selected-icon-image": ("TabBarStyle-Main", "채팅 탭 선택 이미지", "community_mcp", "현대 샘플과 대조 필요"),
    "-ios-group-background-image": ("MessageCellStyle-Send / Receive", "연속 말풍선용 이미지 (cap inset 확인)", "community_mcp", "현대 샘플과 대조 필요"),
    "-ios-title-edgeinsets": ("MessageCellStyle-Send / Receive", "메시지 내부 padding 관련 좌표", "community_mcp", "현대 샘플과 대조 필요"),
}

FAILURES = {
    "적용이 안 됨": [".ktheme ZIP 루트에 KakaoTalkTheme.css와 Images/가 있는지", "압축 자체가 손상되지 않았는지", "실제 최신 샘플의 파일명·CSS 스키마와 일치하는지", "iOS 카카오톡에서 파일을 열었는지"],
    "이미지가 안 나옴": ["CSS 이미지 참조의 베이스 파일명과 Images/ 실제 이름이 일치하는지", "@2x/@3x 쌍과 배율이 맞는지", "PNG 시그니처가 유효한지", "해당 선택자가 현재 카카오톡 버전에서 살아 있는지"],
    "말풍선이 찌그러짐": ["메시지 CSS image 뒤의 stretch/cap inset 수치 확인", "원본 PNG와 스케일에 맞는 inset 단위인지", "짧은·긴 메시지를 실기기에서 각각 확인"],
    "색상이 예상과 다름": ["동일 키가 다른 요소에도 연결되는지", "선택자 우선순위와 타 영역 선언 확인", "기본 UI 색상 중 커스터마이징 불가 영역인지", "현재 기기 앱 버전과 KEYMAP의 검증 범위 확인"],
    "업데이트가 안 됨": ["ManifestStyle 의 고유 ID/버전 확인", "카카오톡 테마 목록에 동일 ID가 있는지", "캐시·적용 상태를 실기기에서 확인"],
}
