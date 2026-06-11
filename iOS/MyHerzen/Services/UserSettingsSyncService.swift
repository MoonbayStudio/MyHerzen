import Foundation

enum UserSettingsSyncService {
    static let didUpdateSelectedGroup = Notification.Name("MyHerzenDidUpdateSelectedGroup")
    private static let appGroupID = "group.myherzen.shared"
    private static let selectedGroupIdKey = "selectedGroupId"
    private static let selectedGroupNameKey = "selectedGroupName"
    private static let offlineScheduleEnabledKey = "offlineScheduleEnabled"
    private static let offlineScheduleWeeksKey = "offlineScheduleWeeks"
    private static let liveActivityEnabledKey = "liveActivityEnabled"

    static func apply(_ settings: UserSettings) {
        let cacheWeeks = min(max(settings.scheduleCacheWeeks, 0), 4)
        let offlineEnabled = cacheWeeks > 0
        UserDefaults.standard.set(offlineEnabled, forKey: offlineScheduleEnabledKey)
        UserDefaults.standard.set(max(cacheWeeks, 1), forKey: offlineScheduleWeeksKey)
        UserDefaults.standard.set(settings.liveActivityEnabled, forKey: liveActivityEnabledKey)
        UserDefaults(suiteName: appGroupID)?.set(offlineEnabled, forKey: offlineScheduleEnabledKey)
        UserDefaults(suiteName: appGroupID)?.set(max(cacheWeeks, 1), forKey: offlineScheduleWeeksKey)
        UserDefaults(suiteName: appGroupID)?.set(settings.liveActivityEnabled, forKey: liveActivityEnabledKey)

        guard let groupId = settings.selectedGroupId else { return }
        let groupIdString = String(groupId)
        let groupName = settings.selectedGroupName ?? groupIdString
        UserDefaults.standard.set(groupIdString, forKey: selectedGroupIdKey)
        UserDefaults.standard.set(groupName, forKey: selectedGroupNameKey)
        UserDefaults(suiteName: appGroupID)?.set(groupIdString, forKey: selectedGroupIdKey)
        UserDefaults(suiteName: appGroupID)?.set(groupName, forKey: selectedGroupNameKey)

        NotificationCenter.default.post(
            name: didUpdateSelectedGroup,
            object: nil,
            userInfo: [
                "groupId": groupIdString,
                "groupName": groupName
            ]
        )
    }

    static func syncRemoteSettingsIfAuthenticated() async {
        guard AuthSessionManager.shared.isAuthenticated else { return }
        do {
            let settings = try await APIService.shared.fetchSettings()
            await MainActor.run {
                apply(settings)
            }
        } catch {
            print("[UserSettingsSyncService] settings sync failed: \(error)")
            if case APIServiceError.httpStatus(401) = error {
                await MainActor.run {
                    AuthSessionManager.shared.signOut()
                }
            }
        }
    }

    static func updateRemoteSelectedGroupIfAuthenticated(_ group: MyGroup) async {
        UserDefaults.standard.set(group.id, forKey: selectedGroupIdKey)
        UserDefaults.standard.set(group.name, forKey: selectedGroupNameKey)
        UserDefaults(suiteName: appGroupID)?.set(group.id, forKey: selectedGroupIdKey)
        UserDefaults(suiteName: appGroupID)?.set(group.name, forKey: selectedGroupNameKey)

        guard AuthSessionManager.shared.isAuthenticated,
              let groupId = Int(group.id) else { return }
        do {
            _ = try await APIService.shared.updateSettings(
                selectedGroupId: groupId,
                selectedGroupName: group.name,
                scheduleCacheWeeks: UserDefaults.standard.bool(forKey: offlineScheduleEnabledKey)
                    ? UserDefaults.standard.integer(forKey: offlineScheduleWeeksKey)
                    : 0,
                liveActivityEnabled: localLiveActivityEnabled
            )
        } catch {
            print("[UserSettingsSyncService] selected group sync failed: \(error)")
            if case APIServiceError.httpStatus(401) = error {
                await MainActor.run {
                    AuthSessionManager.shared.signOut()
                }
            }
        }
    }

    private static var localLiveActivityEnabled: Bool {
        guard UserDefaults.standard.object(forKey: liveActivityEnabledKey) != nil else { return true }
        return UserDefaults.standard.bool(forKey: liveActivityEnabledKey)
    }
}
