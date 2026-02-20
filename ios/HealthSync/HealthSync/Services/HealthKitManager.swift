import Foundation
import HealthKit

/// Manages HealthKit authorization, observer queries, and anchored object queries.
final class HealthKitManager {
    static let shared = HealthKitManager()

    let healthStore = HKHealthStore()
    let anchorStore = AnchorStore()

    /// All quantity types we track.
    let quantityTypes: [HKQuantityType] = [
        HKQuantityType(.stepCount),
        HKQuantityType(.heartRate),
        HKQuantityType(.restingHeartRate),
        HKQuantityType(.heartRateVariabilitySDNN),
        HKQuantityType(.vo2Max),
        HKQuantityType(.activeEnergyBurned),
        HKQuantityType(.basalEnergyBurned),
        HKQuantityType(.distanceWalkingRunning),
        HKQuantityType(.appleExerciseTime),
    ]

    /// Category types we track.
    let categoryTypes: [HKCategoryType] = [
        HKCategoryType(.sleepAnalysis),
    ]

    /// All sample types (quantity + category).
    var allSampleTypes: [HKSampleType] {
        quantityTypes + categoryTypes + [HKWorkoutType.workoutType()]
    }

    /// All types we want to read.
    var allReadTypes: Set<HKObjectType> {
        var types = Set<HKObjectType>(allSampleTypes)
        types.insert(HKObjectType.activitySummaryType())
        return types
    }

    // Preferred units per quantity type.
    private let preferredUnits: [HKQuantityTypeIdentifier: HKUnit] = [
        .stepCount: .count(),
        .heartRate: HKUnit.count().unitDivided(by: .minute()),
        .restingHeartRate: HKUnit.count().unitDivided(by: .minute()),
        .heartRateVariabilitySDNN: .secondUnit(with: .milli),
        .vo2Max: HKUnit.literUnit(with: .milli).unitDivided(by: HKUnit.gramUnit(with: .kilo).unitMultiplied(by: .minute())),
        .activeEnergyBurned: .kilocalorie(),
        .basalEnergyBurned: .kilocalorie(),
        .distanceWalkingRunning: .meter(),
        .appleExerciseTime: .minute(),
    ]

    private var observerQueries: [HKObserverQuery] = []

    private init() {}

    // MARK: - Authorization

    func requestAuthorization() async throws {
        try await healthStore.requestAuthorization(toShare: [], read: allReadTypes)
    }

    // MARK: - Background delivery

    func enableBackgroundDelivery() {
        for sampleType in allSampleTypes {
            healthStore.enableBackgroundDelivery(for: sampleType, frequency: .hourly) { success, error in
                if let error {
                    print("Background delivery error for \(sampleType.identifier): \(error.localizedDescription)")
                }
            }
        }
    }

    // MARK: - Observer queries

    func startObserving(onUpdate: @escaping (HKSampleType) -> Void) {
        for sampleType in allSampleTypes {
            let query = HKObserverQuery(sampleType: sampleType, predicate: nil) { _, completionHandler, error in
                if let error {
                    print("Observer error for \(sampleType.identifier): \(error.localizedDescription)")
                    completionHandler()
                    return
                }
                onUpdate(sampleType)
                completionHandler()
            }
            healthStore.execute(query)
            observerQueries.append(query)
        }
    }

    // MARK: - Anchored queries

    func fetchNewSamples(for sampleType: HKSampleType) async throws -> ([HKSample], HKQueryAnchor?) {
        let currentAnchor = anchorStore.anchor(for: sampleType.identifier)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKAnchoredObjectQuery(
                type: sampleType,
                predicate: nil,
                anchor: currentAnchor,
                limit: HKObjectQueryNoLimit
            ) { _, added, _, newAnchor, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                continuation.resume(returning: (added ?? [], newAnchor))
            }
            healthStore.execute(query)
        }
    }

    // MARK: - Activity summaries

    func fetchRecentActivitySummaries(since date: Date) async throws -> [HKActivitySummary] {
        let calendar = Calendar.current
        let start = calendar.dateComponents([.year, .month, .day, .era], from: date)
        let end = calendar.dateComponents([.year, .month, .day, .era], from: Date())
        let predicate = HKQuery.predicate(forActivitySummariesBetweenStart: start, end: end)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKActivitySummaryQuery(predicate: predicate) { _, summaries, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                continuation.resume(returning: summaries ?? [])
            }
            healthStore.execute(query)
        }
    }

    // MARK: - Conversion helpers

    private static let iso8601: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    func formatDate(_ date: Date) -> String {
        Self.iso8601.string(from: date)
    }

    func convertToRecordPayloads(_ samples: [HKSample], sampleType: HKSampleType) -> [HealthRecordPayload] {
        samples.compactMap { sample in
            let valueStr: String?
            let unitStr: String?

            if let quantitySample = sample as? HKQuantitySample,
               let qtypeId = HKQuantityTypeIdentifier(rawValue: sampleType.identifier),
               let unit = preferredUnits[qtypeId] {
                valueStr = String(quantitySample.quantity.doubleValue(for: unit))
                unitStr = unit.unitString
            } else if let categorySample = sample as? HKCategorySample {
                valueStr = String(categorySample.value)
                unitStr = nil
            } else {
                return nil
            }

            let deviceStr: String?
            if let d = sample.device {
                deviceStr = "\(d.manufacturer ?? "") \(d.model ?? "") \(d.name ?? "")".trimmingCharacters(in: .whitespaces)
            } else {
                deviceStr = nil
            }

            return HealthRecordPayload(
                type: sampleType.identifier,
                sourceName: sample.sourceRevision.source.name,
                startDate: formatDate(sample.startDate),
                endDate: formatDate(sample.endDate),
                value: valueStr,
                unit: unitStr,
                sourceVersion: sample.sourceRevision.version,
                device: deviceStr,
                creationDate: nil
            )
        }
    }

    func convertToWorkoutPayloads(_ samples: [HKSample]) -> [WorkoutPayload] {
        samples.compactMap { sample in
            guard let workout = sample as? HKWorkout else { return nil }

            let deviceStr: String?
            if let d = workout.device {
                deviceStr = "\(d.manufacturer ?? "") \(d.model ?? "") \(d.name ?? "")".trimmingCharacters(in: .whitespaces)
            } else {
                deviceStr = nil
            }

            let stats: [WorkoutStatisticPayload] = workout.allStatistics.compactMap { (qtype, stat) in
                guard let qtypeId = HKQuantityTypeIdentifier(rawValue: qtype.identifier),
                      let unit = preferredUnits[qtypeId] else { return nil }

                return WorkoutStatisticPayload(
                    type: qtype.identifier,
                    startDate: formatDate(stat.startDate),
                    endDate: formatDate(stat.endDate),
                    unit: unit.unitString,
                    average: stat.averageQuantity()?.doubleValue(for: unit),
                    minimum: stat.minimumQuantity()?.doubleValue(for: unit),
                    maximum: stat.maximumQuantity()?.doubleValue(for: unit),
                    sum: stat.sumQuantity()?.doubleValue(for: unit)
                )
            }

            return WorkoutPayload(
                workoutActivityType: workout.workoutActivityType.rawValue.description,
                sourceName: workout.sourceRevision.source.name,
                startDate: formatDate(workout.startDate),
                endDate: formatDate(workout.endDate),
                duration: workout.duration,
                durationUnit: "s",
                totalDistance: workout.totalDistance?.doubleValue(for: .meter()),
                totalDistanceUnit: workout.totalDistance != nil ? "m" : nil,
                totalEnergyBurned: workout.totalEnergyBurned?.doubleValue(for: .kilocalorie()),
                totalEnergyBurnedUnit: workout.totalEnergyBurned != nil ? "kcal" : nil,
                sourceVersion: workout.sourceRevision.version,
                device: deviceStr,
                creationDate: nil,
                statistics: stats
            )
        }
    }

    func convertToActivitySummaryPayloads(_ summaries: [HKActivitySummary]) -> [ActivitySummaryPayload] {
        summaries.map { s in
            let dc = s.dateComponents(for: Calendar.current)
            let dateString = String(format: "%04d-%02d-%02d", dc.year ?? 0, dc.month ?? 0, dc.day ?? 0)

            return ActivitySummaryPayload(
                dateComponents: dateString,
                activeEnergyBurned: s.activeEnergyBurned.doubleValue(for: .kilocalorie()),
                activeEnergyBurnedGoal: s.activeEnergyBurnedGoal.doubleValue(for: .kilocalorie()),
                activeEnergyBurnedUnit: "kcal",
                appleExerciseTime: s.appleExerciseTime.doubleValue(for: .minute()),
                appleExerciseTimeGoal: s.exerciseTimeGoal?.doubleValue(for: .minute()),
                appleStandHours: s.appleStandHours.doubleValue(for: .count()),
                appleStandHoursGoal: s.standHoursGoal?.doubleValue(for: .count())
            )
        }
    }
}
