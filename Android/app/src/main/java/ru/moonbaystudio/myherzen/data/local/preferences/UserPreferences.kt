package ru.moonbaystudio.myherzen.data.local.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "user_prefs")

@Singleton
class UserPreferences @Inject constructor(@ApplicationContext private val context: Context) {

    private val TOKEN_KEY = stringPreferencesKey("auth_token")
    private val GROUP_ID_KEY = intPreferencesKey("selected_group_id")
    private val GROUP_NAME_KEY = stringPreferencesKey("selected_group_name")
    private val THEME_ID_KEY = stringPreferencesKey("selected_theme_id")
    
    // Accessibility
    private val REDUCE_MOTION_KEY = booleanPreferencesKey("accessibility_reduce_motion")
    private val HIGH_CONTRAST_KEY = booleanPreferencesKey("accessibility_high_contrast")
    private val LARGER_TEXT_KEY = booleanPreferencesKey("accessibility_larger_text")
    private val AUTO_SPEAK_SCHEDULE_KEY = booleanPreferencesKey("accessibility_auto_speak_schedule")
    private val SPEECH_DETAILED_KEY = booleanPreferencesKey("accessibility_speech_detailed")
    private val HAPTICS_ENABLED_KEY = booleanPreferencesKey("accessibility_haptics_enabled")
    private val DEFAULT_PERSONA_KEY = stringPreferencesKey("assistant_default_persona")
    private val DEVICE_ID_KEY = stringPreferencesKey("device_id")
    
    // Cache & Live Activity
    private val SCHEDULE_CACHE_WEEKS_KEY = intPreferencesKey("schedule_cache_weeks")
    private val LIVE_ACTIVITY_ENABLED_KEY = booleanPreferencesKey("live_activity_enabled")

    val authToken: Flow<String?> = context.dataStore.data.map { it[TOKEN_KEY] }
    val selectedGroupId: Flow<Int?> = context.dataStore.data.map { it[GROUP_ID_KEY] }
    val selectedGroupName: Flow<String?> = context.dataStore.data.map { it[GROUP_NAME_KEY] }
    val selectedThemeId: Flow<String> = context.dataStore.data.map { it[THEME_ID_KEY] ?: "classic" }

    val reduceMotion: Flow<Boolean> = context.dataStore.data.map { it[REDUCE_MOTION_KEY] ?: false }
    val highContrast: Flow<Boolean> = context.dataStore.data.map { it[HIGH_CONTRAST_KEY] ?: false }
    val largerText: Flow<Boolean> = context.dataStore.data.map { it[LARGER_TEXT_KEY] ?: false }
    val autoSpeakSchedule: Flow<Boolean> = context.dataStore.data.map { it[AUTO_SPEAK_SCHEDULE_KEY] ?: false }
    val speechDetailed: Flow<Boolean> = context.dataStore.data.map { it[SPEECH_DETAILED_KEY] ?: true }
    val hapticsEnabled: Flow<Boolean> = context.dataStore.data.map { it[HAPTICS_ENABLED_KEY] ?: true }
    val defaultPersona: Flow<String> = context.dataStore.data.map { it[DEFAULT_PERSONA_KEY] ?: "pelikasha" }
    
    val scheduleCacheWeeks: Flow<Int> = context.dataStore.data.map { it[SCHEDULE_CACHE_WEEKS_KEY] ?: 2 }
    val liveActivityEnabled: Flow<Boolean> = context.dataStore.data.map { it[LIVE_ACTIVITY_ENABLED_KEY] ?: true }
    
    val deviceId: Flow<String> = context.dataStore.data.map { 
        it[DEVICE_ID_KEY] ?: run {
            val newId = java.util.UUID.randomUUID().toString()
            saveDeviceId(newId)
            newId
        }
    }

    suspend fun saveAuthToken(token: String) {
        context.dataStore.edit { it[TOKEN_KEY] = token }
    }

    suspend fun clearAuthToken() {
        context.dataStore.edit { it.remove(TOKEN_KEY) }
    }

    suspend fun saveSelectedGroup(id: Int, name: String) {
        context.dataStore.edit {
            it[GROUP_ID_KEY] = id
            it[GROUP_NAME_KEY] = name
        }
    }

    suspend fun saveThemeId(themeId: String) {
        context.dataStore.edit { it[THEME_ID_KEY] = themeId }
    }

    suspend fun updateReduceMotion(enabled: Boolean) {
        context.dataStore.edit { it[REDUCE_MOTION_KEY] = enabled }
    }

    suspend fun updateHighContrast(enabled: Boolean) {
        context.dataStore.edit { it[HIGH_CONTRAST_KEY] = enabled }
    }

    suspend fun updateLargerText(enabled: Boolean) {
        context.dataStore.edit { it[LARGER_TEXT_KEY] = enabled }
    }

    suspend fun updateAutoSpeakSchedule(enabled: Boolean) {
        context.dataStore.edit { it[AUTO_SPEAK_SCHEDULE_KEY] = enabled }
    }

    suspend fun updateSpeechDetailed(enabled: Boolean) {
        context.dataStore.edit { it[SPEECH_DETAILED_KEY] = enabled }
    }

    suspend fun updateHapticsEnabled(enabled: Boolean) {
        context.dataStore.edit { it[HAPTICS_ENABLED_KEY] = enabled }
    }

    suspend fun updateDefaultPersona(persona: String) {
        context.dataStore.edit { it[DEFAULT_PERSONA_KEY] = persona }
    }

    suspend fun updateScheduleCacheWeeks(weeks: Int) {
        context.dataStore.edit { it[SCHEDULE_CACHE_WEEKS_KEY] = weeks }
    }

    suspend fun updateLiveActivityEnabled(enabled: Boolean) {
        context.dataStore.edit { it[LIVE_ACTIVITY_ENABLED_KEY] = enabled }
    }

    private suspend fun saveDeviceId(id: String) {
        context.dataStore.edit { it[DEVICE_ID_KEY] = id }
    }
}
