package ru.moonbaystudio.myherzen.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.data.model.ScheduleItem
import ru.moonbaystudio.myherzen.data.repository.AuthRepository
import ru.moonbaystudio.myherzen.data.repository.ScheduleRepository
import ru.moonbaystudio.myherzen.data.repository.SettingsRepository
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale
import javax.inject.Inject

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
@HiltViewModel
class ScheduleViewModel @Inject constructor(
    private val repository: ScheduleRepository,
    private val authRepository: AuthRepository,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    sealed class RefreshStatus {
        object Success : RefreshStatus()
        data class Error(val message: String) : RefreshStatus()
    }

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _refreshStatus = MutableStateFlow<RefreshStatus?>(null)
    val refreshStatus: StateFlow<RefreshStatus?> = _refreshStatus.asStateFlow()

    private val _showLastDayWarning = MutableStateFlow(false)
    val showLastDayWarning: StateFlow<Boolean> = _showLastDayWarning.asStateFlow()

    private val _isOffline = MutableStateFlow(false)
    val isOffline: StateFlow<Boolean> = _isOffline.asStateFlow()

    private val _groupId = MutableStateFlow<Int?>(null)
    val selectedGroupId: StateFlow<Int?> = _groupId.asStateFlow()
    private val _selectedDate = MutableStateFlow(Date())
    val selectedDate: StateFlow<Date> = _selectedDate.asStateFlow()
    private val _examOnly = MutableStateFlow(false)

    private val _temporaryItems = MutableStateFlow<Map<String, List<ScheduleItem>>>(emptyMap())

    private val _homeworks = MutableStateFlow<Map<String, ru.moonbaystudio.myherzen.data.remote.Homework>>(emptyMap())
    val homeworks: StateFlow<Map<String, ru.moonbaystudio.myherzen.data.remote.Homework>> = _homeworks.asStateFlow()

    val currentUser = authRepository.currentUser

    val scheduleItems: StateFlow<List<ScheduleItem>> = combine(
        _groupId,
        _selectedDate,
        _examOnly,
        _temporaryItems
    ) { id, date, exam, temp ->
        val dateStr = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(date)
        DataState(id, date, dateStr, exam, temp[dateStr])
    }.flatMapLatest { state ->
        if (state.id != null) {
            repository.getScheduleFlow(state.id, state.date, state.examOnly).map { local ->
                if (local.isEmpty() && state.tempItems != null) state.tempItems else local
            }
        } else {
            flowOf(emptyList())
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    data class DataState(
        val id: Int?,
        val date: Date,
        val dateStr: String,
        val examOnly: Boolean,
        val tempItems: List<ScheduleItem>?
    )

    fun loadSchedule(groupId: Int, examOnly: Boolean = false) {
        if (_groupId.value == groupId && _examOnly.value == examOnly) {
            return
        }
        _groupId.value = groupId
        _examOnly.value = examOnly
        checkCacheAndLoad()
    }

    fun setDate(date: Date) {
        val oldDate = _selectedDate.value
        _selectedDate.value = date
        
        // If date changed significantly or we are in cache mode, check cache
        checkCacheAndLoad()
    }

    fun manualRefresh() {
        val groupId = _groupId.value ?: return
        val date = _selectedDate.value
        val examOnly = _examOnly.value
        
        viewModelScope.launch {
            _isLoading.value = true
            try {
                repository.refreshSchedule(groupId, date, examOnly)
                if (!examOnly) {
                    val homeworkList = repository.getHomeworks(groupId, date)
                    _homeworks.value = homeworkList.associateBy { homeworkKey(it.lessonDate, it.lessonTime, it.subject) }
                }
                _refreshStatus.value = RefreshStatus.Success
                _isOffline.value = false
            } catch (e: Exception) {
                val errorMsg = when (e) {
                    is java.net.UnknownHostException -> {
                        _isOffline.value = true
                        "Нет интернета"
                    }
                    is java.net.ConnectException -> {
                        _isOffline.value = true
                        "Сервер недоступен"
                    }
                    else -> e.message ?: "Ошибка обновления"
                }
                _refreshStatus.value = RefreshStatus.Error(errorMsg)
            } finally {
                _isLoading.value = false
                kotlinx.coroutines.delay(1000)
                _refreshStatus.value = null
            }
        }
    }

    private fun checkCacheAndLoad() {
        val groupId = _groupId.value ?: return
        val date = _selectedDate.value
        val examOnly = _examOnly.value

        viewModelScope.launch {
            val cacheEnabled = settingsRepository.offlineScheduleEnabled.first()
            val cacheWeeks = settingsRepository.offlineScheduleWeeks.first()

            if (cacheEnabled) {
                if (examOnly) {
                    val hasSession = repository.hasSession(groupId)
                    if (!hasSession) {
                        try {
                            repository.refreshSchedule(groupId, date, true)
                        } catch (e: Exception) {}
                    }
                } else {
                    val hasData = repository.hasDataForDate(groupId, date)
                    val minDate = repository.getMinCachedDate(groupId)
                    
                    if (!hasData) {
                        if (minDate != null && date.before(minDate)) {
                            // Date is before min cached date (likely cleared)
                            // Fetch without saving to cache
                            try {
                                val remoteItems = repository.fetchSchedule(groupId, date, false)
                                val dateStr = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(date)
                                _temporaryItems.value = _temporaryItems.value + (dateStr to remoteItems)
                                _isOffline.value = false
                            } catch (e: Exception) {
                                _isOffline.value = true
                            }
                        } else {
                            // Fetch range and save to cache
                            try {
                                loadCacheRange(groupId, date, cacheWeeks)
                                _isOffline.value = false
                            } catch (e: Exception) {
                                try { 
                                    repository.refreshSchedule(groupId, date, false)
                                    _isOffline.value = false
                                } catch (e2: Exception) {
                                    _isOffline.value = true
                                }
                            }
                        }
                    }

                    // Check if it's the last day in cache
                    val maxDate = repository.getMaxCachedDate(groupId)
                    if (maxDate != null) {
                        val cal = Calendar.getInstance()
                        cal.time = maxDate
                        val maxDateStr = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(cal.time)
                        val currentDateStr = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(date)
                        
                        if (maxDateStr == currentDateStr) {
                            // Try to extend
                            try {
                                extendCache(groupId, date, cacheWeeks)
                            } catch (e: Exception) {
                                _showLastDayWarning.value = true
                            }
                        }
                    }

                    // Fetch homeworks for this day
                    try {
                        val homeworkList = repository.getHomeworks(groupId, date)
                        _homeworks.value = homeworkList.associateBy { homeworkKey(it.lessonDate, it.lessonTime, it.subject) }
                    } catch (e: Exception) {}
                }
            } else {
                // Not using cache, always refresh current day
                refresh()
            }
        }
    }

    private suspend fun loadCacheRange(groupId: Int, startDate: Date, weeks: Int) {
        val cal = Calendar.getInstance()
        cal.time = startDate
        
        // Start from beginning of previous week
        cal.set(Calendar.DAY_OF_WEEK, cal.firstDayOfWeek)
        cal.add(Calendar.WEEK_OF_YEAR, -1)
        val rangeStart = cal.time
        
        // Go N weeks forward from current date
        cal.time = startDate
        cal.add(Calendar.WEEK_OF_YEAR, weeks)
        val rangeEnd = cal.time
        
        repository.refreshScheduleRange(groupId, rangeStart, rangeEnd, false)
        // Also load session
        repository.refreshSchedule(groupId, startDate, true)
        
        // Cleanup
        repository.cleanOldCache(groupId, startDate)
    }

    private suspend fun extendCache(groupId: Int, fromDate: Date, weeks: Int) {
        val cal = Calendar.getInstance()
        cal.time = fromDate
        cal.add(Calendar.DAY_OF_YEAR, 1)
        val startDate = cal.time
        cal.add(Calendar.WEEK_OF_YEAR, weeks)
        val endDate = cal.time
        
        try {
            repository.refreshScheduleRange(groupId, startDate, endDate, false)
            repository.cleanOldCache(groupId, fromDate)
            _isOffline.value = false
        } catch (e: Exception) {
            _isOffline.value = true
            throw e
        }
    }

    fun dismissWarning() {
        _showLastDayWarning.value = false
    }

    private fun refresh() {
        val groupId = _groupId.value ?: return
        val date = _selectedDate.value
        val examOnly = _examOnly.value
        viewModelScope.launch {
            _isLoading.value = true
            try {
                repository.refreshSchedule(groupId, date, examOnly)
                if (!examOnly) {
                    val homeworkList = repository.getHomeworks(groupId, date)
                    _homeworks.value = homeworkList.associateBy { homeworkKey(it.lessonDate, it.lessonTime, it.subject) }
                } else {
                    _homeworks.value = emptyMap()
                }
            } catch (e: Exception) {
                // Handle error
            } finally {
                _isLoading.value = false
            }
        }
    }

    private fun homeworkKey(date: String, time: String, subject: String): String {
        return "$date|$time|$subject"
    }

    fun getHomeworkForKey(date: String, time: String, subject: String): ru.moonbaystudio.myherzen.data.remote.Homework? {
        return _homeworks.value[homeworkKey(date, time, subject)]
    }

    fun saveHomework(lesson: ScheduleItem, text: String) {
        val groupId = _groupId.value ?: return
        val dateStr = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(_selectedDate.value)
        val existing = _homeworks.value[homeworkKey(dateStr, lesson.time, lesson.title)]

        viewModelScope.launch {
            _isLoading.value = true
            val result = if (existing != null) {
                repository.updateHomework(groupId, existing.id, text)
            } else {
                repository.createHomework(
                    groupId = groupId,
                    lessonDate = dateStr,
                    lessonTime = lesson.time,
                    subject = lesson.title,
                    teacher = lesson.teacher.ifBlank { null },
                    room = lesson.room.ifBlank { null },
                    text = text
                )
            }
            if (result.isSuccess) {
                refresh()
            }
            _isLoading.value = false
        }
    }

    fun deleteHomework(homeworkId: String) {
        val groupId = _groupId.value ?: return
        viewModelScope.launch {
            _isLoading.value = true
            if (repository.deleteHomework(groupId, homeworkId).isSuccess) {
                refresh()
            }
            _isLoading.value = false
        }
    }
}
