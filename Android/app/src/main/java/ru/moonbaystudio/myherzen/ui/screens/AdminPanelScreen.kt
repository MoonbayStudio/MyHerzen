package ru.moonbaystudio.myherzen.ui.screens

import androidx.compose.animation.*
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.data.remote.dto.*
import ru.moonbaystudio.myherzen.data.repository.AuthRepository
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

    private val _badges = MutableStateFlow<List<BadgeDto>>(emptyList())
    val badges: StateFlow<List<BadgeDto>> = _badges.asStateFlow()

    private val _settings = MutableStateFlow<List<AdminRuntimeSetting>>(emptyList())
    val settings: StateFlow<List<AdminRuntimeSetting>> = _settings.asStateFlow()

    private val _notices = MutableStateFlow<List<SystemNotice>>(emptyList())
    val notices: StateFlow<List<SystemNotice>> = _notices.asStateFlow()

    private val _userSessions = MutableStateFlow<List<AccountSession>>(emptyList())
    val userSessions: StateFlow<List<AccountSession>> = _userSessions.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    fun loadAllData() {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null
            try {
                _users.value = authRepository.getAdminUsers()
                _requests.value = authRepository.getAdminRoleRequests("pending")
                _badges.value = authRepository.getAdminBadges()
                _settings.value = authRepository.getAdminSettings()
                _notices.value = authRepository.getAdminSystemNotices()
            } catch (e: Exception) {
                _errorMessage.value = "Ошибка загрузки: ${e.message}"
            }
            _isLoading.value = false
        }
    }

    fun approveRequest(requestId: Int) {
        viewModelScope.launch {
            authRepository.approveRoleRequest(requestId).onSuccess { loadAllData() }
        }
    }

    fun rejectRequest(requestId: Int) {
        viewModelScope.launch {
            authRepository.rejectRoleRequest(requestId).onSuccess { loadAllData() }
        }
    }

    fun setRole(userId: String, role: String, enabled: Boolean) {
        viewModelScope.launch {
            val result = if (enabled) authRepository.grantRole(userId, role) else authRepository.revokeRole(userId, role)
            result.onSuccess { loadAllData() }
        }
    }

    fun setBadge(userId: String, badgeCode: String, enabled: Boolean, note: String?) {
        viewModelScope.launch {
            val result = if (enabled) authRepository.grantBadge(userId, badgeCode, note) else authRepository.revokeBadge(userId, badgeCode)
            result.onSuccess { loadAllData() }
        }
    }

    fun updateSetting(key: String, value: Any) {
        viewModelScope.launch {
            authRepository.updateAdminSetting(key, value).onSuccess { loadAllData() }
        }
    }

    fun deleteNotice(id: Int) {
        viewModelScope.launch {
            authRepository.deleteAdminSystemNotice(id).onSuccess { loadAllData() }
        }
    }

    fun toggleNotice(id: Int, active: Boolean) {
        viewModelScope.launch {
            val result = if (active) authRepository.activateSystemNotice(id) else authRepository.deactivateSystemNotice(id)
            result.onSuccess { loadAllData() }
        }
    }

    fun loadUserSessions(userId: String) {
        viewModelScope.launch {
            _userSessions.value = authRepository.getAdminUserSessions(userId)
        }
    }

    fun revokeUserSession(userId: String, sessionId: String) {
        viewModelScope.launch {
            authRepository.revokeAdminSession(sessionId).onSuccess { loadUserSessions(userId) }
        }
    }

    fun createNotice(request: SystemNoticeMutationRequest) {
        viewModelScope.launch {
            authRepository.createAdminSystemNotice(request).onSuccess { loadAllData() }
        }
    }
}

enum class AdminTab { USERS, REQUESTS, SETTINGS, NOTICES }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminPanelScreen(
    onBack: () -> Unit,
    viewModel: AdminViewModel = hiltViewModel()
) {
    val users by viewModel.users.collectAsState()
    val requests by viewModel.requests.collectAsState()
    val settings by viewModel.settings.collectAsState()
    val notices by viewModel.notices.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.errorMessage.collectAsState()

    var selectedTab by remember { mutableStateOf(AdminTab.USERS) }
    var searchText by remember { mutableStateOf("") }
    var userToEdit by remember { mutableStateOf<AdminUserDto?>(null) }
    var showCreateNoticeDialog by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        viewModel.loadAllData()
    }

    if (showCreateNoticeDialog) {
        CreateNoticeDialog(
            onDismiss = { showCreateNoticeDialog = false },
            onConfirm = { request ->
                viewModel.createNotice(request)
                showCreateNoticeDialog = false
            }
        )
    }

    if (userToEdit != null) {
        UserEditorDialog(
            user = userToEdit!!,
            availableBadges = viewModel.badges.collectAsState().value,
            sessions = viewModel.userSessions.collectAsState().value,
            onDismiss = { userToEdit = null },
            onRoleToggle = { role, enabled -> viewModel.setRole(userToEdit!!.id, role, enabled) },
            onBadgeToggle = { code, enabled, note -> viewModel.setBadge(userToEdit!!.id, code, enabled, note) },
            onLoadSessions = { viewModel.loadUserSessions(userToEdit!!.id) },
            onRevokeSession = { viewModel.revokeUserSession(userToEdit!!.id, it) }
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
                },
                actions = {
                    IconButton(onClick = { viewModel.loadAllData() }, enabled = !isLoading) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            ScrollableTabRow(
                selectedTabIndex = selectedTab.ordinal,
                edgePadding = 16.dp,
                containerColor = Color.Transparent
            ) {
                AdminTab.values().forEach { tab ->
                    val title = when(tab) {
                        AdminTab.USERS -> "Юзеры"
                        AdminTab.REQUESTS -> "Заявки (${requests.size})"
                        AdminTab.SETTINGS -> "Дебаг"
                        AdminTab.NOTICES -> "Уведомления"
                    }
                    Tab(
                        selected = selectedTab == tab,
                        onClick = { selectedTab = tab },
                        text = { Text(title) }
                    )
                }
            }

            if (selectedTab == AdminTab.NOTICES) {
                Button(
                    onClick = { showCreateNoticeDialog = true },
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Создать уведомление")
                }
            }

            if (selectedTab == AdminTab.USERS) {
                OutlinedTextField(
                    value = searchText,
                    onValueChange = { searchText = it },
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    placeholder = { Text("Поиск по имени или email") },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                    singleLine = true,
                    shape = RoundedCornerShape(12.dp)
                )
            }

            error?.let {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(16.dp))
            }

            Box(modifier = Modifier.fillMaxSize()) {
                if (isLoading && users.isEmpty()) {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                } else {
                    val filteredUsers = if (searchText.isBlank()) users else {
                        users.filter { it.name?.contains(searchText, true) == true || it.email?.contains(searchText, true) == true }
                    }

                    LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 100.dp)) {
                        when (selectedTab) {
                            AdminTab.USERS -> {
                                items(filteredUsers) { user ->
                                    UserListItem(user = user, onClick = { userToEdit = user })
                                }
                            }
                            AdminTab.REQUESTS -> {
                                items(requests) { request ->
                                    RequestListItem(request = request, viewModel = viewModel)
                                }
                                if (requests.isEmpty()) {
                                    item { EmptyState("Нет активных заявок") }
                                }
                            }
                            AdminTab.SETTINGS -> {
                                items(settings) { setting ->
                                    SettingItem(setting = setting, onUpdate = { viewModel.updateSetting(setting.key, it) })
                                }
                            }
                            AdminTab.NOTICES -> {
                                items(notices) { notice ->
                                    NoticeItem(notice = notice, viewModel = viewModel)
                                }
                                if (notices.isEmpty()) {
                                    item { EmptyState("Уведомлений нет") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun UserListItem(user: AdminUserDto, onClick: () -> Unit) {
    ListItem(
        headlineContent = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(user.name ?: "Без имени", fontWeight = FontWeight.Bold)
                if (user.badges.isNotEmpty()) {
                    Spacer(Modifier.width(8.dp))
                    UserBadgeRow(badges = user.badges)
                }
            }
        },
        supportingContent = { Text("${user.email ?: "no email"} • ${user.tier.uppercase()}") },
        leadingContent = {
            val icon = if (user.roles.any { it.type == "admin" }) Icons.Default.Star else Icons.Default.Person
            Icon(icon, contentDescription = null, tint = if (icon == Icons.Default.Star) Color(0xFFFFD700) else MaterialTheme.colorScheme.primary)
        },
        trailingContent = { Icon(Icons.Default.KeyboardArrowRight, contentDescription = null) },
        modifier = Modifier.clickable(onClick = onClick)
    )
}

@Composable
fun RequestListItem(request: AdminRoleRequestDto, viewModel: AdminViewModel) {
    ListItem(
        headlineContent = { Text(request.userEmail ?: "ID: ${request.userId}") },
        supportingContent = { Text("Хочет роль: ${request.roleType}\n${request.createdAt}") },
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

@Composable
fun SettingItem(setting: AdminRuntimeSetting, onUpdate: (Any) -> Unit) {
    ListItem(
        headlineContent = { Text(setting.key, fontWeight = FontWeight.Medium) },
        supportingContent = { Text(setting.value.toString()) },
        trailingContent = {
            when (setting.value) {
                is Boolean -> {
                    Switch(checked = setting.value, onCheckedChange = { onUpdate(it) })
                }
                else -> {
                    IconButton(onClick = { /* TODO: Dialog for text/int update */ }) {
                        Icon(Icons.Default.Edit, contentDescription = null)
                    }
                }
            }
        }
    )
}

@Composable
fun NoticeItem(notice: SystemNotice, viewModel: AdminViewModel) {
    ListItem(
        headlineContent = { Text(notice.title) },
        supportingContent = { Text("${notice.type} • ${notice.showAs}\n${notice.message}") },
        trailingContent = {
            Row {
                Switch(checked = notice.isActive == true, onCheckedChange = { viewModel.toggleNotice(notice.id, it) })
                IconButton(onClick = { viewModel.deleteNotice(notice.id) }) {
                    Icon(Icons.Default.Delete, contentDescription = null, tint = Color.Red)
                }
            }
        }
    )
}

@Composable
fun UserEditorDialog(
    user: AdminUserDto,
    availableBadges: List<BadgeDto>,
    sessions: List<AccountSession>,
    onDismiss: () -> Unit,
    onRoleToggle: (String, Boolean) -> Unit,
    onBadgeToggle: (String, Boolean, String?) -> Unit,
    onLoadSessions: () -> Unit,
    onRevokeSession: (String) -> Unit
) {
    val roles = listOf("admin", "moderator", "tester", "premium", "plus", "free", "group_leader")

    LaunchedEffect(user.id) {
        onLoadSessions()
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Редактировать: ${user.name ?: user.email ?: user.id}") },
        text = {
            LazyColumn(modifier = Modifier.heightIn(max = 500.dp)) {
                item { Text("Роли", style = MaterialTheme.typography.titleSmall, modifier = Modifier.padding(vertical = 8.dp)) }
                items(roles) { role ->
                    val hasRole = user.roles.any { it.type == role }
                    Row(
                        modifier = Modifier.fillMaxWidth().clickable { onRoleToggle(role, !hasRole) }.padding(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Checkbox(checked = hasRole, onCheckedChange = { onRoleToggle(role, it) })
                        Text(role.uppercase(), modifier = Modifier.padding(start = 8.dp))
                    }
                }

                item { Text("Значки", style = MaterialTheme.typography.titleSmall, modifier = Modifier.padding(vertical = 8.dp)) }
                items(availableBadges) { badge ->
                    val hasBadge = user.badges.any { it.code == badge.code }
                    Row(
                        modifier = Modifier.fillMaxWidth().clickable { onBadgeToggle(badge.code, !hasBadge, null) }.padding(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Checkbox(checked = hasBadge, onCheckedChange = { onBadgeToggle(badge.code, it, null) })
                        Text(badge.title, modifier = Modifier.padding(start = 8.dp))
                    }
                }

                item {
                    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(vertical = 8.dp)) {
                        Text("Сеансы", style = MaterialTheme.typography.titleSmall)
                        Spacer(Modifier.weight(1f))
                        TextButton(onClick = onLoadSessions) { Text("Обновить") }
                    }
                }
                if (sessions.isEmpty()) {
                    item { Text("Нет активных сеансов", style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(8.dp)) }
                } else {
                    items(sessions) { session ->
                        ListItem(
                            headlineContent = { Text(session.deviceName ?: "Устройство", style = MaterialTheme.typography.bodySmall) },
                            supportingContent = { Text("${session.platform} • ${session.safeIpText}", style = MaterialTheme.typography.labelSmall) },
                            trailingContent = {
                                IconButton(onClick = { onRevokeSession(session.id) }) {
                                    Icon(Icons.Default.Close, contentDescription = "Revoke", tint = Color.Red, modifier = Modifier.size(16.dp))
                                }
                            }
                        )
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Готово") } }
    )
}

@Composable
fun CreateNoticeDialog(
    onDismiss: () -> Unit,
    onConfirm: (SystemNoticeMutationRequest) -> Unit
) {
    var title by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }
    var type by remember { mutableStateOf("info") }
    var showAs by remember { mutableStateOf("banner") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Новое уведомление") },
        text = {
            Column {
                OutlinedTextField(value = title, onValueChange = { title = it }, label = { Text("Заголовок") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = message, onValueChange = { message = it }, label = { Text("Текст") }, modifier = Modifier.fillMaxWidth())

                Text("Тип", modifier = Modifier.padding(top = 8.dp))
                Row {
                    listOf("info", "warning", "maintenance", "critical").forEach {
                        FilterChip(
                            selected = type == it,
                            onClick = { type = it },
                            label = { Text(it) },
                            modifier = Modifier.padding(end = 4.dp)
                        )
                    }
                }

                Text("Показ", modifier = Modifier.padding(top = 8.dp))
                Row {
                    listOf("banner", "modal").forEach {
                        FilterChip(
                            selected = showAs == it,
                            onClick = { showAs = it },
                            label = { Text(it) },
                            modifier = Modifier.padding(end = 4.dp)
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(onClick = {
                onConfirm(SystemNoticeMutationRequest(title, message, type, showAs, true, null, null))
            }) { Text("Создать") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Отмена") } }
    )
}

@Composable
fun EmptyState(text: String) {
    Box(modifier = Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
        Text(text, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
