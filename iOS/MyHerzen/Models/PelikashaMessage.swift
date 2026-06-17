import Foundation

enum PelikashaMessageRole: String, Codable {
    case user
    case assistant
}

struct PelikashaMessage: Identifiable, Codable, Equatable {
    let id: UUID
    let role: PelikashaMessageRole
    let text: String
    let createdAt: Date

    init(id: UUID = UUID(), role: PelikashaMessageRole, text: String, createdAt: Date = Date()) {
        self.id = id
        self.role = role
        self.text = text
        self.createdAt = createdAt
    }
}
