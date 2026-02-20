import SwiftUI

struct ContentView: View {
    @StateObject private var syncManager = SyncManager.shared
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            List {
                Section("Status") {
                    HStack {
                        Text("Sync Status")
                        Spacer()
                        Text(syncManager.syncStatus)
                            .foregroundStyle(.secondary)
                    }

                    if let lastSync = syncManager.lastSyncDate {
                        HStack {
                            Text("Last Sync")
                            Spacer()
                            Text(lastSync, style: .relative)
                                .foregroundStyle(.secondary)
                        }
                    }

                    if let error = syncManager.errorMessage {
                        Text(error)
                            .foregroundStyle(.red)
                            .font(.caption)
                    }
                }

                Section("Data Types") {
                    ForEach(HealthKitManager.shared.allSampleTypes, id: \.identifier) { type in
                        Text(type.identifier.replacingOccurrences(of: "HKQuantityTypeIdentifier", with: "")
                            .replacingOccurrences(of: "HKCategoryTypeIdentifier", with: "")
                            .replacingOccurrences(of: "HKWorkoutType", with: "Workouts"))
                    }
                    Text("Activity Summaries")
                }

                Section {
                    Button {
                        Task { await syncManager.syncAll() }
                    } label: {
                        HStack {
                            Spacer()
                            if syncManager.isSyncing {
                                ProgressView()
                                    .padding(.trailing, 8)
                            }
                            Text(syncManager.isSyncing ? "Syncing..." : "Sync Now")
                                .fontWeight(.semibold)
                            Spacer()
                        }
                    }
                    .disabled(syncManager.isSyncing)
                }
            }
            .navigationTitle("HealthSync")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showSettings = true
                    } label: {
                        Image(systemName: "gear")
                    }
                }
            }
            .sheet(isPresented: $showSettings) {
                SettingsView()
            }
        }
    }
}
