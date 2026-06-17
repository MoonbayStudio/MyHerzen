import SwiftUI

struct DeveloperToolsView: View {
    var onBack: (() -> Void)? = nil
    @AppStorage("selectedThemeID") private var selectedThemeID = AppThemeCatalog.default
    @AppStorage("developerModeEnabled") private var developerModeEnabled = false

    private var activeTheme: AppTheme {
        AppThemeCatalog.theme(for: selectedThemeID)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
#if os(iOS)
            MyHerzenTitleBackHeader(shape: activeTheme.headerShape, title: "Игрушки разработчика") {
                onBack?()
            }
#endif
            MyHerzenSettingsCard {
                Toggle(isOn: $developerModeEnabled) {
                    Label("Режим разработчика", systemImage: "hammer.fill")
                }
                Button {
                    UserDefaults.standard.removeObject(forKey: "institutes_groups_cache.json")
                } label: {
                    Label("Очистить локальные кэши", systemImage: "trash")
                }
                .myherzenInteractiveButtonStyle()
            }
            Spacer()
        }
        .padding(16)
        .background(ThemedBackground(theme: activeTheme).ignoresSafeArea())
    }
}
