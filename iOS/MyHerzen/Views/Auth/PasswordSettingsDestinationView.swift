import SwiftUI

struct PasswordSettingsDestinationView: View {
    let activeTheme: AppTheme
    let onBack: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
#if os(iOS)
            MyHerzenTitleBackHeader(shape: activeTheme.headerShape, title: "Пароли и вход", onBack: onBack)
#endif
            MyHerzenSettingsCard {
                Text("Настройки пароля доступны из раздела аккаунта.")
                    .foregroundColor(.secondary)
            }
            Spacer()
        }
        .padding(16)
        .background(ThemedBackground(theme: activeTheme).ignoresSafeArea())
    }
}
