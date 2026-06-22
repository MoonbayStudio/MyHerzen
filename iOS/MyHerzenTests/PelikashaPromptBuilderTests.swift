import Foundation
import Testing
@testable import MyHerzen

@MainActor
struct PelikashaPromptBuilderTests {
    @Test
    func promptBuilderIncludesSummaryAndRecentMessagesOnly() {
        let messages = (0..<30).flatMap { index in
            [
                PelikashaPromptMessage(id: UUID(), role: "user", text: "Вопрос \(index)"),
                PelikashaPromptMessage(id: UUID(), role: "assistant", text: "Ответ \(index)")
            ]
        }
        let dialog = PelikashaPromptDialog(
            messages: messages,
            summary: "Пользователь готовится к сессии.",
            summarizedMessageIDs: []
        )

        let prompt = PelikashaPromptBuilder.buildMessages(personaRawValue: "pelikasha", dialog: dialog)

        #expect(prompt.first?.role == "system")
        #expect(prompt.contains { $0.content.contains("Пользователь готовится к сессии") })
        #expect(prompt.contains { $0.content == "Вопрос 29" })
        #expect(prompt.contains { $0.content == "Ответ 29" })
        #expect(!prompt.contains { $0.content == "Вопрос 0" })
        #expect(prompt.contains { $0.content.contains("Это уже начатый диалог") })
        #expect(prompt.count == 15)
    }

    @Test
    func summaryServiceMarksOnlyOldMessagesAsSummarized() {
        let messages = (0..<26).map { index in
            PelikashaPromptMessage(id: UUID(), role: index.isMultiple(of: 2) ? "user" : "assistant", text: "Сообщение \(index)")
        }
        let dialog = PelikashaPromptDialog(
            messages: messages,
            summary: nil,
            summarizedMessageIDs: []
        )

        let summarized = PelikashaConversationSummaryService.summarizeIfNeeded(dialog)

        #expect(summarized?.summary.isEmpty == false)
        #expect(summarized?.summarizedMessageIDs.count == 14)
    }
}
