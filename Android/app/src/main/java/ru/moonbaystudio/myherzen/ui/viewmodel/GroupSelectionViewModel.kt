package ru.moonbaystudio.myherzen.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.data.model.Institute
import ru.moonbaystudio.myherzen.data.repository.ScheduleRepository
import ru.moonbaystudio.myherzen.data.repository.SettingsRepository
import javax.inject.Inject

@HiltViewModel
class GroupSelectionViewModel @Inject constructor(
    private val scheduleRepository: ScheduleRepository,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    private val _institutes = MutableStateFlow<List<Institute>>(emptyList())
    val institutes: StateFlow<List<Institute>> = _institutes.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    init {
        loadInstitutes()
    }

    private fun loadInstitutes() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                _institutes.value = scheduleRepository.getInstitutesWithGroups()
            } catch (e: Exception) {
                // Handle error
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun selectGroup(groupId: Int, groupName: String) {
        viewModelScope.launch {
            settingsRepository.saveSelectedGroup(groupId, groupName)
        }
    }
}
