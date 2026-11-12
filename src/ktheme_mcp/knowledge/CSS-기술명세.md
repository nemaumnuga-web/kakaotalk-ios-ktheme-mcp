# 카카오톡 iOS 전용 테마 CSS: 기술 명세와 키 추적

## 브라우저 CSS가 아니다

`KakaoTalkTheme.css`는 카카오톡의 테마 로더가 읽는 스타일 정의다. JavaScript, HTML, CSS Grid/Flex 같은 웹 레이아웃 기능을 제공하는 파일이 아니다. 알 수 없는 키를 새로 만들어 쓰지 말고 버전 맞는 샘플에 나온 키만 우선 사용한다.

## ManifestStyle 키

- `-kakaotalk-theme-id`: 설치/업데이트 식별자 (기존 테마와 충돌 금지)
- `-kakaotalk-theme-name`: 테마 목록 이름
- `-kakaotalk-theme-version`: 업데이트를 위한 버전
- `-kakaotalk-theme-url`: 안내 URL
- `-kakaotalk-author-name`: 제작자 표시

2018 공식 가이드의 예시는 `url('...')` 형식이고 현대 예시는 `'...'` 문자열을 쓴다. **현재 적용되는 샘플 문법**을 따라라.

## 현대 샘플에서 발견되는 선택자 (예시, 전체 목록 아님)

| 선택자 | 기술 역할 | 주의 |
| --- | --- | --- |
| `ManifestStyle` | 식별 메타데이터 | ID, 버전 충돌 |
| `TabBarStyle-Main` | 탭 바 이미지와 상태 | 일반/선택 이름을 샘플에서 추출 |
| `HeaderStyle-Main` | 헤더 텍스트 등 | 앱 버전별 실제 영향 확인 |
| `MainViewStyle-Primary` | 리스트·텍스트 일부 | 한 색상 키가 다른 버튼에도 영향 가능 |
| `MainViewStyle-Secondary` | 보조 목록 배경 | 배경 이미지 우선순위 주의 |
| `SectionTitleStyle-Main` | 섹션 제목 관련 | 상태별 처리 |
| `DefaultProfileStyle` | 기본 프로필 이미지 | 참조 PNG 누락 주의 |
| `BackgroundStyle-ChatRoom` | 채팅방 배경 | 이미지/색 우선순위 확인 |
| `InputBarStyle-Chat` | 채팅 입력창/전송 | 상태별 키 주의 |
| `MessageCellStyle-Send` | 송신 말풍선 | 늘어나는 이미지/인셋 |
| `MessageCellStyle-Receive` | 수신 말풍선 | 늘어나는 이미지/인셋 |

이 선택자 표는 다수의 커뮤니티 샘플에서 보이는 형태이며 공식 최신 전체 명세라고 주장하지 않는다.

## 이미지와 CSS를 연결하는 예

```css
BackgroundStyle-ChatRoom {
  -ios-background-image: 'chatroomBgImage.png';
}
MessageCellStyle-Send {
  -ios-background-image: 'chatroomBubbleSend01.png' 20px 20px;
  -ios-group-background-image: 'chatroomBubbleSend02.png' 20px 20px;
}
```

파일명과 cap inset 수치는 **기술 형식 예시**일 뿐 디자인 지시나 현재 앱 호환 보증이 아니다.

## 스케일과 이미지 인셋

- CSS는 통상 `@2x`/`@3x` 접미사가 없는 베이스 PNG 이름을 참조한다.
- @2x 실제 픽셀 수와 @3x 실제 픽셀 수를 2:3 비율로 준비한다.
- `-ios-background-image` 등 확장 가능한 이미지 선언의 trailing `px`는 샘플 구조에 맞게 검증해야 한다.
- 이미지 파일 규격, 선택자, 뒤따르는 인셋 값 모두 사용 중인 샘플에 종속적이다.
- 일반 웹의 `border-radius`를 넣는 것이 이미지 말풍선의 cap inset을 대체하지 않는다.

## 2026년 9월 실기기 실측 주의

[커뮤니티 KEYMAP](https://github.com/han-hyeonmin/kakaotalk-custom-theme/blob/main/KEYMAP.md)은 `MainViewStyle-Primary`의 `-ios-text-color`가 목록 이름뿐 아니라 일부 헤더 아이콘, 통화 버튼 원 등에 동시 영향한다고 보고한다. `HeaderStyle-Main`과 일부 탭 칩의 매핑도 작성 당시 가이드와 달랐다고 한다. 이는 특정 앱 버전·화면에서의 측정이며 공식 스펙은 아니다.

## 흔한 오류 유형

- `CSS_BRACES`: 중괄호 수 불일치 → CSS 블록 정리.
- `MANIFEST_FIELD`: Manifest 필수 속성 공백 → 실제 값 입력.
- `IMAGE_REF_MISSING`: CSS가 참조하지만 해당 PNG/스케일 에셋이 없음 → 이름 비교.
- `CSS_DUPLICATE`: 같은 선택자에서 같은 키가 여러 번 등장 → 마지막 선언의 효과를 의심.
- `ALPHA_RANGE`: alpha의 예상 범위 0~1에서 벗어남.
- `SCALE_PAIR_MISSING`: @2x/@3x 중 하나만 있음 → 기준 샘플 요구 확인.

원문: https://t1.kakaocdn.net/kakaocorp/Service/Theme/KakaoTalk/iOS_theme_guide_KR_180103.pdf
구현 예: https://github.com/han-hyeonmin/kakaotalk-custom-theme
