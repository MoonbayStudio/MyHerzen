import SwiftUI
#if os(iOS)
import GoogleSignIn
import UIKit
#endif
#if os(macOS)
import Cocoa

struct MacWindowChromeConfigurator: NSViewRepresentable {
    let colorScheme: ColorScheme?

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            configure(window: view.window)
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        DispatchQueue.main.async {
            configure(window: nsView.window)
        }
    }

    private func configure(window: NSWindow?) {
        guard let window else { return }
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.isMovableByWindowBackground = true
        window.isOpaque = false
        window.backgroundColor = .clear
        window.contentView?.wantsLayer = true
        window.contentView?.layer?.backgroundColor = NSColor.clear.cgColor
        window.styleMask.insert(.fullSizeContentView)

        switch colorScheme {
        case .dark:
            window.appearance = NSAppearance(named: .darkAqua)
        case .light:
            window.appearance = NSAppearance(named: .aqua)
        case nil:
            window.appearance = nil
        @unknown default:
            window.appearance = nil
        }

        if #available(macOS 13.0, *) {
            window.titlebarSeparatorStyle = .none
        }
    }
}
#endif
@main
struct MyHerzenApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var runtimeConfig = RuntimeConfigService.shared
    @StateObject private var scheduleViewModel = ScheduleViewModel()
    @State private var showLaunch = true
    @State private var systemIsDark = false
    @State private var themeObserver: NSObjectProtocol?
    @AppStorage("useSystemTheme") private var useSystemTheme = true
    @AppStorage("isDarkMode") private var isDarkMode = false
    @AppStorage("selectedThemeID") private var selectedThemeID = AppThemeCatalog.default

    init() {
#if os(iOS)
        ScheduleLiveActivityBackgroundScheduler.shared.register()
#endif
    }

    var body: some Scene {
        WindowGroup {
            Group {
                if showLaunch {
                    LaunchView(viewModel: scheduleViewModel)
                        .onDisappear {
                            showLaunch = false
                        }
                } else {
                    ContentView(viewModel: scheduleViewModel)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .background(appThemeBackground)
            .environmentObject(runtimeConfig)
            .environment(\.myherzenDisableLiveMaterial, true)
            .environment(\.myherzenSurfaceStrokeOpacity, 0.22)
            .preferredColorScheme(activeColorScheme)
#if os(macOS)
            .modifier(MyHerzenMacWindowToolbarBackgroundModifier())
#endif
            .myherzenDismissKeyboardOnTap()
            .onOpenURL { url in
                handleIncomingURL(url)
            }
            .onAppear {
                Task {
                    await runtimeConfig.refresh(force: true)
                }
            }
            .onChange(of: scenePhase) { phase in
                guard phase == .active else { return }
                Task {
                    await runtimeConfig.refresh()
                }
            }
#if os(macOS)
            .onAppear {
                updateSystemAppearance()
                subscribeToSystemThemeChanges()
            }
            .onDisappear {
                unsubscribeFromSystemThemeChanges()
            }
            .onChange(of: useSystemTheme) { _ in
                updateSystemAppearance()
                forceWindowAppearanceUpdate()
            }
            .onChange(of: isDarkMode) { _ in
                forceWindowAppearanceUpdate()
            }
            .onChange(of: selectedThemeID) { _ in
                forceWindowAppearanceUpdate()
            }
            .ignoresSafeArea(.container, edges: .top)
            .background(MacWindowChromeConfigurator(colorScheme: activeColorScheme))
#endif
        }
#if os(macOS)
        .commands {
            CommandGroup(replacing: .appInfo) { }
        }
#endif
    }

#if os(macOS)
    private var activeColorScheme: ColorScheme? {
        if let forced = AppThemeCatalog.theme(for: selectedThemeID).preferredColorScheme {
            return forced
        }
        return useSystemTheme
            ? (systemIsDark ? ColorScheme.dark : ColorScheme.light)
            : (isDarkMode ? ColorScheme.dark : ColorScheme.light)
    }

    private var appThemeBackground: some View {
        ThemedBackground(theme: AppThemeCatalog.theme(for: selectedThemeID))
            .ignoresSafeArea()
    }

    private func updateSystemAppearance() {
        let style = UserDefaults.standard.string(forKey: "AppleInterfaceStyle")
        systemIsDark = (style == "Dark")
    }

    private func subscribeToSystemThemeChanges() {
        guard themeObserver == nil else { return }
        themeObserver = DistributedNotificationCenter.default().addObserver(
            forName: Notification.Name("AppleInterfaceThemeChangedNotification"),
            object: nil,
            queue: .main
        ) { _ in
            updateSystemAppearance()
            forceWindowAppearanceUpdate()
        }
    }

    private func unsubscribeFromSystemThemeChanges() {
        guard let observer = themeObserver else { return }
        DistributedNotificationCenter.default().removeObserver(observer)
        themeObserver = nil
    }

    private func forceWindowAppearanceUpdate() {
        DispatchQueue.main.async {
            applyAppearanceToAllWindows()
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
            applyAppearanceToAllWindows()
        }
    }

    private func applyAppearanceToAllWindows() {
        for window in NSApp.windows {
            switch activeColorScheme {
            case .dark:
                window.appearance = NSAppearance(named: .darkAqua)
            case .light:
                window.appearance = NSAppearance(named: .aqua)
            case nil:
                window.appearance = nil
            @unknown default:
                window.appearance = nil
            }

            window.titleVisibility = .hidden
            window.titlebarAppearsTransparent = true
            window.isOpaque = false
            window.backgroundColor = .clear
            window.contentView?.wantsLayer = true
            window.contentView?.layer?.backgroundColor = NSColor.clear.cgColor
            window.styleMask.insert(.fullSizeContentView)

            window.contentView?.needsLayout = true
            window.contentView?.layoutSubtreeIfNeeded()
            window.contentView?.needsDisplay = true
            window.displayIfNeeded()
        }
    }
#else
    private var activeColorScheme: ColorScheme? {
        if let forced = AppThemeCatalog.theme(for: selectedThemeID).preferredColorScheme {
            return forced
        }
        return useSystemTheme ? nil : (isDarkMode ? ColorScheme.dark : ColorScheme.light)
    }

    private var appThemeBackground: some View {
        ThemedBackground(theme: AppThemeCatalog.theme(for: selectedThemeID))
            .ignoresSafeArea()
    }

#endif

    private func handleIncomingURL(_ url: URL) {
#if os(iOS)
        if GoogleSignInService.shared.handleIncomingURL(url) {
            return
        }
#endif
        guard url.scheme == "https",
              url.host == "myherzen.moonbaystudio.ru",
              url.path == "/verify-email",
              URLComponents(url: url, resolvingAgainstBaseURL: false)?
                .queryItems?
                .contains(where: { $0.name == "token" && ($0.value?.isEmpty == false) }) == true else {
            return
        }

        openVerificationWebLink(url)
    }

    private func openVerificationWebLink(_ url: URL) {
#if os(iOS)
        UIApplication.shared.open(url)
#elseif os(macOS)
        NSWorkspace.shared.open(url)
#endif
    }
}
