import Foundation

/// Matches the backend `HealthRecordPayload` schema.
struct HealthRecordPayload: Codable {
    let type: String
    let sourceName: String
    let startDate: String
    let endDate: String
    let value: String?
    let unit: String?
    let sourceVersion: String?
    let device: String?
    let creationDate: String?

    enum CodingKeys: String, CodingKey {
        case type
        case sourceName = "source_name"
        case startDate = "start_date"
        case endDate = "end_date"
        case value, unit
        case sourceVersion = "source_version"
        case device
        case creationDate = "creation_date"
    }
}
