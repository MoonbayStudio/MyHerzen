package ru.moonbaystudio.myherzen.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.Response
import retrofit2.http.*

interface MyHerzenApiService {
    @POST("auth/login")
    suspend fun login(@Body request: PasswordLoginRequest): Response<AppleSignInResponse>

    @GET("me")
    suspend fun getCurrentUser(): Response<AppleUser>

    @GET("profile")
    suspend fun getProfile(): Response<AppleUser>

    @PUT("profile")
    suspend fun updateProfile(@Body request: UpdateProfileRequest): Response<AppleUser>

    @GET("settings")
    suspend fun getSettings(): Response<UserSettings>

    @PUT("settings")
    suspend fun updateSettings(@Body settings: UserSettings): Response<UserSettings>

    @POST("me/password/create")
    suspend fun createPassword(@Body request: PasswordSetupRequest): Response<Unit>

    @POST("me/password/change")
    suspend fun changePassword(@Body request: PasswordChangeRequest): Response<Unit>

    @POST("auth/password/reset-request")
    suspend fun requestPasswordReset(@Body request: ResetPasswordRequest): Response<Unit>

    @POST("auth/password/reset-confirm")
    suspend fun confirmPasswordReset(@Body request: ResetPasswordConfirmRequest): Response<Unit>

    @POST("me/email/change-request")
    suspend fun requestEmailChange(@Body request: EmailChangeRequest): Response<Unit>

    @POST("me/email/confirm")
    suspend fun confirmEmailChange(@Body request: EmailConfirmRequest): Response<AppleUser>

    @POST("auth/contact-email/request")
    suspend fun requestContactEmail(@Body request: ContactEmailRequest): Response<Unit>

    @POST("auth/contact-email/resend-verification")
    suspend fun resendContactEmailVerification(): Response<Unit>

    @GET("account/sessions")
    suspend fun getSessions(): Response<List<AccountSession>>

    @DELETE("account/sessions/{sessionId}")
    suspend fun revokeSession(@Path("sessionId") sessionId: String): Response<Unit>

    @POST("account/sessions/logout-others")
    suspend fun logoutOthers(): Response<Unit>

    @POST("role-requests")
    suspend fun createRoleRequest(@Body request: RoleRequestCreateRequest): Response<RoleRequest>

    @GET("role-requests/me")
    suspend fun getMyRoleRequests(): Response<List<RoleRequest>>

    @GET("groups/{groupId}/homeworks")
    suspend fun getGroupHomeworks(
        @Path("groupId") groupId: Int,
        @Query("date") date: String?
    ): Response<List<Homework>>

    @POST("groups/{groupId}/homeworks")
    suspend fun createHomework(
        @Path("groupId") groupId: Int,
        @Body request: HomeworkMutationRequest
    ): Response<Homework>

    @PATCH("groups/{groupId}/homeworks/{homeworkId}")
    suspend fun updateHomework(
        @Path("groupId") groupId: Int,
        @Path("homeworkId") homeworkId: String,
        @Body request: HomeworkUpdateRequest
    ): Response<Homework>

    @DELETE("groups/{groupId}/homeworks/{homeworkId}")
    suspend fun deleteHomework(
        @Path("groupId") groupId: Int,
        @Path("homeworkId") homeworkId: String
    ): Response<Unit>

    @POST("assistant/chat")
    suspend fun assistantChat(@Body request: AssistantChatRequest): Response<AssistantChatResponse>

    @POST("auth/google")
    suspend fun googleLogin(@Body request: GoogleLoginRequest): Response<AppleSignInResponse>

    @POST("me/providers/google")
    suspend fun linkGoogle(@Body request: GoogleLoginRequest): Response<AppleUser>

    @GET("groups/{groupId}/users")
    suspend fun getGroupUsers(@Path("groupId") groupId: Int): Response<List<GroupUserDto>>

    @GET("admin/users")
    suspend fun getAdminUsers(): Response<List<AdminUserDto>>

    @GET("admin/role-requests")
    suspend fun getAdminRoleRequests(@Query("status") status: String): Response<List<AdminRoleRequestDto>>

    @POST("admin/role-requests/{requestId}/approve")
    suspend fun approveRoleRequest(@Path("requestId") requestId: Int): Response<Unit>

    @POST("admin/role-requests/{requestId}/reject")
    suspend fun rejectRoleRequest(@Path("requestId") requestId: Int): Response<Unit>

    @POST("admin/roles/grant")
    suspend fun grantRole(@Body request: GrantRoleRequest): Response<Unit>
}

data class GrantRoleRequest(
    @SerializedName("user_id") val userId: Int,
    val role: String
)

data class GoogleLoginRequest(
    val idToken: String,
    val deviceId: String?,
    val deviceName: String?,
    val platform: String = "android",
    @SerializedName("appVersion") val appVersion: String?,
    @SerializedName("systemVersion") val systemVersion: String?
)

data class AssistantChatRequest(
    val message: String,
    val persona: String,
    val context: AssistantContext,
    @SerializedName("conversationId") val conversationId: String,
    @SerializedName("groupId") val groupId: Int?,
    @SerializedName("targetDate") val targetDate: String?,
    @SerializedName("cachedSchedule") val cachedSchedule: CachedSchedulePayload?
)

data class AssistantContext(
    @SerializedName("selectedGroupId") val selectedGroupId: Int?,
    @SerializedName("selectedDate") val selectedDate: String?
)

data class CachedSchedulePayload(
    @SerializedName("generatedAt") val generatedAt: String,
    val source: String = "android_cache",
    val lessons: List<CachedScheduleLessonPayload>
)

data class CachedScheduleLessonPayload(
    val name: String,
    val type: String?,
    @SerializedName("startTime") val startTime: String,
    @SerializedName("endTime") val endTime: String,
    val date: String,
    val room: String?,
    val teacher: String?,
    @SerializedName("roomId") val roomId: Int?,
    @SerializedName("teacherId") val teacherId: Int?,
    @SerializedName("classUrl") val classUrl: String?,
    val note: String?,
    @SerializedName("isExam") val isExam: Boolean?
)

data class AssistantChatResponse(
    val reply: String,
    val remaining: Int,
    val plan: String
)

data class PasswordLoginRequest(
    val email: String,
    val password: String,
    @SerializedName("deviceId") val deviceId: String?,
    @SerializedName("deviceName") val deviceName: String?,
    val platform: String = "android",
    @SerializedName("appVersion") val appVersion: String?
)

data class AppleSignInResponse(
    val token: String,
    val user: AppleUser
)

data class UserRole(
    val type: String,
    val title: String,
    @SerializedName("groupId") val groupId: Int?
)

data class BadgeDto(
    val code: String,
    val title: String,
    val description: String?,
    @SerializedName("icon_name") val iconName: String,
    val rarity: String
)

data class AppleUser(
    val id: String,
    @SerializedName("displayName") val displayName: String? = null,
    val email: String?,
    @SerializedName("appleEmail") val appleEmail: String?,
    @SerializedName("contactEmail") val contactEmail: String?,
    @SerializedName("contactEmailVerified") val contactEmailVerified: Boolean = false,
    @SerializedName("pendingContactEmail") val pendingContactEmail: String?,
    @SerializedName("needsContactEmail") val needsContactEmail: Boolean = false,
    @SerializedName("isAppleRelayEmail") val isAppleRelayEmail: Boolean = false,
    val roles: List<UserRole> = emptyList(),
    val badges: List<BadgeDto> = emptyList(),
    val tier: String = "free",
    @SerializedName("remainingToday") val remainingToday: Int? = null,
    @SerializedName("scheduleCacheWeeks") val scheduleCacheWeeks: Int = 2,
    @SerializedName("liveActivityEnabled") val liveActivityEnabled: Boolean = true,
    @SerializedName("hasPassword") val hasPassword: Boolean = false,
    @SerializedName("emailVerified") val emailVerified: Boolean = false,
    @SerializedName("pendingEmail") val pendingEmail: String?,
    @SerializedName("linkedProviders") val linkedProviders: List<String> = emptyList()
) {
    val isAdmin: Boolean get() = roles.any { it.type == "admin" }
    val isModerator: Boolean get() = roles.any { it.type == "moderator" }
    val isGroupLeader: Boolean get() = roles.any { it.type == "group_leader" }
    val isTester: Boolean get() = roles.any { it.type == "tester" }

    val name: String? get() = displayName
}

data class UserSettings(
    @SerializedName("selectedGroupId") val selectedGroupId: Int?,
    @SerializedName("selectedGroupName") val selectedGroupName: String?,
    @SerializedName("scheduleCacheWeeks") val scheduleCacheWeeks: Int = 2,
    @SerializedName("liveActivityEnabled") val liveActivityEnabled: Boolean = true
)

data class Homework(
    val id: String,
    @SerializedName("group_id") val groupId: Int,
    @SerializedName("lesson_date") val lessonDate: String,
    @SerializedName("lesson_time") val lessonTime: String,
    val subject: String,
    val teacher: String?,
    val room: String?,
    val text: String,
    @SerializedName("created_by") val createdBy: String?,
    @SerializedName("created_at") val createdAt: String?,
    @SerializedName("updated_at") val updatedAt: String?
)

data class HomeworkMutationRequest(
    @SerializedName("lesson_date") val lessonDate: String,
    @SerializedName("lesson_time") val lessonTime: String,
    val subject: String,
    val teacher: String?,
    val room: String?,
    val text: String
)

data class HomeworkUpdateRequest(
    val text: String
)

data class UpdateProfileRequest(val displayName: String)

data class PasswordSetupRequest(val password: String)

data class PasswordChangeRequest(
    val currentPassword: String,
    val newPassword: String
)

data class ResetPasswordRequest(val email: String)

data class ResetPasswordConfirmRequest(
    val code: String,
    val newPassword: String
)

data class EmailChangeRequest(val email: String)

data class EmailConfirmRequest(val code: String)

data class ContactEmailRequest(val email: String)

data class AccountSession(
    val id: String,
    @SerializedName("device_name") val deviceName: String,
    val platform: String,
    @SerializedName("last_active_at") val lastActiveAt: String,
    @SerializedName("is_current") val isCurrent: Boolean
)

data class RoleRequestCreateRequest(
    @SerializedName("role_type") val roleType: String,
    @SerializedName("group_id") val groupId: Int?,
    @SerializedName("group_name") val groupName: String?,
    val comment: String?
)

data class RoleRequest(
    val id: String,
    @SerializedName("role_type") val roleType: String,
    val status: String,
    @SerializedName("created_at") val createdAt: String
)

data class GroupUserDto(
    val id: String,
    val email: String?,
    val name: String?,
    @SerializedName("group_id") val groupId: Int,
    val roles: List<UserRole>,
    val badges: List<BadgeDto> = emptyList(),
    val tier: String
)

data class AdminUserDto(
    val id: String,
    val email: String?,
    val name: String?,
    val roles: List<UserRole>,
    val badges: List<BadgeDto> = emptyList(),
    @SerializedName("remainingToday") val remainingToday: Int,
    val tier: String
)

data class AdminRoleRequestDto(
    val id: Int,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("user_email") val userEmail: String?,
    @SerializedName("role_type") val roleType: String,
    val status: String,
    @SerializedName("created_at") val createdAt: String
)
