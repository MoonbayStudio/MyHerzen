import SwiftUI

struct BottomIsland: View {
    @Binding var selectedIndex: Int
    @AppStorage("selectedThemeID") private var selectedThemeID = AppThemeCatalog.default

    private var activeTheme: AppTheme {
        AppThemeCatalog.theme(for: selectedThemeID)
    }

    private let items: [(title: String, icon: String)] = [
        ("Расписание", "calendar"),
        ("AI", "bubble.left.and.bubble.right.fill"),
        ("Сессия", "graduationcap.fill"),
        ("Аккаунт", "person.crop.circle.fill"),
        ("Меню", "line.3.horizontal")
    ]

    var body: some View {
        HStack(spacing: 6) {
            ForEach(items.indices, id: \.self) { index in
                Button {
                    withAnimation(.easeInOut(duration: 0.18)) {
                        selectedIndex = index
                    }
                } label: {
                    VStack(spacing: 3) {
                        Image(systemName: items[index].icon)
                            .font(.system(size: 16, weight: .semibold))
                        Text(items[index].title)
                            .font(.caption2.weight(.medium))
                            .lineLimit(1)
                    }
                    .foregroundColor(selectedIndex == index ? .white : .primary)
                    .frame(maxWidth: .infinity)
                    .frame(height: 54)
                    .background(itemBackground(isSelected: selectedIndex == index))
                    .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                }
                .buttonStyle(.plain)
            }
        }
        .padding(8)
        .frame(maxWidth: 560)
        .myherzenAdaptiveGlassCard(cornerRadius: 26)
        .padding(.horizontal, 12)
    }

    @ViewBuilder
    private func itemBackground(isSelected: Bool) -> some View {
        if isSelected {
            Color.accentColor
        } else if activeTheme.usesCloudSurface {
            activeTheme.cloudSurfaceFill.opacity(0.5)
        } else {
            Color.clear
        }
    }
}
