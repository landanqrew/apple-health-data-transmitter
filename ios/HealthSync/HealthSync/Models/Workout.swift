import Foundation

/// Matches the backend `WorkoutStatisticPayload` schema.
struct WorkoutStatisticPayload: Codable {
    let type: String
    let startDate: String
    let endDate: String
    let unit: String?
    let average: Double?
    let minimum: Double?
    let maximum: Double?
    let sum: Double?

    enum CodingKeys: String, CodingKey {
        case type
        case startDate = "start_date"
        case endDate = "end_date"
        case unit, average, minimum, maximum, sum
    }
}

/// Matches the backend `WorkoutPayload` schema.
struct WorkoutPayload: Codable {
    let workoutActivityType: String
    let sourceName: String
    let startDate: String
    let endDate: String
    let duration: Double?
    let durationUnit: String?
    let totalDistance: Double?
    let totalDistanceUnit: String?
    let totalEnergyBurned: Double?
    let totalEnergyBurnedUnit: String?
    let sourceVersion: String?
    let device: String?
    let creationDate: String?
    let statistics: [WorkoutStatisticPayload]

    enum CodingKeys: String, CodingKey {
        case workoutActivityType = "workout_activity_type"
        case sourceName = "source_name"
        case startDate = "start_date"
        case endDate = "end_date"
        case duration
        case durationUnit = "duration_unit"
        case totalDistance = "total_distance"
        case totalDistanceUnit = "total_distance_unit"
        case totalEnergyBurned = "total_energy_burned"
        case totalEnergyBurnedUnit = "total_energy_burned_unit"
        case sourceVersion = "source_version"
        case device
        case creationDate = "creation_date"
        case statistics
    }
}
