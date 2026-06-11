package ru.moonbaystudio.myherzen.ui.screens

import android.content.Context
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.ui.components.ActionCapsule
import ru.moonbaystudio.myherzen.ui.components.CapsuleHeader
import ru.moonbaystudio.myherzen.ui.viewmodel.AuthViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SecurityScreen(
    onNavigate: (String) -> Unit,
    onBack: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel()
) {
    val currentUser by viewModel.currentUser.collectAsState()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    Scaffold(
        topBar = {
            CapsuleHeader(
                title = "Безопасность",
                navigationIcon = {
                    ActionCapsule(icon = Icons.Default.ArrowBack, onClick = onBack)
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            item {
                Text("Учетная запись", style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(bottom = 8.dp))
                SecurityItem(icon = Icons.Default.Email, title = "Электронная почта", onClick = { onNavigate("email_change") })
                SecurityItem(icon = Icons.Default.Lock, title = "Пароль", onClick = { onNavigate("password_setup") })
            }

            item {
                Spacer(modifier = Modifier.height(16.dp))
                Text("Привязки", style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(bottom = 8.dp))
                
                // Apple Indicator
                val isAppleLinked = currentUser?.linkedProviders?.contains("apple") == true
                ListItem(
                    headlineContent = { Text("Apple ID") },
                    leadingContent = { Icon(Icons.Default.AccountCircle, contentDescription = null, tint = if (isAppleLinked) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant) },
                    supportingContent = { Text(if (isAppleLinked) "Привязан" else "Не привязан") }
                )

                // Google Link
                val isGoogleLinked = currentUser?.linkedProviders?.contains("google") == true
                ListItem(
                    headlineContent = { Text("Google") },
                    leadingContent = { Icon(Icons.Default.AccountCircle, contentDescription = null, tint = if (isGoogleLinked) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant) },
                    supportingContent = { Text(if (isGoogleLinked) "Привязан" else "Не привязан") },
                    trailingContent = {
                        if (!isGoogleLinked) {
                            TextButton(onClick = {
                                scope.launch {
                                    handleGoogleLink(context, viewModel)
                                }
                            }) { Text("Привязать") }
                        }
                    }
                )
            }

            item {
                Spacer(modifier = Modifier.height(16.dp))
                Text("Сеансы", style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(bottom = 8.dp))
                SecurityItem(icon = Icons.Default.Build, title = "Активные устройства", onClick = { onNavigate("sessions") })
            }
        }
    }
}

private suspend fun handleGoogleLink(context: Context, viewModel: AuthViewModel) {
    val credentialManager = CredentialManager.create(context)
    val googleIdOption = GetGoogleIdOption.Builder()
        .setFilterByAuthorizedAccounts(false)
        .setServerClientId("295307918338-v06h8kfncsi65plqte80laqe7rqj4vt4.apps.googleusercontent.com")
        .setAutoSelectEnabled(false)
        .build()

    val request = GetCredentialRequest.Builder()
        .addCredentialOption(googleIdOption)
        .build()

    try {
        val result = credentialManager.getCredential(context, request)
        val credential = result.credential
        if (credential is GoogleIdTokenCredential) {
            viewModel.linkGoogle(credential.idToken)
        }
    } catch (e: GetCredentialException) {
        // Log error
    }
}

@Composable
fun SecurityItem(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, onClick: () -> Unit) {
    ListItem(
        headlineContent = { Text(title) },
        leadingContent = { Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary) },
        trailingContent = { Icon(Icons.Default.KeyboardArrowRight, contentDescription = null) },
        modifier = Modifier.clickable(onClick = onClick)
    )
}
