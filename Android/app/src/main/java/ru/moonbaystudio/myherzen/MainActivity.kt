package ru.moonbaystudio.myherzen

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.animation.*
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import ru.moonbaystudio.myherzen.data.local.preferences.UserPreferences
import ru.moonbaystudio.myherzen.ui.viewmodel.AuthViewModel
import ru.moonbaystudio.myherzen.ui.components.ThemedBackground
import ru.moonbaystudio.myherzen.ui.screens.AboutScreen
import ru.moonbaystudio.myherzen.ui.screens.AccessibilitySettingsScreen
import ru.moonbaystudio.myherzen.ui.screens.AccountScreen
import ru.moonbaystudio.myherzen.ui.screens.AccountSessionsScreen
import ru.moonbaystudio.myherzen.ui.screens.AdminPanelScreen
import ru.moonbaystudio.myherzen.ui.viewmodel.AdminViewModel
import ru.moonbaystudio.myherzen.ui.screens.AssistantScreen
import ru.moonbaystudio.myherzen.ui.screens.EmailChangeScreen
import ru.moonbaystudio.myherzen.ui.screens.GroupMembersScreen
import ru.moonbaystudio.myherzen.ui.screens.GroupSelectionScreen
import ru.moonbaystudio.myherzen.ui.screens.LoginScreen
import ru.moonbaystudio.myherzen.ui.screens.MenuScreen
import ru.moonbaystudio.myherzen.ui.screens.OnboardingScreen
import ru.moonbaystudio.myherzen.ui.screens.PasswordSetupScreen
import ru.moonbaystudio.myherzen.ui.screens.ProfileEditorScreen
import ru.moonbaystudio.myherzen.ui.screens.ScheduleScreen
import ru.moonbaystudio.myherzen.ui.screens.SessionScreen
import ru.moonbaystudio.myherzen.ui.screens.SecurityScreen
import ru.moonbaystudio.myherzen.ui.screens.SettingsScreen
import ru.moonbaystudio.myherzen.ui.screens.ThemesSettingsScreen
import ru.moonbaystudio.myherzen.ui.theme.AppThemeCatalog
import ru.moonbaystudio.myherzen.ui.theme.MyHerzenTheme
import ru.moonbaystudio.myherzen.service.ScheduleLiveService
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var userPreferences: UserPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Обработка Deep Link при запуске
        intent?.data?.let { handleAuthDeepLink(it) }

        setContent {
            val selectedThemeId by userPreferences.selectedThemeId.collectAsState(initial = "classic")
            val liveActivityEnabled by userPreferences.liveActivityEnabled.collectAsState(initial = true)
            val highContrast by userPreferences.highContrast.collectAsState(initial = false)
            val largerText by userPreferences.largerText.collectAsState(initial = false)
            val selectedGroupId by userPreferences.selectedGroupId.collectAsState(initial = null)
            val onboardingCompleted by userPreferences.onboardingCompleted.collectAsState(initial = null)
            val appTheme = AppThemeCatalog.theme(selectedThemeId)

            LaunchedEffect(liveActivityEnabled, selectedGroupId) {
                val intent = android.content.Intent(this@MainActivity, ScheduleLiveService::class.java)
                if (liveActivityEnabled && selectedGroupId != null) {
                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                        startForegroundService(intent)
                    } else {
                        startService(intent)
                    }
                } else {
                    stopService(intent)
                }
            }

            MyHerzenTheme(
                appTheme = appTheme,
                highContrast = highContrast,
                largerText = largerText
            ) {
                ThemedBackground(theme = appTheme) {
                    AppNavigation(selectedGroupId, onboardingCompleted)
                }
            }
        }
    }

    override fun onNewIntent(intent: android.content.Intent?) {
        super.onNewIntent(intent)
        intent?.data?.let { handleAuthDeepLink(it) }
    }

    private fun handleAuthDeepLink(uri: android.net.Uri) {
        if (uri.scheme == "myherzen" && uri.host == "auth") {
            val token = uri.getQueryParameter("token")
            if (token != null) {
                CoroutineScope(Dispatchers.Main).launch {
                    userPreferences.saveAuthToken(token)
                }
            }
        }
    }

}

sealed class Screen(val route: String, val label: String, val icon: ImageVector) {
    object Schedule : Screen("schedule", "Пары", Icons.Default.Home)
    object Pelikasha : Screen("pelikasha", "Пеликаша", Icons.Default.Face)
    object Session : Screen("session", "Сессия", Icons.Default.DateRange)
    object Account : Screen("account", "Аккаунт", Icons.Default.AccountCircle)
    object Menu : Screen("menu", "Меню", Icons.Default.Menu)
}

@Composable
fun AppNavigation(selectedGroupId: Int?, onboardingCompleted: Boolean?) {
    if (onboardingCompleted == null) return // Wait for preferences to load

    val navController = rememberNavController()
    val startDestination = if (onboardingCompleted == false) "onboarding"
                          else if (selectedGroupId != null) Screen.Schedule.route
                          else "group_selection"

    val items = listOf(
        Screen.Schedule,
        Screen.Pelikasha,
        Screen.Session,
        Screen.Account,
        Screen.Menu
    )

    Box(modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        NavHost(
            navController = navController,
            startDestination = startDestination,
            modifier = Modifier.fillMaxSize(),
            enterTransition = { fadeIn(animationSpec = tween(300)) },
            exitTransition = { fadeOut(animationSpec = tween(300)) },
            popEnterTransition = { fadeIn(animationSpec = tween(300)) },
            popExitTransition = { fadeOut(animationSpec = tween(300)) }
        ) {
            composable("onboarding") {
                OnboardingScreen(
                    onFinish = {
                        navController.navigate(if (selectedGroupId != null) Screen.Schedule.route else "group_selection") {
                            popUpTo("onboarding") { inclusive = true }
                        }
                    }
                )
            }
            composable("group_selection") {
                GroupSelectionScreen(
                    onGroupSelected = {
                        navController.navigate(Screen.Schedule.route) {
                            popUpTo("group_selection") { inclusive = true }
                        }
                    },
                    onBack = if (selectedGroupId != null) {
                        { navController.popBackStack() }
                    } else null
                )
            }
            composable(Screen.Schedule.route) {
                if (selectedGroupId != null) {
                    ScheduleScreen(
                        groupId = selectedGroupId
                    )
                }
            }
            composable(Screen.Pelikasha.route) {
                AssistantScreen()
            }
            composable(Screen.Session.route) {
                if (selectedGroupId != null) {
                    SessionScreen(
                        groupId = selectedGroupId
                    )
                }
            }
            composable(Screen.Account.route) {
                AccountScreen(
                    onNavigateToLogin = { navController.navigate("login") },
                    onNavigate = { route: String -> navController.navigate(route) }
                )
            }
            composable(Screen.Menu.route) {
                MenuScreen(onNavigate = { route: String ->
                    navController.navigate(route)
                })
            }
            composable("settings") {
                SettingsScreen(
                    onNavigate = { route: String -> navController.navigate(route) },
                    onBack = { navController.popBackStack() }
                )
            }
            composable("themes") {
                ThemesSettingsScreen(onBack = { navController.popBackStack() })
            }
            composable("accessibility") {
                AccessibilitySettingsScreen(onBack = { navController.popBackStack() })
            }
            composable("about") {
                AboutScreen(onBack = { navController.popBackStack() })
            }
            composable("group_members") {
                GroupMembersScreen(onBack = { navController.popBackStack() })
            }
            composable("profile_editor") {
                ProfileEditorScreen(onBack = { navController.popBackStack() })
            }
            composable("admin") {
                AdminPanelScreen(
                    onBack = { navController.popBackStack() }
                )
            }
            composable("security") {
                SecurityScreen(
                    onNavigate = { route: String -> navController.navigate(route) },
                    onBack = { navController.popBackStack() }
                )
            }
            composable("sessions") {
                AccountSessionsScreen(onBack = { navController.popBackStack() })
            }
            composable("email_change") {
                EmailChangeScreen(onBack = { navController.popBackStack() })
            }
            composable("password_setup") {
                PasswordSetupScreen(onBack = { navController.popBackStack() })
            }
            composable("login") {
                LoginScreen(onLoginSuccess = {
                    navController.navigate(Screen.Schedule.route) {
                        popUpTo("login") { inclusive = true }
                    }
                })
            }
        }

        if (selectedGroupId != null) {
            BottomIsland(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 24.dp),
                navController = navController,
                items = items
            )
        }
    }
}

@Composable
fun BottomIsland(
    modifier: Modifier = Modifier,
    navController: androidx.navigation.NavController,
    items: List<Screen>
) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    Surface(
        modifier = modifier
            .padding(horizontal = 16.dp)
            .height(64.dp)
            .clip(RoundedCornerShape(32.dp)),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.95f),
        tonalElevation = 8.dp,
        shadowElevation = 12.dp
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 8.dp),
            horizontalArrangement = Arrangement.SpaceAround,
            verticalAlignment = Alignment.CenterVertically
        ) {
            items.forEach { screen ->
                val selected = currentDestination?.hierarchy?.any { it.route == screen.route } == true
                IconButton(
                    onClick = {
                        navController.navigate(screen.route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = false
                            }
                            launchSingleTop = true
                            restoreState = false
                        }
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            imageVector = screen.icon,
                            contentDescription = screen.label,
                            tint = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        if (selected) {
                            Box(
                                modifier = Modifier
                                    .size(4.dp)
                                    .clip(RoundedCornerShape(2.dp))
                                    .background(MaterialTheme.colorScheme.primary)
                            )
                        }
                    }
                }
            }
        }
    }

}
