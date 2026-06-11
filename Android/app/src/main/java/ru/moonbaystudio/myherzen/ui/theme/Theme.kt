package ru.moonbaystudio.myherzen.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.graphics.Color
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary = Purple80,
    secondary = PurpleGrey80,
    tertiary = Pink80
)

private val LightColorScheme = lightColorScheme(
    primary = Purple40,
    secondary = PurpleGrey40,
    tertiary = Pink40
)

@Composable
fun MyHerzenTheme(
    appTheme: AppTheme = AppThemeCatalog.theme("classic"),
    content: @Composable () -> Unit
) {
    val colorScheme = when (appTheme.backgroundStyle) {
        ThemeBackgroundStyle.DREAMY_SKY_DAY -> lightColorScheme(primary = Color(0xFF007AFF), secondary = Color(0xFF5AC8FA))
        ThemeBackgroundStyle.DREAMY_SKY_NIGHT -> darkColorScheme(primary = Color(0xFF5AC8FA), secondary = Color(0xFF007AFF))
        ThemeBackgroundStyle.TOKYO_CITY_DAY -> lightColorScheme(primary = TokyoDayAccent)
        ThemeBackgroundStyle.TOKYO_CITY_NIGHT -> darkColorScheme(primary = TokyoNightAccent)
        ThemeBackgroundStyle.GIRLY_VIBES_DAY -> lightColorScheme(primary = GirlyDayAccent)
        ThemeBackgroundStyle.GIRLY_VIBES_NIGHT -> darkColorScheme(primary = GirlyNightAccent)
        ThemeBackgroundStyle.CHUCK_NETWORK_DAY -> lightColorScheme(primary = ChuckDayAccent)
        ThemeBackgroundStyle.CHUCK_NETWORK_NIGHT -> darkColorScheme(primary = ChuckNightAccent)
        else -> if (appTheme.isDark) DarkColorScheme else LightColorScheme
    }
    
    val view = LocalView.current
    // ... rest of the code ...
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.primary.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !appTheme.isDark
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
