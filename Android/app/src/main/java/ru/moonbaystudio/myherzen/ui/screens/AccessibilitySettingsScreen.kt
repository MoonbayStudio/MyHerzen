package ru.moonbaystudio.myherzen.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import ru.moonbaystudio.myherzen.ui.components.ActionCapsule
import ru.moonbaystudio.myherzen.ui.components.CapsuleHeader

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AccessibilitySettingsScreen(onBack: () -> Unit) {
    Scaffold(
        topBar = {
            CapsuleHeader(
                title = "Спец. возможности",
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
        LazyColumn(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            item {
                ListItem(
                    headlineContent = { Text("Увеличенный шрифт") },
                    supportingContent = { Text("Сделать текст расписания крупнее") },
                    trailingContent = { Switch(checked = false, onCheckedChange = {}) }
                )
                ListItem(
                    headlineContent = { Text("Высокий контраст") },
                    supportingContent = { Text("Улучшить видимость элементов интерфейса") },
                    trailingContent = { Switch(checked = false, onCheckedChange = {}) }
                )
            }
        }
    }
}
