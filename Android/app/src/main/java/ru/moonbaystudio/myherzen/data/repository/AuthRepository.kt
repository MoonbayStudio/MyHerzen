package ru.moonbaystudio.myherzen.data.repository

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import ru.moonbaystudio.myherzen.data.local.preferences.UserPreferences
import ru.moonbaystudio.myherzen.data.remote.*
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
        return try {
            val deviceIdValue = userPreferences.deviceId.first()
            val request = PasswordLoginRequest(
                email = email,
                password = password,
                deviceId = deviceIdValue,
                deviceName = android.os.Build.MODEL,
                appVersion = "1.0"
            )
            val response = apiService.login(request)
            if (response.isSuccessful) {
                response.body()?.let { body ->
                    userPreferences.saveAuthToken(body.token)
                    _currentUser.value = body.user
                    Result.success(Unit)
                } ?: Result.failure(Exception("Empty response body"))
            } else {
                Result.failure(Exception("Login failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun googleLogin(idToken: String): Result<Unit> {
        return try {
            val deviceIdValue = userPreferences.deviceId.first()
            val request = GoogleLoginRequest(
                idToken = idToken,
                deviceId = deviceIdValue,
                deviceName = android.os.Build.MODEL,
                appVersion = "1.0",
                systemVersion = android.os.Build.VERSION.RELEASE
            )
            val response = apiService.googleLogin(request)
            if (response.isSuccessful) {
                response.body()?.let { body ->
                    userPreferences.saveAuthToken(body.token)
                    _currentUser.value = body.user
                    Result.success(Unit)
                } ?: Result.failure(Exception("Empty body"))
            } else {
                Result.failure(Exception("Google login failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun linkGoogle(idToken: String): Result<AppleUser> {
        return try {
            val deviceIdValue = userPreferences.deviceId.first()
            val request = GoogleLoginRequest(
                idToken = idToken,
                deviceId = deviceIdValue,
                deviceName = android.os.Build.MODEL,
                appVersion = "1.0",
                systemVersion = android.os.Build.VERSION.RELEASE
            )
            val response = apiService.linkGoogle(request)
            if (response.isSuccessful) {
                val user = response.body()!!
                _currentUser.value = user
                Result.success(user)
            } else {
                Result.failure(Exception("Google link failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun logout() {
        userPreferences.clearAuthToken()
        _currentUser.value = null
    }

    suspend fun refreshUser() {
        try {
            val response = apiService.getProfile()
            if (response.isSuccessful) {
                _currentUser.value = response.body()
            }
        } catch (e: Exception) {}
    }

    suspend fun updateProfile(name: String): Result<AppleUser> {
        return try {
            val response = apiService.updateProfile(UpdateProfileRequest(name))
            if (response.isSuccessful) {
                val user = response.body()!!
                _currentUser.value = user
                Result.success(user)
            } else {
                Result.failure(Exception("Update failed: ${response.code()}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun createPassword(password: String): Result<Unit> {
        return try {
            val response = apiService.createPassword(PasswordSetupRequest(password))
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun changePassword(current: String, new: String): Result<Unit> {
        return try {
            val response = apiService.changePassword(PasswordChangeRequest(current, new))
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun requestEmailChange(email: String): Result<Unit> {
        return try {
            val response = apiService.requestEmailChange(EmailChangeRequest(email))
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun confirmEmailChange(code: String): Result<AppleUser> {
        return try {
            val response = apiService.confirmEmailChange(EmailConfirmRequest(code))
            if (response.isSuccessful) {
                val user = response.body()!!
                _currentUser.value = user
                Result.success(user)
            } else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun getSessions(): List<AccountSession> {
        return try {
            val response = apiService.getSessions()
            if (response.isSuccessful) response.body() ?: emptyList() else emptyList()
        } catch (e: Exception) { emptyList() }
    }

    suspend fun revokeSession(sessionId: String): Result<Unit> {
        return try {
            val response = apiService.revokeSession(sessionId)
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun logoutOthers(): Result<Unit> {
        return try {
            val response = apiService.logoutOthers()
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun getMyRoleRequests(): List<RoleRequest> {
        return try {
            val response = apiService.getMyRoleRequests()
            if (response.isSuccessful) response.body() ?: emptyList() else emptyList()
        } catch (e: Exception) { emptyList() }
    }

    suspend fun createRoleRequest(type: String, groupId: Int?, groupName: String?, comment: String?): Result<RoleRequest> {
        return try {
            val response = apiService.createRoleRequest(RoleRequestCreateRequest(type, groupId, groupName, comment))
            if (response.isSuccessful) response.body()?.let { Result.success(it) } ?: Result.failure(Exception("Empty body"))
            else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun requestEmailVerification(email: String): Result<Unit> {
        return try {
            val response = apiService.requestContactEmail(ContactEmailRequest(email))
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun resendEmailVerification(): Result<Unit> {
        return try {
            val response = apiService.resendContactEmailVerification()
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun getGroupUsers(groupId: Int): List<GroupUserDto> {
        return try {
            val response = apiService.getGroupUsers(groupId)
            if (response.isSuccessful) {
                response.body() ?: emptyList()
            } else {
                emptyList()
            }
        } catch (e: Exception) {
            emptyList()
        }
    }

    suspend fun getAdminUsers(): List<AdminUserDto> {
        return try {
            val response = apiService.getAdminUsers()
            if (response.isSuccessful) response.body() ?: emptyList() else emptyList()
        } catch (e: Exception) { emptyList() }
    }

    suspend fun getAdminRoleRequests(status: String): List<AdminRoleRequestDto> {
        return try {
            val response = apiService.getAdminRoleRequests(status)
            if (response.isSuccessful) response.body() ?: emptyList() else emptyList()
        } catch (e: Exception) { emptyList() }
    }

    suspend fun approveRoleRequest(requestId: Int): Result<Unit> {
        return try {
            val response = apiService.approveRoleRequest(requestId)
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun rejectRoleRequest(requestId: Int): Result<Unit> {
        return try {
            val response = apiService.rejectRoleRequest(requestId)
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun grantRole(userId: Int, role: String): Result<Unit> {
        return try {
            val response = apiService.grantRole(ru.moonbaystudio.myherzen.data.remote.GrantRoleRequest(userId, role))
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun clearCache() {
        // Implement clearing logic
    }

    suspend fun requestPasswordReset(email: String): Result<Unit> {
        return try {
            val response = apiService.requestPasswordReset(ResetPasswordRequest(email))
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }

    suspend fun confirmPasswordReset(code: String, newPassword: String): Result<Unit> {
        return try {
            val response = apiService.confirmPasswordReset(ResetPasswordConfirmRequest(code, newPassword))
            if (response.isSuccessful) Result.success(Unit) else Result.failure(Exception("Error ${response.code()}"))
        } catch (e: Exception) { Result.failure(e) }
    }
}
