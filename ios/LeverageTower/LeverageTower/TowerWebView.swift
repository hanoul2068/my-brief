import SwiftUI
import UIKit
import UniformTypeIdentifiers
import WebKit

enum TowerMode: String {
    /// claude.ai에 올라간 실제 아티팩트를 연다. 로그인하면 계정 동기화 · 구글 드라이브 시세 ·
    /// 스크린샷 자동 채우기 · 가계부 공유까지 아티팩트와 똑같이 된다.
    case cloud
    /// 앱에 들어 있는 사본(Web/index.html)을 연다. 인터넷 없이 되지만 기록은 이 기기에만 남는다.
    case local
}

/// 웹뷰와 SwiftUI 메뉴 사이를 잇는 상태.
final class TowerController: ObservableObject {
    static let artifactURL = URL(string: "https://claude.ai/artifact/9nG9ugbYNfMmozoVJA85pU")!
    static let localURL = URL(string: "\(BundleSchemeHandler.scheme)://app/index.html")!
    private static let modeKey = "towerMode"

    @Published private(set) var mode: TowerMode
    @Published var toast: String?
    weak var webView: WKWebView?
    private var toastTask: DispatchWorkItem?

    init() {
        mode = TowerMode(rawValue: UserDefaults.standard.string(forKey: Self.modeKey) ?? "") ?? .cloud
    }

    var startURL: URL { mode == .cloud ? Self.artifactURL : Self.localURL }

    func switchTo(_ newMode: TowerMode, message: String? = nil) {
        mode = newMode
        UserDefaults.standard.set(newMode.rawValue, forKey: Self.modeKey)
        webView?.load(URLRequest(url: startURL))
        show(message ?? (newMode == .cloud ? "클라우드 모드로 열었어요" : "오프라인 모드로 열었어요 · 기록은 이 기기에만 저장돼요"))
    }

    func reload() {
        guard let webView else { return }
        if webView.url == nil { webView.load(URLRequest(url: startURL)) } else { webView.reload() }
    }

    func show(_ text: String) {
        toastTask?.cancel()
        toast = text
        let task = DispatchWorkItem { [weak self] in self?.toast = nil }
        toastTask = task
        DispatchQueue.main.asyncAfter(deadline: .now() + 3, execute: task)
    }
}

struct TowerWebView: UIViewRepresentable {
    @ObservedObject var tower: TowerController

    func makeCoordinator() -> Coordinator { Coordinator(tower: tower) }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        // 기본 저장소: claude.ai 로그인 쿠키와 오프라인 모드의 localStorage가 앱을 껐다 켜도 남는다.
        config.websiteDataStore = .default()
        config.setURLSchemeHandler(BundleSchemeHandler(), forURLScheme: BundleSchemeHandler.scheme)
        config.allowsInlineMediaPlayback = true
        // 구글 로그인은 앱 내장 브라우저를 막기 때문에 모바일 사파리와 같은 꼬리표를 단다.
        config.applicationNameForUserAgent = "Version/18.0 Mobile/15E148 Safari/604.1"

        let controller = config.userContentController
        controller.addUserScript(WKUserScript(source: Self.localBridgeJS, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        controller.addScriptMessageHandler(context.coordinator, contentWorld: .page, name: "saveFile")

        let webView = WKWebView(frame: .zero, configuration: config)
        Self.style(webView)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator

        tower.webView = webView
        context.coordinator.mainWebView = webView
        webView.load(URLRequest(url: tower.startURL))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    static func style(_ webView: WKWebView) {
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0xF6 / 255, green: 0xF7 / 255, blue: 0xF3 / 255, alpha: 1)
        webView.scrollView.backgroundColor = webView.backgroundColor
        // 페이지가 env(safe-area-inset-*)로 직접 여백을 잡으므로 스크롤뷰 자동 여백은 끈다.
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        if #available(iOS 16.4, *) { webView.isInspectable = true }
    }

    /// 오프라인 모드에서만 쓰는 window.claude 대용품.
    /// - downloads: 백업 JSON · CSV · PNG 저장을 iOS 공유 시트로 넘긴다.
    /// - 그 밖의 기능(db · user · mcp · sample)은 null을 돌려줘서 페이지가 '이 기기 저장' 모드로 동작하게 한다.
    /// 클라우드 모드에서는 claude.ai가 진짜 window.claude를 주므로 건드리지 않는다.
    static let localBridgeJS = """
    (function () {
      if (location.protocol !== '\(BundleSchemeHandler.scheme):') return;
      function toBase64(data) {
        if (data instanceof Blob) {
          return new Promise(function (res, rej) {
            var r = new FileReader();
            r.onload = function () { res(String(r.result).split(',')[1] || ''); };
            r.onerror = rej;
            r.readAsDataURL(data);
          });
        }
        var bytes = new TextEncoder().encode(String(data == null ? '' : data));
        var bin = '';
        for (var i = 0; i < bytes.length; i += 0x8000) {
          bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
        }
        return Promise.resolve(btoa(bin));
      }
      var downloads = {
        save: function (opts) {
          opts = opts || {};
          return toBase64(opts.data).then(function (b64) {
            return window.webkit.messageHandlers.saveFile.postMessage({ filename: opts.filename || 'file', base64: b64 });
          }).then(function (result) {
            if (result !== 'saved') { var e = new Error('declined'); e.code = 'declined'; throw e; }
          });
        }
      };
      window.claude = {
        native: true,
        use: function (name) { return Promise.resolve(name === 'downloads' ? downloads : null); }
      };
    })();
    """

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandlerWithReply, WKDownloadDelegate {
        let tower: TowerController
        weak var mainWebView: WKWebView?
        private var popups: [WKWebView: UIViewController] = [:]
        private var downloadFiles: [ObjectIdentifier: URL] = [:]

        init(tower: TowerController) { self.tower = tower }

        /// 앱 안에서 열어도 되는 주소: claude.ai와 로그인 화면들.
        static func isInAppHost(_ url: URL) -> Bool {
            guard let host = url.host?.lowercased() else { return false }
            let allowed = ["claude.ai", "anthropic.com", "claudeusercontent.com", "claude.com",
                           "accounts.google.com", "google.com", "gstatic.com", "googleusercontent.com",
                           "appleid.apple.com", "apple.com"]
            return allowed.contains { host == $0 || host.hasSuffix("." + $0) }
        }

        // MARK: 오프라인 모드 파일 저장 → 공유 시트

        func userContentController(_ userContentController: WKUserContentController,
                                   didReceive message: WKScriptMessage,
                                   replyHandler: @escaping (Any?, String?) -> Void) {
            guard let body = message.body as? [String: Any],
                  let b64 = body["base64"] as? String,
                  let data = Data(base64Encoded: b64) else {
                replyHandler(nil, "잘못된 파일 데이터")
                return
            }
            let name = ((body["filename"] as? String) ?? "file").replacingOccurrences(of: "/", with: "_")
            let url = Self.exportsDir().appendingPathComponent(name)
            do {
                try data.write(to: url, options: .atomic)
            } catch {
                replyHandler(nil, error.localizedDescription)
                return
            }
            share(url) { completed in replyHandler(completed ? "saved" : "declined", nil) }
        }

        private static func exportsDir() -> URL {
            let dir = FileManager.default.temporaryDirectory.appendingPathComponent("exports", isDirectory: true)
            try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            return dir
        }

        private func share(_ url: URL, done: @escaping (Bool) -> Void) {
            let sheet = UIActivityViewController(activityItems: [url], applicationActivities: nil)
            var replied = false
            sheet.completionWithItemsHandler = { _, completed, _, _ in
                guard !replied else { return }
                replied = true
                done(completed)
            }
            guard let host = topViewController() else { return done(false) }
            if let pop = sheet.popoverPresentationController, let wv = mainWebView {
                pop.sourceView = wv
                pop.sourceRect = CGRect(x: wv.bounds.midX, y: wv.bounds.maxY - 40, width: 1, height: 1)
            }
            host.present(sheet, animated: true)
        }

        private func topViewController() -> UIViewController? {
            let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
            let scene = scenes.first { $0.activationState == .foregroundActive } ?? scenes.first
            var top = scene?.windows.first { $0.isKeyWindow }?.rootViewController ?? scene?.windows.first?.rootViewController
            while let presented = top?.presentedViewController { top = presented }
            return top
        }

        // MARK: 클라우드 모드 다운로드(백업 · CSV · 이미지) → 공유 시트

        func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
            download.delegate = self
        }

        func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
            download.delegate = self
        }

        func download(_ download: WKDownload, decideDestinationUsing response: URLResponse,
                      suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
            let url = Self.exportsDir().appendingPathComponent(suggestedFilename.isEmpty ? "file" : suggestedFilename)
            try? FileManager.default.removeItem(at: url)
            downloadFiles[ObjectIdentifier(download)] = url
            completionHandler(url)
        }

        func downloadDidFinish(_ download: WKDownload) {
            guard let url = downloadFiles.removeValue(forKey: ObjectIdentifier(download)) else { return }
            share(url) { _ in }
        }

        func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
            downloadFiles.removeValue(forKey: ObjectIdentifier(download))
            tower.show("파일을 받지 못했어요")
        }

        // MARK: 이동 규칙

        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            if navigationAction.shouldPerformDownload { return decisionHandler(.download) }
            guard let url = navigationAction.request.url, let scheme = url.scheme?.lowercased() else {
                return decisionHandler(.allow)
            }
            if ["about", "blob", "data", "javascript", BundleSchemeHandler.scheme].contains(scheme) {
                return decisionHandler(.allow)
            }
            // 아티팩트 안쪽 프레임은 막지 않는다.
            if let frame = navigationAction.targetFrame, !frame.isMainFrame { return decisionHandler(.allow) }
            if (scheme == "https" || scheme == "http") && Self.isInAppHost(url) { return decisionHandler(.allow) }
            // 그 밖의 링크(뉴스, 증권사, 전화, 메일 등)는 사파리나 해당 앱으로.
            UIApplication.shared.open(url)
            decisionHandler(.cancel)
        }

        func webView(_ webView: WKWebView, decidePolicyFor navigationResponse: WKNavigationResponse,
                     decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
            if let http = navigationResponse.response as? HTTPURLResponse,
               let disp = http.value(forHTTPHeaderField: "Content-Disposition"), disp.lowercased().hasPrefix("attachment") {
                return decisionHandler(.download)
            }
            decisionHandler(navigationResponse.canShowMIMEType ? .allow : .download)
        }

        // 클라우드 모드에서 인터넷이 없으면 오프라인 모드로 넘어간다.
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            guard webView === mainWebView, tower.mode == .cloud else { return }
            let code = (error as NSError).code
            let offline: Set<Int> = [NSURLErrorNotConnectedToInternet, NSURLErrorNetworkConnectionLost,
                                     NSURLErrorTimedOut, NSURLErrorCannotFindHost, NSURLErrorCannotConnectToHost,
                                     NSURLErrorDNSLookupFailed, NSURLErrorDataNotAllowed]
            if offline.contains(code) {
                tower.switchTo(.local, message: "인터넷이 안 돼서 오프라인 모드로 열었어요")
            }
        }

        // 메모리 부족으로 웹 프로세스가 죽으면 다시 띄운다.
        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            webView.reload()
        }

        // MARK: 새 창(구글 · 애플 로그인 팝업 등)

        func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                     for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
            guard let url = navigationAction.request.url else { return nil }
            let isBlank = url.absoluteString.isEmpty || url.scheme == "about"
            guard isBlank || Self.isInAppHost(url) else {
                UIApplication.shared.open(url)
                return nil
            }
            // 로그인 팝업은 window.opener 연결이 살아 있어야 하므로 같은 설정으로 띄운다.
            let popup = WKWebView(frame: .zero, configuration: configuration)
            TowerWebView.style(popup)
            popup.scrollView.contentInsetAdjustmentBehavior = .automatic
            popup.navigationDelegate = self
            popup.uiDelegate = self

            let vc = UIViewController()
            vc.view.backgroundColor = .systemBackground
            vc.view.addSubview(popup)
            popup.translatesAutoresizingMaskIntoConstraints = false
            NSLayoutConstraint.activate([
                popup.topAnchor.constraint(equalTo: vc.view.safeAreaLayoutGuide.topAnchor),
                popup.bottomAnchor.constraint(equalTo: vc.view.bottomAnchor),
                popup.leadingAnchor.constraint(equalTo: vc.view.leadingAnchor),
                popup.trailingAnchor.constraint(equalTo: vc.view.trailingAnchor),
            ])
            let nav = UINavigationController(rootViewController: vc)
            vc.navigationItem.leftBarButtonItem = UIBarButtonItem(systemItem: .close, primaryAction: UIAction { [weak self, weak popup] _ in
                if let popup { self?.closePopup(popup) }
            })
            popups[popup] = nav
            topViewController()?.present(nav, animated: true)
            return popup
        }

        func webViewDidClose(_ webView: WKWebView) {
            closePopup(webView)
        }

        private func closePopup(_ webView: WKWebView) {
            guard let vc = popups.removeValue(forKey: webView) else { return }
            vc.dismiss(animated: true)
        }

        // MARK: 기본 alert / confirm / prompt

        func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                     initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
            let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
            a.addAction(UIAlertAction(title: "확인", style: .default) { _ in completionHandler() })
            guard let host = topViewController() else { return completionHandler() }
            host.present(a, animated: true)
        }

        func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                     initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
            let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
            a.addAction(UIAlertAction(title: "취소", style: .cancel) { _ in completionHandler(false) })
            a.addAction(UIAlertAction(title: "확인", style: .default) { _ in completionHandler(true) })
            guard let host = topViewController() else { return completionHandler(false) }
            host.present(a, animated: true)
        }

        func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String, defaultText: String?,
                     initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
            let a = UIAlertController(title: nil, message: prompt, preferredStyle: .alert)
            a.addTextField { $0.text = defaultText }
            a.addAction(UIAlertAction(title: "취소", style: .cancel) { _ in completionHandler(nil) })
            a.addAction(UIAlertAction(title: "확인", style: .default) { _ in completionHandler(a.textFields?.first?.text) })
            guard let host = topViewController() else { return completionHandler(nil) }
            host.present(a, animated: true)
        }
    }
}

/// `tower://app/<경로>` 요청을 앱 번들의 Web 폴더에서 읽어 돌려준다 (오프라인 모드).
final class BundleSchemeHandler: NSObject, WKURLSchemeHandler {
    static let scheme = "tower"
    private let root: URL = Bundle.main.resourceURL!.appendingPathComponent("Web", isDirectory: true)

    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        guard let url = urlSchemeTask.request.url else { return }
        var path = url.path
        if path.isEmpty || path == "/" { path = "/index.html" }
        let fileURL = root.appendingPathComponent(String(path.dropFirst())).standardizedFileURL

        guard fileURL.path.hasPrefix(root.standardizedFileURL.path),
              let data = try? Data(contentsOf: fileURL) else {
            let resp = HTTPURLResponse(url: url, statusCode: 404, httpVersion: "HTTP/1.1", headerFields: nil)!
            urlSchemeTask.didReceive(resp)
            urlSchemeTask.didReceive(Data())
            urlSchemeTask.didFinish()
            return
        }
        let mime = UTType(filenameExtension: fileURL.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
        let headers = [
            "Content-Type": mime.hasPrefix("text/") || mime.contains("javascript") ? "\(mime); charset=utf-8" : mime,
            "Content-Length": String(data.count),
            "Cache-Control": "no-cache",
        ]
        let resp = HTTPURLResponse(url: url, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: headers)!
        urlSchemeTask.didReceive(resp)
        urlSchemeTask.didReceive(data)
        urlSchemeTask.didFinish()
    }

    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) {}
}
