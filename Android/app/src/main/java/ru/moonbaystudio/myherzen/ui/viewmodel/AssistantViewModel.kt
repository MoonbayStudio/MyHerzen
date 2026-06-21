package ru.moonbaystudio.myherzen.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject

@HiltViewModel
class AssistantViewModel @Inject constructor(
    private val apiService: MyHerzenApiService,
    private val scheduleRepository: ScheduleRepository,
    private val userPreferences: UserPreferences
) : ViewModel() {

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
    private val isoFormatter = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    fun setInputText(text: String) {
        _inputText.value = text
    }

    fun setPersona(persona: AssistantPersona) {
        _selectedPersona.value = persona
    }

    fun sendMessage() {
        val text = _inputText.value.trim()
        if (text.isEmpty()) return

        val userMessage = AssistantMessage(role = AssistantMessage.Role.USER, text = text, persona = _selectedPersona.value)
        _messages.value += userMessage
        _inputText.value = ""

        viewModelScope.launch {
            _isLoading.value = true
            try {
                val groupId = userPreferences.selectedGroupId.first()
                val date = Date()
                val dateStr = requestDateFormatter.format(date)
                
                val request = AssistantChatRequest(
                    message = text,
                    persona = _selectedPersona.value.rawValue,
                    context = AssistantContext(groupId, dateStr),
                    conversationId = conversationId,
                    groupId = groupId,
                    targetDate = dateStr,
                    cachedSchedule = null // Simplified for now
                )

                val response = apiService.assistantChat(request)
                if (response.isSuccessful) {
                    response.body()?.let {
                        _messages.value += AssistantMessage(role = AssistantMessage.Role.ASSISTANT, text = it.reply, persona = _selectedPersona.value)
                    }
                } else {
                    _messages.value += AssistantMessage(role = AssistantMessage.Role.SYSTEM_LOCAL, text = "Ошибка: ${response.code()}")
                }
            } catch (e: Exception) {
                _messages.value += AssistantMessage(role = AssistantMessage.Role.SYSTEM_LOCAL, text = "Ошибка соединения")
            } finally {
                _isLoading.value = false
            }
        }
    }
}
