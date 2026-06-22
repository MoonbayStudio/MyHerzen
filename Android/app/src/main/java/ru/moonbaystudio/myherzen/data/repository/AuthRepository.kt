package ru.moonbaystudio.myherzen.data.repository

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import ru.moonbaystudio.myherzen.data.local.preferences.UserPreferences
import ru.moonbaystudio.myherzen.data.remote.MyHerzenApiService
import ru.moonbaystudio.myherzen.data.remote.dto.*
import ru.moonbaystudio.myherzen.util.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepository @Inject constructor(
    private val apiService: MyHerzenApiService,
    private val userPreferences: UserPreferences
) {
    private val _currentUser = MutableStateFlow<AppleUser?>(null)
    val currentUser: StateFlow<AppleUser?> = _currentUser.asStateFlow()

    val isLoggedIn = userPreferences.authToken.map { it != null }

    suspend fun login(email: String, password: String): Result<Unit> {
        val deviceIdValue = userPreferences.deviceId.first()
        val request = PasswordLoginRequest(
            email = email,
            password = password,
            deviceId = deviceIdValue,
            deviceName = android.os.Build.MODEL,
            appVersion = "1.0"
        )
        return safeApiCall { apiService.login(request) }.toResult().map { body ->
            userPreferences.saveAuthToken(body.token)
            _currentUser.value = body.user
            Unit
        }
    }

    suspend fun register(name: String, email: String, password: String): Result<Unit> {
        val request = SignupRequest(
            email = email,
            password = password,
            displayName = name
        )
        return safeApiCall { apiService.signup(request) }.toResult().map { Unit }
    }

    suspend fun verifySignup(email: String, code: String): Result<Unit> {
        val deviceIdValue = userPreferences.deviceId.first()
        val request = SignupVerifyRequest(
            email = email,
            code = code,
            deviceId = deviceIdValue,
            deviceName = android.os.Build.MODEL,
            appVersion = "1.0"
        )
        return safeApiCall { apiService.signupVerify(request) }.toResult().map { body ->
            userPreferences.saveAuthToken(body.token)
            _currentUser.value = body.user
            Unit
        }
    }

    suspend fun googleLogin(idToken: String): Result<Unit> {
        val deviceIdValue = userPreferences.deviceId.first()
        val request = GoogleLoginRequest(
            idToken = idToken,
            deviceId = deviceIdValue,
            deviceName = android.os.Build.MODEL,
            appVersion = "1.0",
            systemVersion = android.os.Build.VERSION.RELEASE
        )
        return safeApiCall { apiService.googleLogin(request) }.toResult().map { body ->
            userPreferences.saveAuthToken(body.token)
            _currentUser.value = body.user
            Unit
        }
    }

    suspend fun linkGoogle(idToken: String): Result<AppleUser> {
        val deviceIdValue = userPreferences.deviceId.first()
        val request = GoogleLoginRequest(
            idToken = idToken,
            deviceId = deviceIdValue,
            deviceName = android.os.Build.MODEL,
            appVersion = "1.0",
            systemVersion = android.os.Build.VERSION.RELEASE
        )
        return safeApiCall { apiService.linkGoogle(request) }.toResult().also { result ->
            result.onSuccess { _currentUser.value = it }
        }
    }

    suspend fun logout() {
        userPreferences.clearAuthToken()
        _currentUser.value = null
    }

    suspend fun refreshUser() {
        safeApiCall { apiService.getProfile() }.onSuccess {
            _currentUser.value = it
        }
    }

    suspend fun updateProfile(name: String): Result<AppleUser> {
        return safeApiCall { apiService.updateProfile(UpdateProfileRequest(name)) }
            .toResult()
            .also { result -> result.onSuccess { _currentUser.value = it } }
    }

    suspend fun createPassword(password: String): Result<Unit> {
        return safeApiCall { apiService.createPassword(PasswordSetupRequest(password)) }.toResult().map { Unit }
    }

    suspend fun changePassword(current: String, new: String): Result<Unit> {
        return safeApiCall { apiService.changePassword(PasswordChangeRequest(current, new)) }.toResult().map { Unit }
    }

    suspend fun requestEmailChange(email: String): Result<Unit> {
        return safeApiCall { apiService.requestEmailChange(EmailChangeRequest(email)) }.toResult().map { Unit }
    }

    suspend fun confirmEmailChange(code: String): Result<AppleUser> {
        return safeApiCall { apiService.confirmEmailChange(EmailConfirmRequest(code)) }
            .toResult()
            .also { result -> result.onSuccess { _currentUser.value = it } }
    }

    suspend fun getSessions(): List<AccountSession> {
        return safeApiCall { apiService.getSessions() }.getOrElse { emptyList() }
    }

    suspend fun revokeSession(sessionId: String): Result<Unit> {
        return safeApiCall { apiService.revokeSession(sessionId) }.toResult().map { Unit }
    }

    suspend fun logoutOthers(): Result<Unit> {
        return safeApiCall { apiService.logoutOthers() }.toResult().map { Unit }
    }

    suspend fun getMyRoleRequests(): List<RoleRequest> {
        return safeApiCall { apiService.getMyRoleRequests() }.getOrElse { emptyList() }
    }

    suspend fun createRoleRequest(type: String, groupId: Int?, groupName: String?, comment: String?): Result<RoleRequest> {
        return safeApiCall { apiService.createRoleRequest(RoleRequestCreateRequest(type, groupId, groupName, comment)) }.toResult()
    }

    suspend fun requestEmailVerification(email: String): Result<Unit> {
        return safeApiCall { apiService.requestContactEmail(ContactEmailRequest(email)) }.toResult().map { Unit }
    }

    suspend fun resendEmailVerification(): Result<Unit> {
        return safeApiCall { apiService.resendContactEmailVerification() }.toResult().map { Unit }
    }

    suspend fun getGroupUsers(groupId: Int): List<GroupUserDto> {
        return safeApiCall { apiService.getGroupUsers(groupId) }.getOrElse { emptyList() }
    }

    suspend fun getAdminUsers(): List<AdminUserDto> {
        return safeApiCall { apiService.getAdminUsers() }.getOrElse { emptyList() }
    }

    suspend fun getAdminRoleRequests(status: String): List<AdminRoleRequestDto> {
        return safeApiCall { apiService.getAdminRoleRequests(status) }.getOrElse { emptyList() }
    }

    suspend fun approveRoleRequest(requestId: Int): Result<Unit> {
        return safeApiCall { apiService.approveRoleRequest(requestId) }.toResult().map { Unit }
    }

    suspend fun rejectRoleRequest(requestId: Int): Result<Unit> {
        return safeApiCall { apiService.rejectRoleRequest(requestId) }.toResult().map { Unit }
    }

    suspend fun grantRole(userId: String, role: String): Result<Unit> {
        return safeApiCall { apiService.grantRole(GrantRoleRequest(userId, role)) }.toResult().map { Unit }
    }

    suspend fun revokeRole(userId: String, role: String): Result<Unit> {
        return safeApiCall { apiService.revokeRole(GrantRoleRequest(userId, role)) }.toResult().map { Unit }
    }

    suspend fun getAdminBadges(): List<BadgeDto> {
        return safeApiCall { apiService.getAdminBadges() }.getOrElse { emptyList() }
    }

    suspend fun grantBadge(userId: String, badgeCode: String, note: String?): Result<AdminUserDto> {
        return safeApiCall { apiService.grantBadge(userId, BadgeMutationRequest(badgeCode, note)) }.toResult()
    }

    suspend fun revokeBadge(userId: String, badgeCode: String): Result<AdminUserDto> {
        return safeApiCall { apiService.revokeBadge(userId, badgeCode) }.toResult()
    }

    suspend fun getAdminSettings(): List<AdminRuntimeSetting> {
        return safeApiCall { apiService.getAdminSettings() }.getOrElse { emptyList() }
    }

    suspend fun updateAdminSetting(key: String, value: Any): Result<AdminRuntimeSetting> {
        return safeApiCall { apiService.updateAdminSetting(key, RuntimeSettingPatchRequest(value)) }.toResult()
    }

    suspend fun getAdminSystemNotices(): List<SystemNotice> {
        return safeApiCall { apiService.getAdminSystemNotices() }.getOrElse { emptyList() }
    }

    suspend fun createAdminSystemNotice(request: SystemNoticeMutationRequest): Result<SystemNotice> {
        return safeApiCall { apiService.createAdminSystemNotice(request) }.toResult()
    }

    suspend fun updateAdminSystemNotice(id: Int, request: SystemNoticeMutationRequest): Result<SystemNotice> {
        return safeApiCall { apiService.updateAdminSystemNotice(id, request) }.toResult()
    }

    suspend fun deleteAdminSystemNotice(id: Int): Result<Unit> {
        return safeApiCall { apiService.deleteAdminSystemNotice(id) }.toResult().map { Unit }
    }

    suspend fun activateSystemNotice(id: Int): Result<Unit> {
        return safeApiCall { apiService.activateSystemNotice(id) }.toResult().map { Unit }
    }

    suspend fun deactivateSystemNotice(id: Int): Result<Unit> {
        return safeApiCall { apiService.deactivateSystemNotice(id) }.toResult().map { Unit }
    }

    suspend fun getAdminUserSessions(userId: String): List<AccountSession> {
        return safeApiCall { apiService.getAdminUserSessions(userId) }.getOrElse { emptyList() }
    }

    suspend fun revokeAdminSession(sessionId: String): Result<Unit> {
        return safeApiCall { apiService.revokeAdminSession(sessionId) }.toResult().map { Unit }
    }

    suspend fun requestPasswordReset(email: String): Result<Unit> {
        return safeApiCall { apiService.requestPasswordReset(ResetPasswordRequest(email)) }.toResult().map { Unit }
    }

    suspend fun confirmPasswordReset(code: String, newPassword: String): Result<Unit> {
        return safeApiCall { apiService.confirmPasswordReset(ResetPasswordConfirmRequest(code, newPassword)) }.toResult().map { Unit }
    }
}
