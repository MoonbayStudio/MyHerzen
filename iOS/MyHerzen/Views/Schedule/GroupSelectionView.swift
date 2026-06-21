import SwiftUI

struct GroupSelectionView: View {
    @Binding var selectedGroup: MyGroup?
    @Binding var menuTitle: String
    @Binding var selectedMenuSubView: ContentView.MenuSubView?
    @ObservedObject var viewModel: ScheduleViewModel
    var onBack: (() -> Void)? = nil

    @AppStorage("selectedThemeID") private var selectedThemeID = AppThemeCatalog.default
    @State private var institutes: [Institute] = []
    @State private var searchText = ""
    @State private var isLoading = false

    private var activeTheme: AppTheme {
        AppThemeCatalog.theme(for: selectedThemeID)
    }

    private var filteredGroups: [MyGroup] {
        let allGroups = institutes.flatMap(\.groups)
        let query = searchText.myherzenTrimmed.lowercased()
        guard !query.isEmpty else { return allGroups }
        return allGroups.filter {
            $0.name.lowercased().contains(query) || $0.id.lowercased().contains(query)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
#if os(iOS)
            MyHerzenTitleBackHeader(shape: activeTheme.headerShape, title: "Выбор группы") {
                dismiss()
            }
#endif

            TextField("Найти группу", text: $searchText)
                .textFieldStyle(.plain)
                .padding(12)
                .myherzenDefaultSurface(cornerRadius: 14, padding: 0)

            if isLoading {
                ProgressView("Загружаем группы")
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.top, 24)
            } else {
                List(filteredGroups) { group in
                    Button {
                        select(group)
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(group.name)
                                    .font(.body.weight(.semibold))
                                Text("ID \(group.id)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                            if selectedGroup?.id == group.id || viewModel.savedGroupId == group.id {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundColor(.accentColor)
                            }
                        }
                    }
                    .buttonStyle(.plain)
                }
                .listStyle(.plain)
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 16)
        .background(ThemedBackground(theme: activeTheme).ignoresSafeArea())
        .onAppear {
            Task {
                await loadGroups()
            }
        }
    }

    private func loadGroups() async {
        guard institutes.isEmpty else { return }
        isLoading = true
        let cached = APIService.shared.fetchCachedInstitutesWithGroups()
        if !cached.isEmpty {
            institutes = cached
        }
        let loaded = await APIService.shared.fetchInstitutesWithGroups()
        if !loaded.isEmpty {
            institutes = loaded
        }
        isLoading = false
    }

    private func select(_ group: MyGroup) {
        selectedGroup = group
        viewModel.savedGroupId = group.id
        UserDefaults.standard.set(group.name, forKey: "selectedGroupName")
        Task {
            await UserSettingsSyncService.updateRemoteSelectedGroupIfAuthenticated(group)
        }
        dismiss()
    }

    private func dismiss() {
        if let onBack {
            onBack()
        } else {
            withAnimation(.easeInOut(duration: 0.18)) {
                selectedMenuSubView = nil
                menuTitle = "Меню"
            }
        }
    }
}
