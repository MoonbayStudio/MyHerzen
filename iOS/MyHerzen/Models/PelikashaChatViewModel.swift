import Foundation
internal import Combine

@MainActor
final class PelikashaChatViewModel: ObservableObject {
    struct DialogRecord: Identifiable, Codable, Equatable {
        let id: UUID
        var title: String
        var messages: [PelikashaMessage]
        var updatedAt: Date
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

    init(selectedDateProvider: @escaping () -> Date? = { nil }) {
        self.selectedDateProvider = selectedDateProvider
        let rawPersona = UserDefaults.standard.string(forKey: "assistantDefaultPersona")
        self.selectedPersona = AssistantPersona(rawValue: rawPersona ?? "") ?? .pelikasha
        history = Self.loadHistory(key: historyKey)
        if let first = history.first {
            currentDialogID = first.id
            messages = first.messages
            lastUserMessage = first.messages.last(where: { $0.role == .user })?.text
        } else {
            persistCurrentDialog(title: "Новый диалог")
        }
    }

    func sendMessage() {
        let text = inputText.myherzenTrimmed
        guard !text.isEmpty, !isLoading else { return }
        inputText = ""
        messages.append(PelikashaMessage(role: .user, text: text))
        lastUserMessage = text
        persistCurrentDialog()
        send(text)
    }

    func retryLastMessage() {
        guard !isLoading, let text = lastUserMessage else { return }
        messages.removeAll { $0.role == .systemLocal }
        send(text)
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
        messages = []
        lastUserMessage = nil
        persistCurrentDialog(title: "Новый диалог")
    }

    func openDialog(id: UUID) {
        guard let dialog = history.first(where: { $0.id == id }) else { return }
        cancelCurrentRequest()
        currentDialogID = dialog.id
        messages = dialog.messages
        lastUserMessage = dialog.messages.last(where: { $0.role == .user })?.text
    }

    func deleteDialog(id: UUID) {
        history.removeAll { $0.id == id }
        if currentDialogID == id {
            currentDialogID = UUID()
            messages = []
            lastUserMessage = nil
        }
        saveHistory()
    }

    func clearHistory() {
        history = []
        currentDialogID = UUID()
        messages = []
        lastUserMessage = nil
        saveHistory()
        persistCurrentDialog(title: "Новый диалог")
    }

    private func send(_ text: String) {
        currentTask?.cancel()
        isLoading = true
        let persona = selectedPersona
        let targetDate = selectedDateProvider().map(Self.dateString)
        currentTask = Task { [weak self] in
            do {
                let response = try await AssistantAPIService.shared.sendChatMessage(
                    message: text,
                    persona: persona,
                    conversationId: self?.currentDialogID.uuidString,
                    groupId: Self.selectedGroupId,
                    targetDate: targetDate,
                    cachedSchedule: nil
                )
                guard !Task.isCancelled else { return }
                self?.remaining = response.remaining
                self?.messages.append(PelikashaMessage(role: .assistant, text: response.reply, persona: persona))
            } catch {
                guard !Task.isCancelled else { return }
                self?.appendLocalSystemMessage(Self.errorMessage(for: error))
            }
            self?.isLoading = false
            self?.currentTask = nil
            self?.persistCurrentDialog()
        }
    }

    private func persistCurrentDialog(title explicitTitle: String? = nil) {
        let title = explicitTitle ?? messages.first(where: { $0.role == .user })?.text ?? "Новый диалог"
        let trimmedTitle = Self.normalizedDialogTitle(title)
        let record = DialogRecord(id: currentDialogID, title: trimmedTitle, messages: messages, updatedAt: Date())
        history.removeAll { $0.id == currentDialogID }
        history.insert(record, at: 0)
        history = Array(history.prefix(25))
        saveHistory()
    }

    private func saveHistory() {
        if let data = try? MyHerzenBackendSystem.jsonEncoder.encode(history) {
            UserDefaults.standard.set(data, forKey: historyKey)
        }
    }

    private static func loadHistory(key: String) -> [DialogRecord] {
        guard let data = UserDefaults.standard.data(forKey: key),
              let decoded = try? MyHerzenBackendSystem.jsonDecoder.decode([DialogRecord].self, from: data) else {
            return []
        }
        return decoded.sorted { $0.updatedAt > $1.updatedAt }
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

    private static func dateString(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
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
