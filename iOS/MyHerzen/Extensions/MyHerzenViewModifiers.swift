import SwiftUI
#if os(iOS)
import UIKit
#elseif os(macOS)
import AppKit
#endif

private struct MyHerzenDefaultSurfaceModifier: ViewModifier {
    let cornerRadius: CGFloat
    let padding: CGFloat
    @AppStorage("selectedThemeID") private var selectedThemeID = AppThemeCatalog.default
    @Environment(\.myherzenSurfaceStrokeOpacity) private var strokeOpacity

    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(surfaceBackground)
            .clipShape(shape)
            .overlay(
                shape.stroke(surfaceStroke, lineWidth: 0.8)
            )
    }

    @ViewBuilder
    private var surfaceBackground: some View {
        if activeTheme.usesCloudSurface {
            activeTheme.cloudSurfaceFill
        } else {
            Color.myherzenHeaderCapsuleFill
        }
    }

    private var surfaceStroke: Color {
        activeTheme.usesCloudSurface
        ? activeTheme.cloudSurfaceStroke
        : Color.myherzenSurfaceStrokeBase.opacity(strokeOpacity)
    }

    private var activeTheme: AppTheme {
        AppThemeCatalog.theme(for: selectedThemeID)
    }
}

private struct MyHerzenControlTintModifier: ViewModifier {
    func body(content: Content) -> some View {
#if os(macOS)
        if #available(macOS 13.0, *) {
            content.tint(Color.myherzenControlTint)
        } else {
            content.accentColor(Color.myherzenControlTint)
        }
#else
        content.tint(Color.myherzenControlTint)
#endif
    }
}

private struct MyHerzenStateCardModifier: ViewModifier {
    let cornerRadius: CGFloat
    let shadowRadius: CGFloat
    @AppStorage("selectedThemeID") private var selectedThemeID = AppThemeCatalog.default
    @Environment(\.myherzenSurfaceStrokeOpacity) private var strokeOpacity

    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
        content
            .background(stateBackground)
            .clipShape(shape)
            .overlay(
                shape.stroke(stateStroke, lineWidth: 0.8)
            )
            .shadow(radius: shadowRadius)
    }

    @ViewBuilder
    private var stateBackground: some View {
        if activeTheme.usesCloudSurface {
            activeTheme.cloudSurfaceFill
        } else {
#if os(iOS)
            Color(UIColor.secondarySystemBackground)
#else
            Color(NSColor.windowBackgroundColor)
#endif
        }
    }

    private var stateStroke: Color {
        activeTheme.usesCloudSurface
        ? activeTheme.cloudSurfaceStroke
        : Color.myherzenSurfaceStrokeBase.opacity(strokeOpacity)
    }

    private var activeTheme: AppTheme {
        AppThemeCatalog.theme(for: selectedThemeID)
    }
}

private struct MyHerzenAdaptiveGlassCardModifier: ViewModifier {
    let cornerRadius: CGFloat
    @AppStorage("selectedThemeID") private var selectedThemeID = AppThemeCatalog.default

    func body(content: Content) -> some View {
        let shape = RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
        content
            .background(MyHerzenAdaptiveMaterialFill())
            .clipShape(shape)
            .overlay(
                shape.stroke(adaptiveStroke, lineWidth: 0.8)
            )
            .myherzenGlass(in: shape)
    }

    private var adaptiveStroke: Color {
        let theme = AppThemeCatalog.theme(for: selectedThemeID)
        return theme.usesCloudSurface ? theme.cloudSurfaceStroke : Color.clear
    }
}

#if os(iOS)
private struct MyHerzenKeyboardDismissTapInstaller: UIViewRepresentable {
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        view.isUserInteractionEnabled = false
        DispatchQueue.main.async {
            context.coordinator.installIfNeeded(from: view)
        }
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        DispatchQueue.main.async {
            context.coordinator.installIfNeeded(from: uiView)
        }
    }

    final class Coordinator: NSObject, UIGestureRecognizerDelegate {
        private weak var installedWindow: UIWindow?
        private weak var tapRecognizer: UITapGestureRecognizer?

        func installIfNeeded(from view: UIView) {
            guard UIDevice.current.userInterfaceIdiom == .phone,
                  let window = view.window,
                  installedWindow !== window else { return }

            if let tapRecognizer, let installedWindow {
                installedWindow.removeGestureRecognizer(tapRecognizer)
            }

            let recognizer = UITapGestureRecognizer(target: self, action: #selector(dismissKeyboard))
            recognizer.cancelsTouchesInView = false
            recognizer.delegate = self
            window.addGestureRecognizer(recognizer)
            installedWindow = window
            tapRecognizer = recognizer
        }

        @objc private func dismissKeyboard() {
            UIApplication.shared.sendAction(
                #selector(UIResponder.resignFirstResponder),
                to: nil,
                from: nil,
                for: nil
            )
        }

        func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
            var view: UIView? = touch.view
            while let currentView = view {
                if currentView is UIControl {
                    return false
                }
                view = currentView.superview
            }
            return true
        }
    }
}
#endif

private struct MyHerzenDismissKeyboardOnTapModifier: ViewModifier {
    func body(content: Content) -> some View {
#if os(iOS)
        if UIDevice.current.userInterfaceIdiom == .phone {
            content.background(MyHerzenKeyboardDismissTapInstaller())
        } else {
            content
        }
#else
        content
#endif
    }
}

private struct MyHerzenInteractiveBackSwipeModifier: ViewModifier {
    let enabled: Bool
    let edgeWidth: CGFloat
    let dismissThreshold: CGFloat
    let onBack: () -> Void

    @State private var dragOffset: CGFloat = 0

    func body(content: Content) -> some View {
#if os(iOS)
        content
            .offset(x: max(0, dragOffset))
            .overlay(alignment: .leading) {
                if enabled {
                    Color.clear
                        .frame(width: edgeWidth)
                        .contentShape(Rectangle())
                        .highPriorityGesture(interactiveBackGesture)
                }
            }
#else
        content
#endif
    }

#if os(iOS)
    private var interactiveBackGesture: some Gesture {
        DragGesture(minimumDistance: 8, coordinateSpace: .local)
            .onChanged { value in
                if value.translation.width > 0 {
                    dragOffset = value.translation.width
                }
            }
            .onEnded { value in
                let shouldDismiss = value.translation.width > dismissThreshold
                if shouldDismiss {
                    let width = UIScreen.main.bounds.width
                    withAnimation(.interactiveSpring(response: 0.24, dampingFraction: 0.9)) {
                        dragOffset = width
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.18) {
                        onBack()
                        dragOffset = 0
                    }
                } else {
                    withAnimation(.interactiveSpring(response: 0.24, dampingFraction: 0.9)) {
                        dragOffset = 0
                    }
                }
            }
    }
#endif
}

struct MyHerzenSettingsCard<Content: View>: View {
    @ViewBuilder let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            content
        }
        .myherzenDefaultSurface()
    }
}

extension View {
    @ViewBuilder
    func myherzenDefaultSurface(cornerRadius: CGFloat = 16, padding: CGFloat = 14) -> some View {
        self.modifier(MyHerzenDefaultSurfaceModifier(cornerRadius: cornerRadius, padding: padding))
    }

    @ViewBuilder
    func myherzenDismissKeyboardOnTap() -> some View {
        self.modifier(MyHerzenDismissKeyboardOnTapModifier())
    }

    @ViewBuilder
    func myherzenInteractiveBackSwipe(
        enabled: Bool = true,
        edgeWidth: CGFloat = 28,
        dismissThreshold: CGFloat = 80,
        onBack: @escaping () -> Void
    ) -> some View {
        self.modifier(
            MyHerzenInteractiveBackSwipeModifier(
                enabled: enabled,
                edgeWidth: edgeWidth,
                dismissThreshold: dismissThreshold,
                onBack: onBack
            )
        )
    }

    @ViewBuilder
    func myherzenGlass() -> some View {
#if os(iOS)
        if #available(iOS 26.0, *) {
            self.glassEffect()
        } else {
            self
        }
#elseif os(macOS)
        if #available(macOS 26.0, *) {
            self.glassEffect()
        } else {
            self
        }
#else
        self
#endif
    }

    @ViewBuilder
    func myherzenGlass<S: Shape>(in shape: S) -> some View {
#if os(iOS)
        if #available(iOS 26.0, *) {
            self.glassEffect(.regular, in: shape)
        } else {
            self
        }
#elseif os(macOS)
        if #available(macOS 26.0, *) {
            self.glassEffect(.regular, in: shape)
        } else {
            self
        }
#else
        self
#endif
    }

    @ViewBuilder
    func myherzenGlassButtonStyle() -> some View {
#if os(iOS)
        if #available(iOS 26.0, *) {
            self
                .buttonStyle(.glass)
                .tint(Color.white.opacity(0.92))
        } else {
            self.buttonStyle(.plain)
        }
#elseif os(macOS)
        if #available(macOS 26.0, *) {
            self.buttonStyle(.glass)
        } else {
            self.buttonStyle(.plain)
        }
#else
        self
#endif
    }

    @ViewBuilder
    func myherzenMaterialBackground() -> some View {
#if os(iOS)
        if #available(iOS 15.0, *) {
            self.background(.ultraThinMaterial)
        } else {
            self.background(Color(UIColor.secondarySystemBackground))
        }
#elseif os(macOS)
        if #available(macOS 12.0, *) {
            self.background(.ultraThinMaterial)
        } else {
            self.background(Color(NSColor.windowBackgroundColor).opacity(0.85))
        }
#else
        self
#endif
    }

    @ViewBuilder
    func myherzenPrimaryForeground() -> some View {
#if os(iOS)
        if #available(iOS 15.0, *) {
            self.foregroundStyle(.primary)
        } else {
            self.foregroundColor(.primary)
        }
#elseif os(macOS)
        if #available(macOS 12.0, *) {
            self.foregroundStyle(.primary)
        } else {
            self.foregroundColor(.primary)
        }
#else
        self
#endif
    }

    @ViewBuilder
    func myherzenInteractiveButtonStyle() -> some View {
        self
            .buttonStyle(.plain)
            .modifier(MyHerzenControlTintModifier())
    }

    @ViewBuilder
    func myherzenControlTintStyle() -> some View {
        self.modifier(MyHerzenControlTintModifier())
    }

    @ViewBuilder
    func myherzenStateCard(cornerRadius: CGFloat = 20, shadowRadius: CGFloat = 5) -> some View {
        self.modifier(MyHerzenStateCardModifier(cornerRadius: cornerRadius, shadowRadius: shadowRadius))
    }

    @ViewBuilder
    func myherzenAdaptiveGlassCard(cornerRadius: CGFloat = 16) -> some View {
        self.modifier(MyHerzenAdaptiveGlassCardModifier(cornerRadius: cornerRadius))
    }

    @ViewBuilder
    func myherzenTask(_ action: @escaping () async -> Void) -> some View {
#if os(macOS)
        if #available(macOS 12.0, *) {
            self.task {
                await action()
            }
        } else {
            self.onAppear {
                Task {
                    await action()
                }
            }
        }
#else
        self.task {
            await action()
        }
#endif
    }

    @ViewBuilder
    func myherzenBottomInset<Inset: View>(@ViewBuilder content: @escaping () -> Inset) -> some View {
#if os(macOS)
        if #available(macOS 12.0, *) {
            self.safeAreaInset(edge: .bottom) {
                content()
            }
        } else {
            VStack(spacing: 0) {
                self
                content()
            }
        }
#else
        self.safeAreaInset(edge: .bottom) {
            content()
        }
#endif
    }

    @ViewBuilder
    func myherzenTextSelectionEnabled() -> some View {
#if os(macOS)
        if #available(macOS 12.0, *) {
            self.textSelection(.enabled)
        } else {
            self
        }
#else
        self.textSelection(.enabled)
#endif
    }

    @ViewBuilder
    func myherzenEmailTextContentType() -> some View {
#if os(iOS)
        self.textContentType(.emailAddress)
#elseif os(macOS)
        if #available(macOS 14.0, *) {
            self.textContentType(.emailAddress)
        } else {
            self
        }
#else
        self
#endif
    }

    @ViewBuilder
    func myherzenNewPasswordTextContentType() -> some View {
#if os(iOS)
        self.textContentType(.newPassword)
#elseif os(macOS)
        if #available(macOS 14.0, *) {
            self.textContentType(.newPassword)
        } else {
            self
        }
#else
        self
#endif
    }
}
