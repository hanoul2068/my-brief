import SwiftUI

@main
struct LeverageTowerApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    @StateObject private var tower = TowerController()

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            TowerWebView(tower: tower)
                .ignoresSafeArea()

            Menu {
                Button { tower.reload() } label: { Label("새로고침", systemImage: "arrow.clockwise") }
                Divider()
                Picker("모드", selection: Binding(get: { tower.mode }, set: { tower.switchTo($0) })) {
                    Label("클라우드 (claude.ai 로그인)", systemImage: "icloud").tag(TowerMode.cloud)
                    Label("오프라인 (이 기기에만)", systemImage: "iphone").tag(TowerMode.local)
                }
            } label: {
                Image(systemName: tower.mode == .cloud ? "icloud" : "iphone")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(.white)
                    .frame(width: 38, height: 38)
                    .background(Circle().fill(Color(red: 0x1A / 255, green: 0x24 / 255, blue: 0x20 / 255).opacity(0.55)))
            }
            .padding(.leading, 14)
            .padding(.bottom, 16)

            if let toast = tower.toast {
                Text(toast)
                    .font(.footnote.weight(.semibold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 14).padding(.vertical, 9)
                    .background(Capsule().fill(Color.black.opacity(0.75)))
                    .frame(maxWidth: .infinity)
                    .padding(.bottom, 70)
                    .transition(.opacity)
            }
        }
        .background(Color(red: 0xF6 / 255, green: 0xF7 / 255, blue: 0xF3 / 255).ignoresSafeArea())
        .preferredColorScheme(.light)
        .animation(.easeInOut(duration: 0.2), value: tower.toast)
    }
}
