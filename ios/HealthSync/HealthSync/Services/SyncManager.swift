import Foundation
import HealthKit

/// Orchestrates fetching new HealthKit data and posting it to the backend.
@MainActor
final class SyncManager: ObservableObject {
    static let shared = SyncManager()

    @Published var lastSyncDate: Date?
    @Published var syncStatus: String = "Idle"
    @Published var isSyncing: Bool = false
    @Published var errorMessage: String?

    private let hkManager = HealthKitManager.shared
    private let apiClient = APIClient()
    private let lastSyncKey = "com.healthsync.lastSyncDate"

    private init() {
        lastSyncDate = UserDefaults.standard.object(forKey: lastSyncKey) as? Date
    }

    // MARK: - Full sync cycle

    func syncAll() async {
        guard !isSyncing else { return }
        isSyncing = true
        errorMessage = nil
        syncStatus = "Syncing..."

        do {
            // Sync each sample type
            for sampleType in hkManager.allSampleTypes {
                try await syncSampleType(sampleType)
            }

            // Sync activity summaries
            try await syncActivitySummaries()

            lastSyncDate = Date()
            UserDefaults.standard.set(lastSyncDate, forKey: lastSyncKey)
            syncStatus = "Sync complete"
        } catch {
            errorMessage = error.localizedDescription
            syncStatus = "Sync failed"
        }

        isSyncing = false
    }

    // MARK: - Sync for observer callback (single type)

    nonisolated func handleObserverUpdate(for sampleType: HKSampleType) {
        Task { @MainActor in
            guard !isSyncing else { return }
            isSyncing = true
            errorMessage = nil
            syncStatus = "Syncing \(sampleType.identifier)..."

            do {
                try await syncSampleType(sampleType)
                lastSyncDate = Date()
                UserDefaults.standard.set(lastSyncDate, forKey: lastSyncKey)
                syncStatus = "Sync complete"
            } catch {
                errorMessage = error.localizedDescription
                syncStatus = "Sync failed"
            }

            isSyncing = false
        }
    }

    // MARK: - Private

    private func syncSampleType(_ sampleType: HKSampleType) async throws {
        let (samples, newAnchor) = try await hkManager.fetchNewSamples(for: sampleType)
        guard !samples.isEmpty else { return }

        if sampleType is HKWorkoutType {
            let payloads = hkManager.convertToWorkoutPayloads(samples)
            if !payloads.isEmpty {
                _ = try await apiClient.postWorkouts(payloads)
            }
        } else {
            let payloads = hkManager.convertToRecordPayloads(samples, sampleType: sampleType)
            if !payloads.isEmpty {
                _ = try await apiClient.postRecords(payloads)
            }
        }

        if let newAnchor {
            hkManager.anchorStore.setAnchor(newAnchor, for: sampleType.identifier)
        }
    }

    private func syncActivitySummaries() async throws {
        // Sync last 7 days of activity summaries
        let since = Calendar.current.date(byAdding: .day, value: -7, to: Date()) ?? Date()
        let summaries = try await hkManager.fetchRecentActivitySummaries(since: since)
        guard !summaries.isEmpty else { return }

        let payloads = hkManager.convertToActivitySummaryPayloads(summaries)
        _ = try await apiClient.postActivitySummaries(payloads)
    }
}
