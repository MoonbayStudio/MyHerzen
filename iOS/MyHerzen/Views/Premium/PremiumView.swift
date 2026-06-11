import SwiftUI

struct PremiumView: View {
    @Environment(\.presentationMode) private var presentationMode
    @AppStorage("selectedThemeID") private var selectedThemeID = AppThemeCatalog.default
    @StateObject private var subscriptionManager = SubscriptionManager.shared
    var showsHeader = true
    var onBack: (() -> Void)? = nil

    private var activeTheme: AppTheme { AppThemeCatalog.theme(for: selectedThemeID) }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if showsHeader {
#if os(iOS)
                    header
#endif
                }

                VStack(alignment: .leading, spacing: 12) {
                    Label("Премиум открывает доступ к кастомным темам", systemImage: "sparkles")
                        .font(.body)
                    Label("Midnight Glass, Polar Light, Neon Campus", systemImage: "paintpalette.fill")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .myherzenDefaultSurface()

                VStack(alignment: .leading, spacing: 10) {
                    if let product = subscriptionManager.products.first {
                        Button {
                            Task { await subscriptionManager.purchase() }
                        } label: {
                            HStack {
                                Label(subscriptionManager.hasPremium ? "Подписка активна" : "Оформить подписку", systemImage: "crown.fill")
                                Spacer()
                                if !subscriptionManager.hasPremium {
                                    Text(product.displayPrice)
                                        .foregroundColor(.secondary)
                                }
                            }
                            .myherzenDefaultSurface()
                        }
                        .myherzenInteractiveButtonStyle()
                        .disabled(subscriptionManager.hasPremium || subscriptionManager.isLoading)
                    } else {
                        Text("Продукты премиума недоступны в текущем окружении.")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                    Button {
                        Task { await subscriptionManager.restorePurchases() }
                    } label: {
                        Label("Восстановить покупки", systemImage: "arrow.clockwise")
                            .myherzenDefaultSurface()
                    }
                    .myherzenInteractiveButtonStyle()
                    .disabled(subscriptionManager.isLoading)

                    if let error = subscriptionManager.errorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }
                .myherzenDefaultSurface()
            }
            .padding(.horizontal, 16)
            .padding(.top, 16)
            .padding(.bottom, 24)
        }
        .background(ThemedBackground(theme: activeTheme).ignoresSafeArea())
#if os(iOS)
        .navigationBarBackButtonHidden(true)
        .navigationBarHidden(true)
#endif
        .onAppear {
            Task { await subscriptionManager.bootstrap() }
        }
    }

    @ViewBuilder
    private var header: some View {
        MyHerzenTitleBackHeader(
            shape: activeTheme.headerShape,
            title: "Мой Герцена Плюс/Премиум",
            onBack: { dismissView() }
        )
    }

    private func dismissView() {
        if let onBack {
            onBack()
        } else {
            presentationMode.wrappedValue.dismiss()
        }
    }
}
