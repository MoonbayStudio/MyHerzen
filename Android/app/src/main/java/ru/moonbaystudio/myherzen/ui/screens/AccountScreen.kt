package ru.moonbaystudio.myherzen.ui.screens

import android.content.Context
import android.util.Log
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.ui.components.ActionCapsule
import ru.moonbaystudio.myherzen.ui.components.BadgeDetailDialog
import ru.moonbaystudio.myherzen.ui.components.BadgeIcon
import ru.moonbaystudio.myherzen.ui.components.CapsuleHeader
import ru.moonbaystudio.myherzen.ui.components.UserBadgeRow
import ru.moonbaystudio.myherzen.ui.viewmodel.AuthViewModel
import ru.moonbaystudio.myherzen.ui.viewmodel.SettingsViewModel
import ru.moonbaystudio.myherzen.util.performGoogleSignIn

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun AccountScreen(
    onNavigateToLogin: () -> Unit,
    onNavigate: (String) -> Unit,
    viewModel: AuthViewModel = hiltViewModel()
) {
    val currentUser by viewModel.currentUser.collectAsState()
    val isLoggedIn by viewModel.isLoggedIn.collectAsState(initial = true)
    val isLoading by viewModel.isLoading.collectAsState()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    
    val settingsViewModel: SettingsViewModel = hiltViewModel()
    val selectedGroupName by settingsViewModel.selectedGroupName.collectAsState()

    Scaffold(
        topBar = {
            CapsuleHeader(
                title = "Аккаунт",
                actions = {
                    if (isLoggedIn) {
                        ActionCapsule(icon = Icons.Default.Edit, onClick = { onNavigate("profile_editor") })
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(horizontal = 16.dp)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
        ) {
            if (isLoggedIn) {
                if (currentUser == null && isLoading) {
                    Box(modifier = Modifier.fillMaxWidth().height(200.dp), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                } else {
                    Card(
                        modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.AccountCircle,
                                contentDescription = null,
                                modifier = Modifier.size(48.dp),
                                tint = MaterialTheme.colorScheme.primary
                            )
                            Spacer(Modifier.width(16.dp))
                            Column {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(text = currentUser?.name ?: "Пользователь", style = MaterialTheme.typography.titleLarge)
                                    if (currentUser?.badges?.isNotEmpty() == true) {
                                        Spacer(Modifier.width(8.dp))
                                        UserBadgeRow(badges = currentUser!!.badges)
                                    }
                                }
                                Text(text = currentUser?.email ?: "Email не указан", style = MaterialTheme.typography.bodyMedium)
                                
                                Row(modifier = Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
                                    currentUser?.roles?.forEach { role ->
                                        Surface(
                                            color = MaterialTheme.colorScheme.primaryContainer,
                                            shape = RoundedCornerShape(4.dp)
                                        ) {
                                            Text(
                                                text = role.title,
                                                style = MaterialTheme.typography.labelSmall,
                                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                            )
                                        }
                                    }
                                    
                                    if (selectedGroupName != null) {
                                        Surface(
                                            color = MaterialTheme.colorScheme.secondaryContainer,
                                            shape = RoundedCornerShape(4.dp)
                                        ) {
                                            Text(
                                                text = selectedGroupName!!,
                                                style = MaterialTheme.typography.labelSmall,
                                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    if (currentUser?.contactEmail != null && !currentUser!!.contactEmailVerified) {
                        EmailVerificationBanner(
                            email = currentUser!!.contactEmail!!,
                            onResend = { viewModel.resendEmailVerification() }
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                    } else if (currentUser?.needsContactEmail == true) {
                        EmailRequestCard(
                            onSendRequest = { viewModel.requestEmailVerification(it) }
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                    }

                    if (currentUser?.badges?.isNotEmpty() == true) {
                        Text("Значки", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(vertical = 8.dp))
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                        ) {
                            FlowRow(
                                modifier = Modifier.padding(12.dp),
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                                verticalArrangement = Arrangement.spacedBy(12.dp)
                            ) {
                                currentUser!!.badges.forEach { badge ->
                                    var showDetail by remember { mutableStateOf(false) }
                                    BadgeIcon(badge, size = 32) {
                                        showDetail = true
                                    }
                                    if (showDetail) {
                                        BadgeDetailDialog(badge = badge, onDismiss = { showDetail = false })
                                    }
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(16.dp))
                    }
                    
                    AccountOption(icon = Icons.Default.Lock, title = "Безопасность", onClick = { onNavigate("security") })
                    AccountOption(icon = Icons.Default.Person, title = "Моя группа", onClick = { onNavigate("group_members") })

                    if (currentUser?.isAdmin == true || currentUser?.isModerator == true) {
                        AccountOption(icon = Icons.Default.Settings, title = "Админка", onClick = { onNavigate("admin") })
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    Button(
                        onClick = { viewModel.logout() },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer,
                            contentColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Text("Выйти из аккаунта")
                    }
                }
            } else {
                Column(
                    modifier = Modifier.padding(vertical = 32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(
                        Icons.Default.AccountCircle,
                        contentDescription = null,
                        modifier = Modifier.size(80.dp),
                        tint = MaterialTheme.colorScheme.outline
                    )
                    Spacer(Modifier.height(16.dp))
                    Text(
                        text = "Войдите в аккаунт",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Чтобы синхронизировать расписание и настройки между устройствами",
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    
                    Spacer(modifier = Modifier.height(32.dp))

                    Button(
                        onClick = onNavigateToLogin,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("Войти или Создать аккаунт")
                    }
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    OutlinedButton(
                        onClick = { 
                            scope.launch {
                                performGoogleSignIn(context, viewModel)
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(Icons.Default.AccountCircle, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Продолжить с Google")
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(120.dp))
        }
    }
}

@Composable
fun AccountOption(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, onClick: () -> Unit) {
    ListItem(
        headlineContent = { Text(title) },
        leadingContent = { Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary) },
        trailingContent = { Icon(Icons.Default.KeyboardArrowRight, contentDescription = null) },
        modifier = Modifier.clickable(onClick = onClick)
    )
}

@Composable
fun EmailVerificationBanner(email: String, onResend: () -> Unit) {
    Surface(
        color = MaterialTheme.colorScheme.errorContainer,
        shape = MaterialTheme.shapes.medium
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = "Email не подтвержден", style = MaterialTheme.typography.titleSmall)
            Text(text = "Проверьте почту $email и перейдите по ссылке.", style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = onResend) {
                Text("Отправить письмо еще раз")
            }
        }
    }
}

@Composable
fun EmailRequestCard(onSendRequest: (String) -> Unit) {
    var email by remember { mutableStateOf("") }
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = "Укажите контактный Email", style = MaterialTheme.typography.titleSmall)
            Text(text = "Он нужен для входа по паролю и восстановления доступа.", style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("Email") },
                modifier = Modifier.fillMaxWidth()
            )
            Button(
                onClick = { onSendRequest(email) },
                modifier = Modifier.padding(top = 8.dp),
                enabled = email.isNotBlank()
            ) {
                Text("Отправить код")
            }
        }
    }
}
