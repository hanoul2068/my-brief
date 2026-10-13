import SwiftUI
import UIKit
import UniformTypeIdentifiers
import WebKit

/// 번들에 들어 있는 관제탑 웹앱(Web/index.html)을 띄우는 웹뷰.
/// `tower://app/` 라는 고정 출처로 열어서 localStorage 기록이 앱을 껐다 켜도 그대로 남는다.
struct TowerWebView: UIViewRepresentable {
    static let scheme = "tower"
    static let startURL = URL(string: "\(scheme)://app/index.html")!

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.setURLSchemeHandler(BundleSchemeHandler(), forURLScheme: Self.scheme)
        config.allowsInlineMediaPlayback = true

        let controller = config.userContentController
        controller.addUserScript(WKUserScript(source: Self.bridgeJS, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        controller.addScriptMessageHandler(context.coordinator, contentWorld: .page, name: "saveFile")

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0xF6 / 255, green: 0xF7 / 255, blue: 0xF3 / 255, alpha: 1)
        webView.scrollView.backgroundColor = webView.backgroundColor
        // 페이지가 env(safe-area-inset-*)로 직접 여백을 잡으므로 스크롤뷰 자동 여백은 끈다.
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.allowsBackForwardNavigationGestures = false
        if #available(iOS 16.4, *) { webView.isInspectable = true }

        context.coordinator.webView = webView
        webView.load(URLRequest(url: Self.startURL))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    /// 아티팩트 런타임(window.claude) 대신 쓰는 최소한의 다리.
    /// - downloads: 백업 JSON · CSV · PNG 저장을 iOS 공유 시트(파일에 저장, 메모, 카톡 등)로 넘긴다.
    /// - 그 밖의 기능(db · user · mcp · sample)은 null을 돌려줘서 페이지가 '이 기기 저장' 모드로 동작하게 한다.
    static let bridgeJS = """
    (function () {
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

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandlerWithReply {
        weak var webView: WKWebView?

        // MARK: 파일 저장 → 공유 시트

        func userContentController(_ userContentController: WKUserContentController,
                                   didReceive message: WKScriptMessage,
                                   replyHandler: @escaping (Any?, String?) -> Void) {
            guard let body = message.body as? [String: Any],
                  let b64 = body["base64"] as? String,
                  let data = Data(base64Encoded: b64) else {
                replyHandler(nil, "잘못된 파일 데이터")
                return
            }
            let rawName = (body["filename"] as? String) ?? "file"
            let name = rawName.replacingOccurrences(of: "/", with: "_")
            let dir = FileManager.default.temporaryDirectory.appendingPathComponent("exports", isDirectory: true)
            let url = dir.appendingPathComponent(name)
            do {
                try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
                try data.write(to: url, options: .atomic)
            } catch {
                replyHandler(nil, error.localizedDescription)
                return
            }

            let sheet = UIActivityViewController(activityItems: [url], applicationActivities: nil)
            var replied = false
            sheet.completionWithItemsHandler = { _, completed, _, _ in
                guard !replied else { return }
                replied = true
                replyHandler(completed ? "saved" : "declined", nil)
            }
            guard let host = topViewController() else {
                replyHandler("declined", nil)
                return
            }
            if let pop = sheet.popoverPresentationController, let wv = webView {
                pop.sourceView = wv
                pop.sourceRect = CGRect(x: wv.bounds.midX, y: wv.bounds.maxY - 40, width: 1, height: 1)
            }
            host.present(sheet, animated: true)
        }

        private func topViewController() -> UIViewController? {
            let scene = UIApplication.shared.connectedScenes
                .compactMap { $0 as? UIWindowScene }
                .first { $0.activationState == .foregroundActive } ?? UIApplication.shared.connectedScenes.first as? UIWindowScene
            var top = scene?.windows.first { $0.isKeyWindow }?.rootViewController
            while let presented = top?.presentedViewController { top = presented }
            return top
        }

        // MARK: 바깥 링크는 사파리로

        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = navigationAction.request.url else { return decisionHandler(.allow) }
            if url.scheme == TowerWebView.scheme || url.scheme == "about" || url.scheme == "blob" || url.scheme == "data" {
                return decisionHandler(.allow)
            }
            if navigationAction.navigationType == .linkActivated || navigationAction.targetFrame == nil {
                UIApplication.shared.open(url)
                return decisionHandler(.cancel)
            }
            decisionHandler(.allow)
        }

        func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                     for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
            if let url = navigationAction.request.url { UIApplication.shared.open(url) }
            return nil
        }

        // 메모리 부족으로 웹 프로세스가 죽으면 다시 띄운다 (기록은 localStorage에 남아 있음).
        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            webView.load(URLRequest(url: TowerWebView.startURL))
        }

        // MARK: 혹시 쓰일 수 있는 기본 alert / confirm / prompt

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

/// `tower://app/<경로>` 요청을 앱 번들의 Web 폴더에서 읽어 돌려준다.
final class BundleSchemeHandler: NSObject, WKURLSchemeHandler {
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
