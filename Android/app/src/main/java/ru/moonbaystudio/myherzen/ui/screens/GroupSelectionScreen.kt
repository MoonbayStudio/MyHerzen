package ru.moonbaystudio.myherzen.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import ru.moonbaystudio.myherzen.data.model.Institute
import ru.moonbaystudio.myherzen.data.model.MyGroup
import ru.moonbaystudio.myherzen.ui.components.ActionCapsule
import ru.moonbaystudio.myherzen.ui.components.CapsuleHeader
import ru.moonbaystudio.myherzen.ui.viewmodel.GroupSelectionViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GroupSelectionScreen(
    onGroupSelected: () -> Unit,
    onBack: (() -> Unit)? = null,
    viewModel: GroupSelectionViewModel = hiltViewModel()
) {
    val institutes by viewModel.institutes.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()

    Scaffold(
        topBar = {
            CapsuleHeader(
                title = "Выбор группы",
                navigationIcon = if (onBack != null) {
                    { ActionCapsule(icon = Icons.Default.ArrowBack, onClick = onBack) }
                } else null
            )
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding).fillMaxSize()) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(institutes) { institute ->
                        InstituteItem(institute) { group ->
                            viewModel.selectGroup(group.id.toInt(), group.name)
                            onGroupSelected()
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun InstituteItem(institute: Institute, onGroupClick: (MyGroup) -> Unit) {
    var expanded by remember { mutableStateOf(false) }

    Column {
        ListItem(
            headlineContent = { Text(institute.name) },
            trailingContent = {
                Icon(
                    if (expanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                    contentDescription = null
                )
            },
            modifier = Modifier.clickable { expanded = !expanded }
        )
        if (expanded) {
            institute.groups.forEach { group ->
                ListItem(
                    headlineContent = { Text(group.name) },
                    modifier = Modifier
                        .padding(start = 16.dp)
                        .clickable { onGroupClick(group) }
                )
            }
        }
    }
}
