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
    var body: some View {
        TowerWebView()
            .ignoresSafeArea()
            .background(Color(red: 0xF6 / 255, green: 0xF7 / 255, blue: 0xF3 / 255))
            .preferredColorScheme(.light)
    }
}
