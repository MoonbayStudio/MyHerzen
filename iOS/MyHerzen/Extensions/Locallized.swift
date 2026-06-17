import Foundation

extension String {
    var myherzenTrimmed: String {
        trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var myherzenNormalizedGroupKey: String {
        myherzenTrimmed
            .lowercased()
            .replacingOccurrences(of: " ", with: "")
            .replacingOccurrences(of: "-", with: "")
            .replacingOccurrences(of: "_", with: "")
            .replacingOccurrences(of: "№", with: "")
    }
}
