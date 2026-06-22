import Foundation

struct AssistantChatMessagePayload: Codable, Equatable {
    let role: String
    let content: String
}

struct PelikashaPromptMessage: Equatable {
    let id: UUID
    let role: String
    let text: String
}

struct PelikashaPromptDialog: Equatable {
    var messages: [PelikashaPromptMessage]
    var summary: String?
    var summarizedMessageIDs: [UUID]
}

struct PelikashaSummaryResult: Equatable {
    let summary: String
    let summarizedMessageIDs: [UUID]
}

enum PelikashaPromptBuilder {
    nonisolated static let recentMessageLimit = 12

    nonisolated static func buildMessages(
        personaRawValue: String,
        dialog: PelikashaPromptDialog,
        scheduleContext: String? = nil
    ) -> [AssistantChatMessagePayload] {
        var result: [AssistantChatMessagePayload] = [
            AssistantChatMessagePayload(role: "system", content: systemPrompt(for: personaRawValue))
        ]

        if dialog.messages.contains(where: { $0.role == "assistant" }) {
            result.append(
                AssistantChatMessagePayload(
                    role: "system",
                    content: "Это уже начатый диалог. Не пиши приветствие, не представляйся заново и не начинай разговор сначала. Ответь сразу по сути последнего сообщения пользователя."
                )
            )
        }

        if let summary = trimmed(dialog.summary), !summary.isEmpty {
            result.append(
                AssistantChatMessagePayload(
                    role: "system",
                    content: """
                    Краткая память предыдущей части диалога. Используй её как контекст, но не пересказывай пользователю без необходимости:
                    \(summary)
                    """
                )
            )
        }

        if let scheduleContext = trimmed(scheduleContext), !scheduleContext.isEmpty {
            result.append(
                AssistantChatMessagePayload(
                    role: "system",
                    content: """
                    Контекст расписания из приложения MyHerzen. Используй его для вопросов о парах, занятиях, аудиториях, преподавателях и плане на день. Если в контексте сказано, что данных нет, не выдумывай пары.
                    \(scheduleContext)
                    """
                )
            )
        }

        let recentMessages = dialog.messages
            .filter { $0.role == "user" || $0.role == "assistant" }
            .suffix(recentMessageLimit)

        result.append(contentsOf: recentMessages.map { message in
            AssistantChatMessagePayload(role: message.role, content: message.text)
        })

        return result
    }

    nonisolated static func legacyMessage(from messages: [AssistantChatMessagePayload]) -> String {
        messages.map { message in
            let label: String
            switch message.role {
            case "system":
                label = "SYSTEM"
            case "assistant":
                label = "ASSISTANT"
            case "user":
                label = "USER"
            default:
                label = message.role.uppercased()
            }
            return "[\(label)]\n\(message.content)"
        }
        .joined(separator: "\n\n")
    }

    nonisolated private static func systemPrompt(for personaRawValue: String) -> String {
        let personaPrompt: String
        switch personaRawValue {
        case "stesha":
            personaPrompt = """
            Ты Стеша, спокойный и поддерживающий AI-помощник студентов РГПУ им. Герцена. Отвечай по-русски мягко, ясно и бережно. Помогай структурировать задачи, понимать расписание и снижать тревожность.
            """
        default:
            personaPrompt = """
            Ты Пеликаша, живой и дружелюбный AI-помощник студентов РГПУ им. Герцена. Отвечай по-русски, кратко и полезно. Помогай с расписанием, учебными вопросами и навигацией по приложению.
            """
        }

        return """
        \(personaPrompt)

        Если это не первое сообщение в диалоге, не начинай разговор заново и не повторяй приветствие. Продолжай контекст естественно.
        Не здоровайся в каждом ответе. Не выдумывай расписание или факты; если данных не хватает, честно скажи об этом и предложи, что проверить.
        Отвечай только на русском языке. Не переходи на китайский, английский или другой язык, если пользователь прямо не попросил перевод или ответ на другом языке.
        Не вставляй иностранный текст, служебные фразы, рассуждения о внутренних функциях или технический мусор.
        """
    }

    nonisolated private static func trimmed(_ value: String?) -> String? {
        value?.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

enum PelikashaConversationSummaryService {
    nonisolated static let recentMessageLimit = 12
    nonisolated static let minimumUnsummarizedMessages = 20

    nonisolated static func summarizeIfNeeded(_ dialog: PelikashaPromptDialog) -> PelikashaSummaryResult? {
        let conversationalMessages = dialog.messages.filter { $0.role == "user" || $0.role == "assistant" }
        let summarizedIDs = Set(dialog.summarizedMessageIDs)
        let unsummarized = conversationalMessages.filter { !summarizedIDs.contains($0.id) }

        guard unsummarized.count > minimumUnsummarizedMessages else {
            return nil
        }

        let messagesToSummarize = Array(unsummarized.dropLast(recentMessageLimit))
        guard !messagesToSummarize.isEmpty else {
            return nil
        }

        return PelikashaSummaryResult(
            summary: mergedSummary(existing: dialog.summary, messages: messagesToSummarize),
            summarizedMessageIDs: Array(summarizedIDs.union(messagesToSummarize.map(\.id)))
        )
    }

    nonisolated private static func mergedSummary(existing: String?, messages: [PelikashaPromptMessage]) -> String {
        var sections: [String] = []
        if let existing = existing?.trimmingCharacters(in: .whitespacesAndNewlines), !existing.isEmpty {
            sections.append(existing)
        }

        let compactLines = messages
            .compactMap(summaryLine(for:))
            .prefix(16)

        if !compactLines.isEmpty {
            sections.append(
                """
                Обновление памяти:
                \(compactLines.joined(separator: "\n"))
                """
            )
        }

        return sections
            .joined(separator: "\n\n")
            .split(separator: "\n")
            .prefix(80)
            .joined(separator: "\n")
    }

    nonisolated private static func summaryLine(for message: PelikashaPromptMessage) -> String? {
        let text = message.text
            .replacingOccurrences(of: "\n", with: " ")
            .split(separator: " ")
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        guard !text.isEmpty else { return nil }

        switch message.role {
        case "user":
            return "- Пользователь: \(String(text.prefix(220)))"
        case "assistant":
            return "- Ассистент: \(String(text.prefix(220)))"
        default:
            return nil
        }
    }
}
