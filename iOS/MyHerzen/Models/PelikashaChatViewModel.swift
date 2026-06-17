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
    @Published private(set) var history: [DialogRecord] = []
    @Published private(set) var currentDialogID: UUID = UUID()

    private var currentTask: Task<Void, Never>?
    private let historyKey = "pelikashaChatHistory"

    init() {
        history = Self.loadHistory(key: historyKey)
        if let first = history.first {
            currentDialogID = first.id
            messages = first.messages
        } else {
            persistCurrentDialog(title: "Новый диалог")
        }
    }

    func sendMessage() {
        let text = inputText.myherzenTrimmed
        guard !text.isEmpty, !isLoading else { return }
        inputText = ""
        messages.append(PelikashaMessage(role: .user, text: text))
        persistCurrentDialog()
        send(text)
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
        persistCurrentDialog(title: "Новый диалог")
    }

    func openDialog(id: UUID) {
        guard let dialog = history.first(where: { $0.id == id }) else { return }
        cancelCurrentRequest()
        currentDialogID = dialog.id
        messages = dialog.messages
    }

    func deleteDialog(id: UUID) {
        history.removeAll { $0.id == id }
        if currentDialogID == id {
            currentDialogID = UUID()
            messages = []
        }
        saveHistory()
    }

    func clearHistory() {
        history = []
        currentDialogID = UUID()
        messages = []
        saveHistory()
        persistCurrentDialog(title: "Новый диалог")
    }

    private func send(_ text: String) {
        currentTask?.cancel()
        isLoading = true
        currentTask = Task { [weak self] in
            do {
                let reply = try await PelikashaService.shared.send(text, conversationId: self?.currentDialogID ?? UUID())
                guard !Task.isCancelled else { return }
                self?.messages.append(PelikashaMessage(role: .assistant, text: reply))
            } catch {
                guard !Task.isCancelled else { return }
                self?.messages.append(PelikashaMessage(role: .assistant, text: "Не получилось ответить. Попробуй ещё раз."))
            }
            self?.isLoading = false
            self?.currentTask = nil
            self?.persistCurrentDialog()
        }
    }

    private func persistCurrentDialog(title explicitTitle: String? = nil) {
        let title = explicitTitle ?? messages.first(where: { $0.role == .user })?.text ?? "Новый диалог"
        let trimmedTitle = String(title.prefix(48))
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
}
