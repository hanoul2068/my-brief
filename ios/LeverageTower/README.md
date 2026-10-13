# 레버리지 관제탑 — iPhone 앱

claude.ai 아티팩트 「레버리지 관제탑」을 아이폰 전용 앱으로 감싼 Xcode 프로젝트입니다.
SwiftUI + WKWebView 앱이 claude.ai의 아티팩트를 그대로 띄우고(클라우드 모드), 인터넷이 없을 땐 앱에 넣어 둔 사본을 띄웁니다(오프라인 모드).

## 아이폰에 설치하기

### 방법 A — Mac이 없을 때 (Windows PC 또는 Mac)
1. GitHub 저장소 → **Actions** → **iOS App (관제탑)** → 가장 최근의 초록색 실행을 누르고,
   맨 아래 **Artifacts**의 `LeverageTower-ipa`를 내려받아 압축을 풉니다 → `LeverageTower.ipa`.
2. PC에 [Sideloadly](https://sideloadly.io)를 설치합니다(Windows는 iTunes · iCloud 앱도 필요).
3. 아이폰을 케이블로 연결 → Sideloadly에 `LeverageTower.ipa`를 끌어다 놓고 → Apple ID 입력 → **Start**.
4. 아이폰 **설정 → 일반 → VPN 및 기기 관리**에서 내 Apple ID를 **신뢰**,
   **설정 → 개인정보 보호 및 보안 → 개발자 모드**를 켭니다.
5. 홈 화면의 **관제탑** 아이콘을 눌러 엽니다.

무료 Apple ID는 7일마다 다시 서명해야 합니다(Sideloadly에서 같은 과정을 한 번 더). 유료 개발자 계정은 1년.

### 방법 B — Mac이 있을 때
1. `LeverageTower.xcodeproj`를 Xcode로 엽니다.
2. **LeverageTower** 타깃 → **Signing & Capabilities** → **Team**에 본인 Apple ID를 고릅니다.
   - 번들 ID가 이미 쓰인다는 오류가 나면 `com.hanoul.leveragetower` 뒤에 아무 글자나 붙이면 됩니다.
3. 아이폰을 연결하고 기기를 고른 뒤 ▶︎(⌘R). 신뢰 · 개발자 모드는 방법 A의 4번과 같습니다.

### 처음 열었을 때
claude.ai 로그인 화면이 나오면 **평소 쓰는 claude.ai 계정**으로 로그인하세요(이메일 로그인 추천).
로그인하면 아티팩트에서 쓰던 기록이 그대로 보입니다. 이후엔 로그인이 유지됩니다.

## 공유 중인 아티팩트에는 영향 없음

앱은 아티팩트를 **열어서 보여주기만** 합니다. 아티팩트 자체는 바꾸지 않으므로,
아티팩트를 공유받은 사람은 지금처럼 claude.ai에서 그대로 보고 쓰면 됩니다.
앱에서 입력한 기록은 아티팩트(웹)와 같은 곳에 저장되어 서로 똑같이 보입니다.

## 두 가지 모드

화면 왼쪽 아래 동그란 버튼(☁︎ / 📱)으로 바꿀 수 있습니다.

### ☁︎ 클라우드 모드 (기본)
claude.ai에 올라간 **실제 아티팩트**(`https://claude.ai/artifact/9nG9ugbYNfMmozoVJA85pU`)를 앱 안에서 엽니다.
처음 한 번 claude.ai에 로그인하면 이후엔 로그인이 유지되고, 아티팩트에서 되던 것이 전부 됩니다.

- 계정 동기화(웹 · 다른 기기와 같은 기록)
- 구글 드라이브 시세 시트 불러오기
- 스크린샷 자동 채우기
- 가계부 공유
- 백업 · CSV · 이미지 저장 → iOS 공유 시트(파일에 저장, 메모, 카톡 등)

아티팩트를 claude.ai에서 고치면 앱에도 바로 반영됩니다(앱을 다시 빌드할 필요 없음).

로그인 팁: **이메일로 로그인**이 가장 확실합니다. 구글 로그인도 되도록 해 두었지만 구글 정책이 바뀌면 막힐 수 있어요.

### 📱 오프라인 모드
앱 안에 들어 있는 사본(`LeverageTower/Web/index.html`)을 엽니다. 인터넷이 없어도 열리고, 기록은 이 아이폰에만 저장됩니다.
클라우드 모드에서 인터넷이 안 되면 자동으로 이 모드로 넘어갑니다.
계정 동기화 · 드라이브 시세 · 자동 채우기 · 가계부 공유는 이 모드에서 안 됩니다.

## 오프라인 사본 갱신하기

클라우드 모드는 저절로 최신이 됩니다. 오프라인 사본까지 맞추려면 아티팩트 HTML을 새로 받아 `LeverageTower/Web/index.html`을 바꾸고, 그 안의 cdnjs 스크립트 주소 네 개를
`vendor/react.production.min.js`, `vendor/react-dom.production.min.js`, `vendor/chart.umd.js`,
`vendor/html2canvas.min.js`로 바꾼 뒤 다시 빌드하면 됩니다.

## 파일 구성

```
LeverageTower.xcodeproj/        Xcode 프로젝트
LeverageTower/
  LeverageTowerApp.swift        앱 진입점
  TowerWebView.swift            웹뷰, 클라우드/오프라인 모드, 로그인 팝업, 다운로드 → 공유 시트
  Assets.xcassets/              앱 아이콘
  Web/index.html                관제탑 본체 (아티팩트 그대로)
  Web/vendor/                   React 18.2 · Chart.js 4.4.1 · html2canvas 1.4.1
```
