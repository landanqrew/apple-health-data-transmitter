import Foundation

/// HTTP client for posting health data to the backend API.
final class APIClient {
    private let session: URLSession

    var serverURL: String {
        UserDefaults.standard.string(forKey: "serverURL") ?? ""
    }

    var apiKey: String {
        UserDefaults.standard.string(forKey: "apiKey") ?? ""
    }

    init(session: URLSession = .shared) {
        self.session = session
    }

    // MARK: - Public

    func postRecords(_ records: [HealthRecordPayload]) async throws -> Int {
        let body = ["items": records]
        return try await post(path: "/api/v1/records", body: body)
    }

    func postWorkouts(_ workouts: [WorkoutPayload]) async throws -> Int {
        let body = ["items": workouts]
        return try await post(path: "/api/v1/workouts", body: body)
    }

    func postActivitySummaries(_ summaries: [ActivitySummaryPayload]) async throws -> Int {
        let body = ["items": summaries]
        return try await post(path: "/api/v1/activity-summaries", body: body)
    }

    // MARK: - Private

    private func post<T: Encodable>(path: String, body: T) async throws -> Int {
        guard let base = URL(string: serverURL) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: base.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if !apiKey.isEmpty {
            request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }

        let encoder = JSONEncoder()
        request.httpBody = try encoder.encode(body)

        let (data, response) = try await session.data(for: request)

        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(http.statusCode) else {
            let detail = String(data: data, encoding: .utf8) ?? ""
            throw APIError.httpError(statusCode: http.statusCode, detail: detail)
        }

        let result = try JSONDecoder().decode(BatchResponse.self, from: data)
        return result.inserted
    }
}

private struct BatchResponse: Decodable {
    let inserted: Int
}

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(statusCode: Int, detail: String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Server URL is invalid. Check Settings."
        case .invalidResponse:
            return "Received an invalid response from the server."
        case .httpError(let code, let detail):
            return "HTTP \(code): \(detail)"
        }
    }
}
