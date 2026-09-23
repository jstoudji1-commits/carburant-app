import Capacitor
import Foundation
import StoreKit

@objc(OptiPleinPurchasesPlugin)
public class OptiPleinPurchasesPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "OptiPleinPurchasesPlugin"
    public let jsName = "OptiPleinPurchases"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "isAvailable", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "purchase", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "restore", returnType: CAPPluginReturnPromise)
    ]

    @objc func isAvailable(_ call: CAPPluginCall) {
        if #available(iOS 15.0, *) {
            call.resolve(["available": true])
        } else {
            call.resolve(["available": false])
        }
    }

    @objc func purchase(_ call: CAPPluginCall) {
        guard #available(iOS 15.0, *) else {
            call.reject("Les achats intégrés nécessitent iOS 15 ou plus.")
            return
        }

        guard let productId = call.getString("productId"), !productId.isEmpty else {
            call.reject("Identifiant produit Apple manquant.")
            return
        }

        Task {
            do {
                let products = try await Product.products(for: [productId])
                guard let product = products.first else {
                    call.reject("Produit Premium introuvable dans l'App Store.")
                    return
                }

                let result = try await product.purchase()

                switch result {
                case .success(let verification):
                    switch verification {
                    case .verified(let transaction):
                        await transaction.finish()
                        call.resolve(payload(for: transaction, signedTransaction: verification.jwsRepresentation))
                    case .unverified(_, let error):
                        call.reject("Achat non vérifié par Apple.", nil, error)
                    }
                case .userCancelled:
                    call.reject("Achat annulé.", "cancelled")
                case .pending:
                    call.reject("Achat en attente de validation Apple.", "pending")
                @unknown default:
                    call.reject("Réponse Apple inconnue.")
                }
            } catch {
                call.reject(error.localizedDescription, nil, error)
            }
        }
    }

    @objc func restore(_ call: CAPPluginCall) {
        guard #available(iOS 15.0, *) else {
            call.reject("La restauration nécessite iOS 15 ou plus.")
            return
        }

        guard let productId = call.getString("productId"), !productId.isEmpty else {
            call.reject("Identifiant produit Apple manquant.")
            return
        }

        Task {
            do {
                try await AppStore.sync()

                for await entitlement in Transaction.currentEntitlements {
                    switch entitlement {
                    case .verified(let transaction):
                        if transaction.productID == productId {
                            call.resolve(payload(for: transaction, signedTransaction: entitlement.jwsRepresentation))
                            return
                        }
                    case .unverified:
                        continue
                    }
                }

                call.reject("Aucun abonnement Apple actif trouvé.", "not_found")
            } catch {
                call.reject(error.localizedDescription, nil, error)
            }
        }
    }

    @available(iOS 15.0, *)
    private func payload(for transaction: Transaction, signedTransaction: String) -> JSObject {
        var data = JSObject()
        data["productId"] = transaction.productID
        data["transactionId"] = String(transaction.id)
        data["originalTransactionId"] = String(transaction.originalID)
        data["purchaseDate"] = isoDate(transaction.purchaseDate)
        data["expirationDate"] = transaction.expirationDate.map { isoDate($0) } ?? ""
        data["signedTransaction"] = signedTransaction
        return data
    }

    private func isoDate(_ date: Date) -> String {
        ISO8601DateFormatter().string(from: date)
    }
}
