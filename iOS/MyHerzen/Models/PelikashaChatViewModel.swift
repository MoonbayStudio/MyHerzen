import Foundation
internal import Combine

@MainActor
final class PelikashaChatViewModel: ObservableObject {
    struct DialogRecord: Identifiable, Codable, Equatable {
        let id: UUID
        var title: String
        var messages: [PelikashaMessage]
        var updatedAt: Date
        var summary: String?
        var summarizedMessageIDs: [UUID]?
    }

    private struct ScheduleContext {
        let text: String?
        let cachedPayload: CachedSchedulePayload?
    }

    @Published var messages: [PelikashaMessage] = []
    @Published var inputText = ""
    @Published var isLoading = false
    @Published var isCancelling = false
    @Published var selectedPersona: AssistantPersona {
        didSet {
            UserDefaults.standard.set(selectedPersona.rawValue, forKey: "assistantDefaultPersona")
        }
    }
    @Published var remaining: Int?
    @Published private(set) var history: [DialogRecord] = []
    @Published private(set) var currentDialogID: UUID = UUID()

    private let selectedDateProvider: () -> Date?
    private var currentTask: Task<Void, Never>?
    private var lastUserMessage: String?
    private let historyKey = "pelikashaChatHistory"
    private let activeDialogIDKey = "pelikashaActiveDialogID"

    init(selectedDateProvider: @escaping () -> Date? = { nil }) {
        self.selectedDateProvider = selectedDateProvider
        let rawPersona = UserDefaults.standard.string(forKey: "assistantDefaultPersona")
        self.selectedPersona = AssistantPersona(rawValue: rawPersona ?? "") ?? .pelikasha
        history = Self.loadHistory(key: historyKey)
        if let activeID = Self.loadActiveDialogID(key: activeDialogIDKey),
           let activeDialog = history.first(where: { $0.id == activeID }) {
            applyActiveDialog(activeDialog)
        } else if let first = history.first {
            applyActiveDialog(first)
        } else {
            persistCurrentDialog(title: "Новый диалог")
        }
    }

    func sendMessage() {
        let text = inputText.myherzenTrimmed
        guard !text.isEmpty, !isLoading else { return }
        inputText = ""
        ensureActiveConversation()
        messages.append(PelikashaMessage(role: .user, text: text))
        lastUserMessage = text
        let dialog = persistCurrentDialog()
        send(promptDialog: promptDialog(from: dialog))
    }

    func retryLastMessage() {
        guard !isLoading, lastUserMessage != nil else { return }
        messages.removeAll { $0.role == .systemLocal }
        let dialog = persistCurrentDialog()
        send(promptDialog: promptDialog(from: dialog))
    }

    func appendLocalSystemMessage(_ text: String) {
        messages.append(PelikashaMessage(role: .systemLocal, text: text))
        persistCurrentDialog()
    }

    func cancelCurrentRequest() {
        isCancelling = true
        currentTask?.cancel()
        currentTask = nil
        isLoading = false
        isCancelling = false
    }

    func startNewDialog() {
        cancelCurrentRequest()
        currentDialogID = UUID()
        saveActiveDialogID()
        messages = []
        lastUserMessage = nil
        persistCurrentDialog(title: "Новый диалог")
    }

    func openDialog(id: UUID) {
        guard let dialog = history.first(where: { $0.id == id }) else { return }
        cancelCurrentRequest()
        applyActiveDialog(dialog)
    }

    func deleteDialog(id: UUID) {
        history.removeAll { $0.id == id }
        if currentDialogID == id {
            if let latest = history.first {
                applyActiveDialog(latest)
            } else {
                currentDialogID = UUID()
                saveActiveDialogID()
                messages = []
                lastUserMessage = nil
                persistCurrentDialog(title: "Новый диалог")
            }
        }
        saveHistory()
    }

    func clearHistory() {
        history = []
        currentDialogID = UUID()
        saveActiveDialogID()
        messages = []
        lastUserMessage = nil
        saveHistory()
        persistCurrentDialog(title: "Новый диалог")
    }

    private func send(promptDialog: PelikashaPromptDialog) {
        currentTask?.cancel()
        isLoading = true
        let persona = selectedPersona
        let targetDateValue = selectedDateProvider() ?? Date()
        let targetDate = Self.dateString(targetDateValue)
        let groupId = Self.selectedGroupId
        currentTask = Task { [weak self] in
            do {
                let scheduleContext = await Self.scheduleContext(groupId: groupId, date: targetDateValue)
                let promptMessages = PelikashaPromptBuilder.buildMessages(
                    personaRawValue: persona.rawValue,
                    dialog: promptDialog,
                    scheduleContext: scheduleContext.text
                )
                let contextualMessage = PelikashaPromptBuilder.legacyMessage(from: promptMessages)
                let response = try await AssistantAPIService.shared.sendChatMessage(
                    message: contextualMessage,
                    persona: persona,
                    messages: promptMessages,
                    conversationId: self?.currentDialogID.uuidString,
                    groupId: groupId,
                    targetDate: targetDate,
                    cachedSchedule: scheduleContext.cachedPayload
                )
                guard !Task.isCancelled else { return }
                self?.remaining = response.remaining
                self?.messages.append(PelikashaMessage(role: .assistant, text: response.reply, persona: persona))
                self?.persistCurrentDialog()
                self?.summarizeCurrentDialogIfNeeded()
            } catch {
                guard !Task.isCancelled else { return }
                self?.appendLocalSystemMessage(Self.errorMessage(for: error))
            }
            self?.isLoading = false
            self?.currentTask = nil
        }
    }

    @discardableResult
    private func persistCurrentDialog(title explicitTitle: String? = nil) -> DialogRecord {
        let title = explicitTitle ?? messages.first(where: { $0.role == .user })?.text ?? "Новый диалог"
        let trimmedTitle = Self.normalizedDialogTitle(title)
        let existing = history.first { $0.id == currentDialogID }
        let record = DialogRecord(
            id: currentDialogID,
            title: trimmedTitle,
            messages: messages,
            updatedAt: Date(),
            summary: existing?.summary,
            summarizedMessageIDs: existing?.summarizedMessageIDs
        )
        history.removeAll { $0.id == currentDialogID }
        history.insert(record, at: 0)
        history = Array(history.prefix(25))
        saveActiveDialogID()
        saveHistory()
        return record
    }

    private func summarizeCurrentDialogIfNeeded() {
        guard let current = history.first(where: { $0.id == currentDialogID }) else { return }
        guard let summaryResult = PelikashaConversationSummaryService.summarizeIfNeeded(promptDialog(from: current)) else { return }
        var updated = current
        updated.summary = summaryResult.summary
        updated.summarizedMessageIDs = summaryResult.summarizedMessageIDs
        history.removeAll { $0.id == currentDialogID }
        history.insert(updated, at: 0)
        saveHistory()
    }

    private func promptDialog(from dialog: DialogRecord) -> PelikashaPromptDialog {
        PelikashaPromptDialog(
            messages: dialog.messages.map { message in
                PelikashaPromptMessage(id: message.id, role: message.role.rawValue, text: message.text)
            },
            summary: dialog.summary,
            summarizedMessageIDs: dialog.summarizedMessageIDs ?? []
        )
    }

    private func saveHistory() {
        if let data = try? MyHerzenBackendSystem.jsonEncoder.encode(history) {
            UserDefaults.standard.set(data, forKey: historyKey)
        }
    }

    private func saveActiveDialogID() {
        UserDefaults.standard.set(currentDialogID.uuidString, forKey: activeDialogIDKey)
    }

    @discardableResult
    private func ensureActiveConversation() -> UUID {
        if history.contains(where: { $0.id == currentDialogID }) {
            saveActiveDialogID()
            return currentDialogID
        }

        if !messages.isEmpty {
            persistCurrentDialog()
            return currentDialogID
        }

        if let latest = history.first {
            applyActiveDialog(latest)
        } else {
            currentDialogID = UUID()
            saveActiveDialogID()
            persistCurrentDialog(title: "Новый диалог")
        }

        return currentDialogID
    }

    private func applyActiveDialog(_ dialog: DialogRecord) {
        currentDialogID = dialog.id
        saveActiveDialogID()
        messages = dialog.messages
        lastUserMessage = dialog.messages.last(where: { $0.role == .user })?.text
    }

    private static func loadHistory(key: String) -> [DialogRecord] {
        guard let data = UserDefaults.standard.data(forKey: key),
              let decoded = try? MyHerzenBackendSystem.jsonDecoder.decode([DialogRecord].self, from: data) else {
            return []
        }
        return decoded.sorted { $0.updatedAt > $1.updatedAt }
    }

    private static func loadActiveDialogID(key: String) -> UUID? {
        guard let rawValue = UserDefaults.standard.string(forKey: key) else { return nil }
        return UUID(uuidString: rawValue)
    }

    private static func normalizedDialogTitle(_ title: String) -> String {
        let oneLine = title
            .replacingOccurrences(of: "\n", with: " ")
            .split(separator: " ")
            .joined(separator: " ")
        return oneLine.isEmpty ? "Новый диалог" : String(oneLine.prefix(120))
    }

    private static var selectedGroupId: Int? {
        let value = UserDefaults.standard.string(forKey: "selectedGroupId") ?? ""
        return Int(value)
    }

    private static func scheduleContext(groupId: Int?, date: Date) async -> ScheduleContext {
        guard let groupId else {
            return ScheduleContext(
                text: "Группа пользователя не выбрана, поэтому точное расписание пар недоступно.",
                cachedPayload: nil
            )
        }

        let groupIdString = String(groupId)
        let items = await APIService.shared.fetchSchedule(for: groupIdString, date: date)
        let readableDate = readableDateString(date)

        guard !items.isEmpty else {
            return ScheduleContext(
                text: "Группа: \(groupIdString). Дата: \(readableDate). В локальном расписании на эту дату пары не найдены.",
                cachedPayload: nil
            )
        }

        let lines = items.map { item in
            var parts = ["- \(item.time): \(item.title)"]
            if !item.lessonType.myherzenTrimmed.isEmpty {
                parts.append("тип: \(item.lessonType)")
            }
            if !item.teacher.myherzenTrimmed.isEmpty {
                parts.append("преподаватель: \(item.teacher)")
            }
            if !item.room.myherzenTrimmed.isEmpty {
                parts.append("аудитория: \(item.room)")
            } else if !item.address.myherzenTrimmed.isEmpty {
                parts.append("адрес: \(item.address)")
            }
            if let subgroup = item.subgroup?.myherzenTrimmed, !subgroup.isEmpty {
                parts.append("подгруппа: \(subgroup)")
            }
            return parts.joined(separator: "; ")
        }

        return ScheduleContext(
            text: """
            Группа: \(groupIdString). Дата: \(readableDate).
            Пары:
            \(lines.joined(separator: "\n"))
            """,
            cachedPayload: PelikashaScheduleContextBuilder.cachedSchedule(from: items, date: date)
        )
    }

    private static func dateString(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }

    private static func readableDateString(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.dateFormat = "d MMMM yyyy"
        return formatter.string(from: date)
    }

    private static func errorMessage(for error: Error) -> String {
        if let apiError = error as? APIServiceError {
            return apiError.localizedDescription
        }
        if let urlError = error as? URLError, urlError.code != .cancelled {
            return "Не удалось подключиться к AI-сервису. Проверь сеть и попробуй ещё раз."
        }
        return "Не удалось получить ответ. Попробуй ещё раз."
    }
}
