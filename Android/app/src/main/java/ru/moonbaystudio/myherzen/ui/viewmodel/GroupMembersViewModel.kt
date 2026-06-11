package ru.moonbaystudio.myherzen.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.data.remote.GroupUserDto
import ru.moonbaystudio.myherzen.data.repository.AuthRepository
import javax.inject.Inject

@HiltViewModel
class GroupMembersViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {
    private val _users = MutableStateFlow<List<GroupUserDto>>(emptyList())
    val users: StateFlow<List<GroupUserDto>> = _users.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    fun loadUsers(groupId: Int) {
        viewModelScope.launch {
            _isLoading.value = true
            _users.value = authRepository.getGroupUsers(groupId)
            _isLoading.value = false
        }
    }
}
