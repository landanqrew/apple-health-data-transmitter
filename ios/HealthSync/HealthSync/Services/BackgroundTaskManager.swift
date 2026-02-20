import BackgroundTasks
import Foundation

/// Manages BGAppRefreshTask as a fallback sync mechanism.
final class BackgroundTaskManager {
    static let taskIdentifier = "com.healthsync.refresh"

    static func register() {
        BGTaskScheduler.shared.register(
            forTaskWithIdentifier: taskIdentifier,
            using: nil
        ) { task in
            guard let refreshTask = task as? BGAppRefreshTask else { return }
            handleRefresh(task: refreshTask)
        }
    }

    static func scheduleNextRefresh() {
        let request = BGAppRefreshTaskRequest(identifier: taskIdentifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 60 * 60) // 1 hour
        do {
            try BGTaskScheduler.shared.submit(request)
        } catch {
            print("Failed to schedule background refresh: \(error.localizedDescription)")
        }
    }

    private static func handleRefresh(task: BGAppRefreshTask) {
        // Schedule the next one immediately
        scheduleNextRefresh()

        let syncTask = Task {
            await SyncManager.shared.syncAll()
        }

        task.expirationHandler = {
            syncTask.cancel()
        }

        Task {
            await syncTask.value
            task.setTaskCompleted(success: true)
        }
    }
}
