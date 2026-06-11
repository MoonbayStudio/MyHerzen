package ru.moonbaystudio.myherzen.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.data.remote.AdminRoleRequestDto
import ru.moonbaystudio.myherzen.data.remote.AdminUserDto
import ru.moonbaystudio.myherzen.data.repository.AuthRepository
import ru.moonbaystudio.myherzen.ui.components.ActionCapsule
import ru.moonbaystudio.myherzen.ui.components.CapsuleHeader
import ru.moonbaystudio.myherzen.ui.components.UserBadgeRow
import javax.inject.Inject

@HiltViewModel
class AdminViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {
    private val _users = MutableStateFlow<List<AdminUserDto>>(emptyList())
    val users: StateFlow<List<AdminUserDto>> = _users.asStateFlow()

    private val _requests = MutableStateFlow<List<AdminRoleRequestDto>>(emptyList())
    val requests: StateFlow<List<AdminRoleRequestDto>> = _requests.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    fun loadAdminData() {
        viewModelScope.launch {
            _isLoading.value = true
            _users.value = authRepository.getAdminUsers()
            _requests.value = authRepository.getAdminRoleRequests("pending")
            _isLoading.value = false
        }
    }

    fun approveRequest(requestId: Int) {
        viewModelScope.launch {
            authRepository.approveRoleRequest(requestId)
            loadAdminData()
        }
    }

    fun rejectRequest(requestId: Int) {
        viewModelScope.launch {
            authRepository.rejectRoleRequest(requestId)
            loadAdminData()
        }
    }

    fun grantRole(userId: Int, role: String) {
        viewModelScope.launch {
            authRepository.grantRole(userId, role)
            loadAdminData()
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminPanelScreen(
    onBack: () -> Unit,
    viewModel: AdminViewModel = hiltViewModel()
) {
    val users by viewModel.users.collectAsState()
    val requests by viewModel.requests.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()

    var selectedTab by remember { mutableStateOf(0) }
    var userToGrantRole by remember { mutableStateOf<AdminUserDto?>(null) }

    LaunchedEffect(Unit) {
        viewModel.loadAdminData()
    }

    if (userToGrantRole != null) {
        GrantRoleDialog(
            user = userToGrantRole!!,
            onDismiss = { userToGrantRole = null },
            onConfirm = { role ->
                viewModel.grantRole(userToGrantRole!!.id.toInt(), role)
                userToGrantRole = null
            }
        )
    }

    Scaffold(
        topBar = {
            CapsuleHeader(
                title = "Админка",
                navigationIcon = { 
                    Surface(
                        onClick = onBack,
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        modifier = Modifier.size(40.dp)
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                        }
                    }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            TabRow(selectedTabIndex = selectedTab) {
                Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("Пользователи") })
                Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Заявки (${requests.size})") })
            }

            if (isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    if (selectedTab == 0) {
                        items(users) { user ->
                            ListItem(
                                headlineContent = {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text(user.name ?: "Без имени")
                                        if (user.badges.isNotEmpty()) {
                                            Spacer(Modifier.width(8.dp))
                                            UserBadgeRow(badges = user.badges)
                                        }
                                    }
                                },
                                supportingContent = { Text(user.email ?: "") },
                                leadingContent = { Icon(Icons.Default.Person, contentDescription = null) },
                                trailingContent = { 
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Text(user.tier.uppercase(), style = MaterialTheme.typography.labelSmall)
                                        IconButton(onClick = { userToGrantRole = user }) {
                                            Icon(Icons.Default.Edit, contentDescription = "Grant Role")
                                        }
                                    }
                                }
                            )
                        }
                    } else {
                        if (requests.isEmpty()) {
                            item {
                                Box(modifier = Modifier.fillParentMaxSize(), contentAlignment = Alignment.Center) {
                                    Text("Нет активных заявок", color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        } else {
                            items(requests) { request ->
                                ListItem(
                                    headlineContent = { Text(request.userEmail ?: "ID: ${request.userId}") },
                                    supportingContent = { Text("Роль: ${request.roleType} • ${request.createdAt}") },
                                    trailingContent = {
                                        Row {
                                            IconButton(onClick = { viewModel.approveRequest(request.id) }) { 
                                                Icon(Icons.Default.Check, contentDescription = "Approve", tint = Color.Green) 
                                            }
                                            IconButton(onClick = { viewModel.rejectRequest(request.id) }) { 
                                                Icon(Icons.Default.Close, contentDescription = "Reject", tint = Color.Red) 
                                            }
                                        }
                                    }
                                )
                            }
                        }
                    }
                    
                    item { Spacer(modifier = Modifier.height(100.dp)) }
                }
            }
        }
    }
}

@Composable
fun GrantRoleDialog(user: AdminUserDto, onDismiss: () -> Unit, onConfirm: (String) -> Unit) {
    val roles = listOf("admin", "moderator", "tester", "premium", "plus", "free")
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Выдать роль для ${user.name}") },
        text = {
            Column {
                roles.forEach { role ->
                    ListItem(
                        headlineContent = { Text(role.uppercase()) },
                        modifier = Modifier.clickable { onConfirm(role) }
                    )
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Отмена") } }
    )
}
