package ru.moonbaystudio.myherzen.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.data.local.preferences.UserPreferences
import ru.moonbaystudio.myherzen.data.model.AssistantMessage
import ru.moonbaystudio.myherzen.data.model.AssistantPersona
import ru.moonbaystudio.myherzen.data.remote.MyHerzenApiService
import ru.moonbaystudio.myherzen.data.remote.dto.*
import ru.moonbaystudio.myherzen.data.repository.ScheduleRepository
import ru.moonbaystudio.myherzen.util.AssistantPromptBuilder
import ru.moonbaystudio.myherzen.util.AssistantScheduleContextBuilder
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject

@HiltViewModel
class AssistantViewModel @Inject constructor(
    private val apiService: MyHerzenApiService,
    private val scheduleRepository: ScheduleRepository,
    private val userPreferences: UserPreferences
) : ViewModel() {

    private val gson = Gson()
    private val _messages = MutableStateFlow<List<AssistantMessage>>(emptyList())
    val messages: StateFlow<List<AssistantMessage>> = _messages.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _inputText = MutableStateFlow("")
    val inputText: StateFlow<String> = _inputText.asStateFlow()

    private val _selectedPersona = MutableStateFlow(AssistantPersona.PELIKASHA)
    val selectedPersona: StateFlow<AssistantPersona> = _selectedPersona.asStateFlow()

    private val conversationId = UUID.randomUUID().toString()
    private val requestDateFormatter = SimpleDateFormat("yyyy-MM-dd", Locale.US)

    init {
        viewModelScope.launch {
            val historyJson = userPreferences.assistantHistory.first()
            if (!historyJson.isNullOrBlank()) {
                try {
                    val type = object : TypeToken<List<AssistantMessage>>() {}.type
                    val history: List<AssistantMessage> = gson.fromJson(historyJson, type)
                    _messages.value = history
                } catch (e: Exception) {
                    _messages.value = emptyList()
                }
            }
        }
    }

    private fun saveHistory() {
        viewModelScope.launch {
            val historyJson = gson.toJson(_messages.value.takeLast(50)) // Keep last 50 messages
            userPreferences.saveAssistantHistory(historyJson)
        }
    }

    fun setInputText(text: String) {
        _inputText.value = text
    }

    fun setPersona(persona: AssistantPersona) {
        _selectedPersona.value = persona
    }

    fun sendMessage() {
        val text = _inputText.value.trim()
        if (text.isEmpty() || _isLoading.value) return

        val userMessage = AssistantMessage(role = AssistantMessage.Role.USER, text = text, persona = _selectedPersona.value)
        _messages.value += userMessage
        _inputText.value = ""
        saveHistory()

        viewModelScope.launch {
            _isLoading.value = true
            try {
                val groupId = userPreferences.selectedGroupId.first()
                val date = Date()
                val dateStr = requestDateFormatter.format(date)

                val scheduleItems = if (groupId != null) {
                    try {
                        scheduleRepository.fetchSchedule(groupId, date, false)
                    } catch (e: Exception) { emptyList() }
                } else emptyList()

                val scheduleText = if (groupId != null) {
                    AssistantScheduleContextBuilder.buildScheduleText(groupId, date, scheduleItems)
                } else "Группа пользователя не выбрана, поэтому точное расписание пар недоступно."

                val history = _messages.value.filter {
                    it.role == AssistantMessage.Role.USER || it.role == AssistantMessage.Role.ASSISTANT
                }.takeLast(10).map {
                    AssistantChatMessagePayload(
                        role = if (it.role == AssistantMessage.Role.USER) "user" else "assistant",
                        content = it.text
                    )
                }

                val promptMessages = AssistantPromptBuilder.buildMessages(
                    persona = _selectedPersona.value.rawValue,
                    history = history,
                    scheduleContext = scheduleText
                )

                val legacyMessage = AssistantPromptBuilder.buildLegacyMessage(promptMessages)

                val request = AssistantChatRequest(
                    message = legacyMessage,
                    persona = _selectedPersona.value.rawValue,
                    messages = promptMessages,
                    context = AssistantContext(groupId, dateStr),
                    conversationId = conversationId,
                    groupId = groupId,
                    targetDate = dateStr,
                    cachedSchedule = if (scheduleItems.isNotEmpty()) {
                        AssistantScheduleContextBuilder.buildCachedSchedule(scheduleItems)
                    } else null
                )

                val response = apiService.assistantChat(request)
                if (response.isSuccessful) {
                    response.body()?.let {
                        _messages.value += AssistantMessage(role = AssistantMessage.Role.ASSISTANT, text = it.reply, persona = _selectedPersona.value)
                        saveHistory()
                    }
                } else {
                    val message = when (response.code()) {
                        429 -> "Слишком много запросов. Попробуй позже (лимит исчерпан)."
                        500 -> "Ошибка на стороне AI-сервиса. Мы уже чиним!"
                        else -> "Ошибка сервера: ${response.code()}"
                    }
                    _messages.value += AssistantMessage(role = AssistantMessage.Role.SYSTEM_LOCAL, text = message)
                }
            } catch (e: java.net.SocketTimeoutException) {
                _messages.value += AssistantMessage(role = AssistantMessage.Role.SYSTEM_LOCAL, text = "Превышено время ожидания. AI сегодня задумчив...")
            } catch (e: Exception) {
                _messages.value += AssistantMessage(role = AssistantMessage.Role.SYSTEM_LOCAL, text = "Ошибка сети: ${e.localizedMessage ?: "неизвестно"}")
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun clearHistory() {
        _messages.value = emptyList()
        viewModelScope.launch {
            userPreferences.clearAssistantHistory()
        }
    }
}
