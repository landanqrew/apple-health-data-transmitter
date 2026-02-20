import SwiftUI
import HealthKit

@main
struct HealthSyncApp: App {
    @Environment(\.scenePhase) private var scenePhase

    init() {
        BackgroundTaskManager.register()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .task {
                    await setup()
                }
        }
        .onChange(of: scenePhase) { _, newPhase in
            if newPhase == .background {
                BackgroundTaskManager.scheduleNextRefresh()
            }
        }
    }

    private func setup() async {
        guard HKHealthStore.isHealthDataAvailable() else { return }

        let hkManager = HealthKitManager.shared

        do {
            try await hkManager.requestAuthorization()
        } catch {
            print("HealthKit authorization failed: \(error.localizedDescription)")
            return
        }

        hkManager.enableBackgroundDelivery()

        hkManager.startObserving { sampleType in
            SyncManager.shared.handleObserverUpdate(for: sampleType)
        }
    }
}
