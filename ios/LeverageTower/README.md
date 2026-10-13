# 레버리지 관제탑 — iPhone 앱

claude.ai 아티팩트 「레버리지 관제탑」을 아이폰 전용 앱으로 감싼 Xcode 프로젝트입니다.
화면과 계산 로직은 아티팩트와 똑같고(`LeverageTower/Web/index.html`), SwiftUI + WKWebView가 그것을 띄웁니다.

## 실행 방법

1. Mac에서 `LeverageTower.xcodeproj`를 Xcode(15 이상)로 엽니다.
2. 왼쪽에서 **LeverageTower** 타깃 → **Signing & Capabilities** → **Team**에 본인 Apple ID를 고릅니다.
   - 번들 ID(`com.hanoul.leveragetower`)가 이미 쓰이고 있다는 오류가 나면 아무 값으로 바꾸면 됩니다.
3. 아이폰을 케이블로 연결하고 상단 기기 목록에서 고른 뒤 ▶︎(⌘R)를 누릅니다.
   - 처음엔 아이폰 **설정 → 일반 → VPN 및 기기 관리**에서 개발자 앱을 신뢰해야 열립니다.
   - 아이폰의 **설정 → 개인정보 보호 및 보안 → 개발자 모드**도 켜져 있어야 합니다.
   - 무료 Apple ID로 설치하면 7일마다 Xcode에서 다시 설치해야 합니다(유료 개발자 계정은 1년).

## 앱에서 달라지는 점

| 기능 | 아티팩트 | 앱 |
|---|---|---|
| 기록 저장 | claude.ai 계정(클라우드) | **이 아이폰 안**(앱 삭제 전까지 유지) |
| 백업 JSON · CSV · 포트폴리오 PNG | 다운로드 | iOS 공유 시트(파일에 저장, 메모, 카톡 등) |
| 백업에서 복원 | 파일 선택 | 파일 앱에서 선택 |
| 체결일 환율 자동 조회 | 됨 | 됨(인터넷 필요) |
| 구글 드라이브 시세 시트 · 스크린샷 자동 채우기 · 가계부 공유 | 됨 | 안 됨(claude.ai 전용 기능) |
| 오프라인 | — | React · Chart.js를 앱에 넣어 둬서 인터넷 없이도 열림 |

### 기존 기록 옮기기

1. claude.ai의 아티팩트에서 **설정 → 백업 파일 다운로드**로 JSON을 받아 아이폰 파일 앱에 저장합니다.
2. 앱에서 **설정 → 백업에서 복원**으로 그 파일을 고릅니다.

## 아티팩트를 고친 뒤 앱에 반영하기

아티팩트 HTML을 새로 받아 `LeverageTower/Web/index.html`을 바꾸고, 그 안의 cdnjs 스크립트 주소 네 개를
`vendor/react.production.min.js`, `vendor/react-dom.production.min.js`, `vendor/chart.umd.js`,
`vendor/html2canvas.min.js`로 바꾼 뒤 다시 빌드하면 됩니다.

## 파일 구성

```
LeverageTower.xcodeproj/        Xcode 프로젝트
LeverageTower/
  LeverageTowerApp.swift        앱 진입점
  TowerWebView.swift            웹뷰, tower:// 번들 서버, 파일 저장 → 공유 시트 다리
  Assets.xcassets/              앱 아이콘
  Web/index.html                관제탑 본체 (아티팩트 그대로)
  Web/vendor/                   React 18.2 · Chart.js 4.4.1 · html2canvas 1.4.1
```
