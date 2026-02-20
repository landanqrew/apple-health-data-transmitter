import Foundation
import HealthKit

/// Persists HKQueryAnchor per sample type in UserDefaults for incremental sync.
final class AnchorStore {
    private let defaults: UserDefaults
    private let prefix = "com.healthsync.anchor."

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    func anchor(for identifier: String) -> HKQueryAnchor? {
        guard let data = defaults.data(forKey: prefix + identifier) else { return nil }
        return try? NSKeyedUnarchiver.unarchivedObject(
            ofClass: HKQueryAnchor.self,
            from: data
        )
    }

    func setAnchor(_ anchor: HKQueryAnchor, for identifier: String) {
        guard let data = try? NSKeyedArchiver.archivedData(
            withRootObject: anchor,
            requiringSecureCoding: true
        ) else { return }
        defaults.set(data, forKey: prefix + identifier)
    }
}
