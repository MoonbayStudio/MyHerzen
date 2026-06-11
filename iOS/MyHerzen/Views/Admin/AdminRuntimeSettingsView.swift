import SwiftUI
internal import Combine

@MainActor
final class AdminRuntimeSettingsViewModel: ObservableObject {
    @Published var settings: [AdminRuntimeSetting] = []
    @Published var drafts: [String: RuntimeSettingValue] = [:]
    @Published var isLoading = false
    @Published var processingKey: String?
    @Published var errorMessage: String?
    @Published var successMessage: String?

    private let whitelist = Set(["AI_ENABLED", "AI_DAILY_LIMIT", "PERSONA_THEME", "MAINTENANCE_MODE", "SCHEDULE_CACHE_TTL_SECONDS"])

    var visibleSettings: [AdminRuntimeSetting] {
        settings.filter { whitelist.contains($0.key) }.sorted { $0.key < $1.key }
    }

    func load() async {
        guard !isLoading else { return }
        isLoading = true
        errorMessage = nil
        do {
            settings = try await APIService.shared.fetchAdminSettings()
            drafts = Dictionary(uniqueKeysWithValues: visibleSettings.map { ($0.key, $0.value) })
        } catch {
            errorMessage = Self.message(for: error)
        }
        isLoading = false
    }

    func save(key: String) async {
        guard processingKey == nil, let value = drafts[key] else { return }
        processingKey = key
        errorMessage = nil
        successMessage = nil
        do {
            let updated = try await APIService.shared.updateAdminSetting(key: key, value: normalized(value, for: key))
            if let index = settings.firstIndex(where: { $0.key == key }) {
                settings[index] = updated
            } else {
                settings.append(updated)
            }
            drafts[key] = updated.value
            successMessage = "Настройка сохранена."
            if ["AI_ENABLED", "AI_DAILY_LIMIT", "PERSONA_THEME", "MAINTENANCE_MODE", "SCHEDULE_CACHE_TTL_SECONDS"].contains(key) {
                await RuntimeConfigService.shared.refresh(force: true)
            }
        } catch {
            errorMessage = Self.message(for: error)
        }
        processingKey = nil
    }

    private func normalized(_ value: RuntimeSettingValue, for key: String) -> RuntimeSettingValue {
        switch (key, value) {
        case ("AI_DAILY_LIMIT", .int(let value)), ("SCHEDULE_CACHE_TTL_SECONDS", .int(let value)):
            return .int(max(0, value))
        default:
            return value
        }
    }

    private static func message(for error: Error) -> String {
        if let urlError = error as? URLError, urlError.code != .cancelled {
            return "Сеть недоступна. Попробуйте ещё раз."
        }
        if case APIServiceError.httpStatusWithBody(let statusCode, _) = error {
            return message(forHTTPStatus: statusCode)
        }
        if case APIServiceError.httpStatus(let statusCode) = error {
            return message(forHTTPStatus: statusCode)
        }
        return "Не удалось выполнить действие."
    }

    private static func message(forHTTPStatus statusCode: Int) -> String {
        switch statusCode {
        case 401, 403: return "Недостаточно прав для админки."
        case 422: return "Backend не принял значение настройки."
        case 404: return "Endpoint настроек пока недоступен."
        default: return "Backend вернул ошибку \(statusCode)."
        }
    }
}

struct AdminRuntimeSettingsView: View {
    let activeTheme: AppTheme
    let onBack: () -> Void

    @StateObject private var viewModel = AdminRuntimeSettingsViewModel()

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            header
            statusArea
            content
        }
        .padding(.horizontal, 16)
        .padding(.top, 16)
        .padding(.bottom, 24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(ThemedBackground(theme: activeTheme).ignoresSafeArea())
        .myherzenTask { await viewModel.load() }
    }

    private var header: some View {
        HStack(spacing: 10) {
#if os(iOS)
            MyHerzenTitleBackHeader(shape: activeTheme.headerShape, title: "Настройки") {
                onBack()
            }
#endif
            Spacer(minLength: 0)
            Button {
                Task { await viewModel.load() }
            } label: {
                Image(systemName: "arrow.clockwise")
                    .frame(width: 36, height: 36)
            }
            .buttonStyle(.plain)
            .myherzenDefaultSurface(cornerRadius: 18, padding: 0)
            .disabled(viewModel.isLoading)
        }
    }

    @ViewBuilder
    private var statusArea: some View {
        if viewModel.isLoading && viewModel.settings.isEmpty {
            HStack(spacing: 8) {
                ProgressView()
                Text("Загружаем настройки")
                    .foregroundColor(.secondary)
            }
            .font(.subheadline)
            .padding(.horizontal, 4)
        }
        if let successMessage = viewModel.successMessage {
            Label(successMessage, systemImage: "checkmark.circle.fill")
                .font(.caption.weight(.semibold))
                .foregroundColor(.green)
                .padding(.horizontal, 4)
        }
        if let errorMessage = viewModel.errorMessage {
            Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                .font(.caption.weight(.semibold))
                .foregroundColor(.red)
                .padding(.horizontal, 4)
        }
    }

    @ViewBuilder
    private var content: some View {
        if !viewModel.isLoading && viewModel.visibleSettings.isEmpty {
            VStack(alignment: .leading, spacing: 8) {
                Image(systemName: "slider.horizontal.3")
                    .font(.system(size: 28, weight: .medium))
                    .foregroundColor(.accentColor)
                Text("Настроек пока нет.")
                    .font(.headline)
                Text("Отображаются только whitelisted runtime-настройки.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(16)
            .myherzenAdaptiveGlassCard(cornerRadius: 16)
            .padding(.horizontal, 4)
        } else {
            ScrollView {
                LazyVStack(spacing: 10) {
                    ForEach(viewModel.visibleSettings) { setting in
                        AdminRuntimeSettingRow(
                            setting: setting,
                            draft: Binding(
                                get: { viewModel.drafts[setting.key] ?? setting.value },
                                set: { viewModel.drafts[setting.key] = $0 }
                            ),
                            isProcessing: viewModel.processingKey == setting.key,
                            onSave: { Task { await viewModel.save(key: setting.key) } }
                        )
                    }
                }
                .padding(.horizontal, 4)
                .padding(.bottom, 24)
            }
        }
    }
}

private struct AdminRuntimeSettingRow: View {
    let setting: AdminRuntimeSetting
    @Binding var draft: RuntimeSettingValue
    let isProcessing: Bool
    let onSave: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(.subheadline.weight(.semibold))
                    Text(setting.key)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                Spacer(minLength: 0)
                if isProcessing {
                    ProgressView()
                        .scaleEffect(0.8)
                }
            }

            editor

            Button("Сохранить", action: onSave)
                .font(.caption.weight(.semibold))
                .disabled(isProcessing || draft == setting.value)
        }
        .myherzenDefaultSurface(cornerRadius: 16, padding: 12)
    }

    @ViewBuilder
    private var editor: some View {
        switch draft {
        case .bool:
            Toggle("Значение", isOn: boolBinding)
        case .int:
            TextField("0", text: intBinding)
                .textFieldStyle(.roundedBorder)
#if os(iOS)
                .keyboardType(.numberPad)
#endif
        case .string:
            if setting.key == "PERSONA_THEME" {
                Picker("Значение", selection: stringBinding) {
                    Text("auto").tag("auto")
                    Text("pelikasha").tag("pelikasha")
                    Text("stesha").tag("stesha")
                }
                .pickerStyle(.segmented)
            } else {
                TextField("Значение", text: stringBinding)
                    .textFieldStyle(.roundedBorder)
            }
        }
    }

    private var boolBinding: Binding<Bool> {
        Binding(
            get: {
                if case .bool(let value) = draft { return value }
                return false
            },
            set: { draft = .bool($0) }
        )
    }

    private var intBinding: Binding<String> {
        Binding(
            get: {
                if case .int(let value) = draft { return String(max(0, value)) }
                return "0"
            },
            set: { draft = .int(max(0, Int($0.filter(\.isNumber)) ?? 0)) }
        )
    }

    private var stringBinding: Binding<String> {
        Binding(
            get: {
                if case .string(let value) = draft { return value }
                return ""
            },
            set: { draft = .string($0) }
        )
    }

    private var title: String {
        switch setting.key {
        case "AI_ENABLED": return "AI включён"
        case "AI_DAILY_LIMIT": return "Дневной лимит AI"
        case "PERSONA_THEME": return "Тема персонажа"
        case "MAINTENANCE_MODE": return "Режим техработ"
        case "SCHEDULE_CACHE_TTL_SECONDS": return "TTL кэша расписания"
        default: return setting.key
        }
    }
}
