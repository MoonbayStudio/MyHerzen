import Foundation
internal import Combine

struct PremiumProduct: Identifiable, Equatable {
    let id: String
    let displayPrice: String
}

@MainActor
final class SubscriptionManager: ObservableObject {
    static let shared = SubscriptionManager()

    @Published private(set) var products: [PremiumProduct] = []
    @Published private(set) var hasPremium = false
    @Published private(set) var isLoading = false
    @Published var errorMessage: String?

    private init() {}

    func bootstrap() async {
        guard products.isEmpty else { return }
        products = []
    }

    func purchase() async {
        errorMessage = "Покупки пока не настроены для этой сборки."
    }

    func restorePurchases() async {
        errorMessage = "Восстановление покупок пока не настроено для этой сборки."
    }
}
