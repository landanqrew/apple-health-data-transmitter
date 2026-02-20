import Foundation

/// Matches the backend `ActivitySummaryPayload` schema.
struct ActivitySummaryPayload: Codable {
    let dateComponents: String
    let activeEnergyBurned: Double?
    let activeEnergyBurnedGoal: Double?
    let activeEnergyBurnedUnit: String?
    let appleExerciseTime: Double?
    let appleExerciseTimeGoal: Double?
    let appleStandHours: Double?
    let appleStandHoursGoal: Double?

    enum CodingKeys: String, CodingKey {
        case dateComponents = "date_components"
        case activeEnergyBurned = "active_energy_burned"
        case activeEnergyBurnedGoal = "active_energy_burned_goal"
        case activeEnergyBurnedUnit = "active_energy_burned_unit"
        case appleExerciseTime = "apple_exercise_time"
        case appleExerciseTimeGoal = "apple_exercise_time_goal"
        case appleStandHours = "apple_stand_hours"
        case appleStandHoursGoal = "apple_stand_hours_goal"
    }
}
