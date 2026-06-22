package ru.moonbaystudio.myherzen.util

import ru.moonbaystudio.myherzen.data.model.ScheduleItem
import ru.moonbaystudio.myherzen.data.remote.dto.AssistantChatMessagePayload
import ru.moonbaystudio.myherzen.data.remote.dto.CachedScheduleLessonPayload
import ru.moonbaystudio.myherzen.data.remote.dto.CachedSchedulePayload
import java.text.SimpleDateFormat
import java.util.*

object AssistantScheduleContextBuilder {
    private val isoFormatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    fun buildCachedSchedule(items: List<ScheduleItem>, source: String = "android_cache"): CachedSchedulePayload {
        return CachedSchedulePayload(
            generatedAt = isoFormatter.format(Date()),
            source = source,
            lessons = items.map {
                CachedScheduleLessonPayload(
                    name = it.title,
                    type = it.lessonType,
                    startTime = it.sortDateIso,
                    endTime = it.endDateIso,
                    date = null,
                    room = it.room,
                    teacher = it.teacher,
                    roomId = null,
                    teacherId = null,
                    classUrl = it.classUrl,
                    note = null,
                    isExam = it.period.trim().isNotEmpty()
                )
            }
        )
    }

    fun buildScheduleText(groupId: Int, date: Date, items: List<ScheduleItem>): String {
        val readableDate = SimpleDateFormat("d MMMM yyyy", Locale("ru")).format(date)
        if (items.isEmpty()) {
            return "Группа: $groupId. Дата: $readableDate. В локальном расписании на эту дату пары не найдены."
        }

        val lines = items.map { item ->
            val parts = mutableListOf("- ${item.time}: ${item.title}")
            if (item.lessonType.trim().isNotBlank()) parts.add("тип: ${item.lessonType}")
            if (item.teacher.trim().isNotBlank()) parts.add("преподаватель: ${item.teacher}")
            if (item.room.trim().isNotBlank()) parts.add("аудитория: ${item.room}")
            else if (item.address.trim().isNotBlank()) parts.add("адрес: ${item.address}")
            if (!item.subgroup.isNullOrBlank()) parts.add("подгруппа: ${item.subgroup.trim()}")
            parts.joinToString("; ")
        }

        return """
            Группа: $groupId. Дата: $readableDate.
            Пары:
            ${lines.joinToString("\n")}
        """.trimIndent()
    }
}

object AssistantPromptBuilder {
    private const val RECENT_MESSAGE_LIMIT = 12

    fun buildMessages(
        persona: String,
        history: List<AssistantChatMessagePayload>,
        scheduleContext: String? = null
    ): List<AssistantChatMessagePayload> {
        val result = mutableListOf<AssistantChatMessagePayload>()

        result.add(AssistantChatMessagePayload("system", systemPrompt(persona)))

        if (history.any { it.role == "assistant" }) {
            result.add(AssistantChatMessagePayload(
                "system",
                "Это уже начатый диалог. Не пиши приветствие, не представляйся заново и не начинай разговор сначала. Ответь сразу по сути последнего сообщения пользователя."
            ))
        }

        if (!scheduleContext.isNullOrBlank()) {
            result.add(AssistantChatMessagePayload(
                "system",
                """
                Контекст расписания из приложения MyHerzen. Используй его для вопросов о парах, занятиях, аудиториях, преподавателях и плане на день. Если в контексте сказано, что данных нет, не выдумывай пары.
                $scheduleContext
                """.trimIndent()
            ))
        }

        val recentHistory = history.takeLast(RECENT_MESSAGE_LIMIT)
        result.addAll(recentHistory)

        return result
    }

    fun buildLegacyMessage(messages: List<AssistantChatMessagePayload>): String {
        return messages.joinToString("\n\n") {
            val label = when (it.role) {
                "system" -> "SYSTEM"
                "assistant" -> "ASSISTANT"
                "user" -> "USER"
                else -> it.role.uppercase()
            }
            "[$label]\n${it.content}"
        }
    }

    private fun systemPrompt(persona: String): String {
        val personaPrompt = when (persona) {
            "stesha" -> "Ты Стеша, спокойный и поддерживающий AI-помощник студентов РГПУ им. Герцена. Отвечай по-русски мягко, ясно и бережно. Помогай структурировать задачи, понимать расписание и снижать тревожность."
            else -> "Ты Пеликаша, живой и дружелюбный AI-помощник студентов РГПУ им. Герцена. Отвечай по-русски, кратко и полезно. Помогай с расписанием, учебными вопросами и навигацией по приложению."
        }

        return """
            $personaPrompt

            Если это не первое сообщение в диалоге, не начинай разговор заново и не повторяй приветствие. Продолжай контекст естественно.
            Не здоровайся в каждом ответе. Не выдумывай расписание или факты; если данных не хватает, честно скажи об этом и предложи, что проверить.
            Отвечай только на русском языке. Не переходи на китайский, английский или другой язык, если пользователь прямо не попросил перевод или ответ на другом языке.
            Не вставляй иностранный текст, служебные фразы, рассуждения о внутренних функциях или технический мусор.
        """.trimIndent()
    }
}
