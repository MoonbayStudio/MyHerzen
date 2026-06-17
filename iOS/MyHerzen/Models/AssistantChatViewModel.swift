import Foundation
internal import Combine

@MainActor
final class AssistantChatViewModel: ObservableObject {
    @Published var messages: [AssistantMessage] = []
    @Published var inputText = ""
    @Published var isLoading = false
    @Published var selectedPersona: AssistantPersona {
        didSet {
            UserDefaults.standard.set(selectedPersona.rawValue, forKey: "assistantDefaultPersona")
        }
    }
    @Published var remaining: Int?

    private let selectedDateProvider: () -> Date?
    private var currentTask: Task<Void, Never>?
    private var lastUserMessage: String?
    private let conversationID = UUID()

    init(selectedDateProvider: @escaping () -> Date? = { nil }) {
        self.selectedDateProvider = selectedDateProvider
        let rawPersona = UserDefaults.standard.string(forKey: "assistantDefaultPersona")
        self.selectedPersona = AssistantPersona(rawValue: rawPersona ?? "") ?? .pelikasha
    }

    func sendMessage() {
        let text = inputText.myherzenTrimmed
        guard !text.isEmpty, !isLoading else { return }
        inputText = ""
        appendUserMessage(text)
        lastUserMessage = text
        send(text)
    }

    func retryLastMessage() {
        guard !isLoading, let text = lastUserMessage else { return }
        messages.removeAll { $0.role == .systemLocal }
        send(text)
    }

    func appendLocalSystemMessage(_ text: String) {
        messages.append(AssistantMessage(role: .systemLocal, text: text))
    }

    func cancel() {
        currentTask?.cancel()
        currentTask = nil
        isLoading = false
    }

    private func appendUserMessage(_ text: String) {
        messages.append(AssistantMessage(role: .user, text: text))
    }

    private func send(_ text: String) {
        cancel()
        isLoading = true
        let persona = selectedPersona
        let targetDate = selectedDateProvider().map(Self.dateString)
        currentTask = Task { [weak self] in
            do {
                let response = try await AssistantAPIService.shared.sendChatMessage(
                    message: text,
                    persona: persona,
                    conversationId: self?.conversationID.uuidString,
                    groupId: Self.selectedGroupId,
                    targetDate: targetDate,
                    cachedSchedule: nil
                )
                guard !Task.isCancelled else { return }
                self?.remaining = response.remaining
                self?.messages.append(
                    AssistantMessage(role: .assistant, text: response.reply, persona: persona)
                )
            } catch {
                guard !Task.isCancelled else { return }
                self?.appendLocalSystemMessage(Self.errorMessage(for: error))
            }
            self?.isLoading = false
            self?.currentTask = nil
        }
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
