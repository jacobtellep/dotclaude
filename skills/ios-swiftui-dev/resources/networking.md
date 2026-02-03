# Networking Patterns

## APIClient Architecture

### Base Client

```swift
import Foundation

final class APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let baseURL: URL
    private let decoder: JSONDecoder

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
        self.baseURL = URL(string: AppConfiguration.apiBaseURL)!

        self.decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        decoder.keyDecodingStrategy = .convertFromSnakeCase
    }

    func request<T: Decodable>(
        _ endpoint: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil,
        queryItems: [URLQueryItem]? = nil
    ) async throws -> T {
        var url = baseURL.appendingPathComponent(endpoint)

        if let queryItems = queryItems {
            var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
            components.queryItems = queryItems
            url = components.url!
        }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token
        if let token = try? await getAuthToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            return try decoder.decode(T.self, from: data)
        case 401:
            throw NetworkError.unauthorized
        case 403:
            throw NetworkError.forbidden
        case 404:
            throw NetworkError.notFound
        case 500...599:
            throw NetworkError.serverError(httpResponse.statusCode)
        default:
            throw NetworkError.httpError(httpResponse.statusCode)
        }
    }

    private func getAuthToken() async throws -> String? {
        guard let credentials = try? await Auth0Manager.shared.credentialsManager.credentials() else {
            return nil
        }
        return credentials.accessToken
    }
}

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case patch = "PATCH"
    case delete = "DELETE"
}
```

## Caching

### LRU Cache with TTL

```swift
actor APICache {
    private var cache: [String: CacheEntry] = [:]
    private let maxEntries = 100

    struct CacheEntry {
        let data: Any
        let expiresAt: Date
    }

    func get<T>(_ key: String) -> T? {
        guard let entry = cache[key],
              entry.expiresAt > Date() else {
            cache.removeValue(forKey: key)
            return nil
        }
        return entry.data as? T
    }

    func set<T>(_ key: String, value: T, ttl: TimeInterval = 300) {
        // Evict oldest if at capacity
        if cache.count >= maxEntries {
            evictOldest()
        }

        cache[key] = CacheEntry(
            data: value,
            expiresAt: Date().addingTimeInterval(ttl)
        )
    }

    func clear() {
        cache.removeAll()
    }

    private func evictOldest() {
        guard let oldest = cache.min(by: { $0.value.expiresAt < $1.value.expiresAt }) else {
            return
        }
        cache.removeValue(forKey: oldest.key)
    }
}
```

### Cache TTL Constants

```swift
struct CacheTTL {
    static let positions: TimeInterval = 300      // 5 minutes
    static let events: TimeInterval = 1800        // 30 minutes
    static let analytics: TimeInterval = 900      // 15 minutes
    static let userProfile: TimeInterval = 600    // 10 minutes
}
```

## Request Deduplication

Prevent duplicate concurrent requests:

```swift
actor APIRequestDeduplicator {
    private var inFlightRequests: [String: Task<Any, Error>] = [:]

    func deduplicate<T>(
        key: String,
        request: @escaping () async throws -> T
    ) async throws -> T {
        // Check for existing request
        if let existingTask = inFlightRequests[key] {
            return try await existingTask.value as! T
        }

        // Create new request
        let task = Task<Any, Error> {
            try await request()
        }

        inFlightRequests[key] = task

        do {
            let result = try await task.value
            inFlightRequests.removeValue(forKey: key)
            return result as! T
        } catch {
            inFlightRequests.removeValue(forKey: key)
            throw error
        }
    }
}
```

## Retry Handler

```swift
actor RetryHandler {
    enum Policy {
        case `default`    // 3 attempts, exponential backoff
        case aggressive   // 5 attempts
        case conservative // 2 attempts

        var maxAttempts: Int {
            switch self {
            case .default: return 3
            case .aggressive: return 5
            case .conservative: return 2
            }
        }

        var baseDelay: TimeInterval {
            switch self {
            case .default: return 1.0
            case .aggressive: return 0.5
            case .conservative: return 2.0
            }
        }
    }

    func execute<T>(
        policy: Policy = .default,
        operation: @escaping () async throws -> T
    ) async throws -> T {
        var lastError: Error?

        for attempt in 1...policy.maxAttempts {
            do {
                return try await operation()
            } catch {
                lastError = error

                // Don't retry non-transient errors
                guard isRetryable(error) else { throw error }

                // Don't delay on last attempt
                if attempt < policy.maxAttempts {
                    let delay = policy.baseDelay * pow(2, Double(attempt - 1))
                    try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                }
            }
        }

        throw lastError!
    }

    private func isRetryable(_ error: Error) -> Bool {
        if let networkError = error as? NetworkError {
            switch networkError {
            case .timeout, .noConnection, .serverError:
                return true
            case .unauthorized, .forbidden, .notFound:
                return false
            default:
                return false
            }
        }
        return false
    }
}
```

## APIService Implementation

```swift
protocol APIServiceProtocol {
    func getPositions() async throws -> [Position]
    func getUserProfile() async throws -> User
    func getAccountsSummary() async throws -> AccountsSummaryResponse
}

final class APIService: APIServiceProtocol {
    private let client: APIClient
    private let cache = APICache()
    private let deduplicator = APIRequestDeduplicator()
    private let retryHandler = RetryHandler()

    init(client: APIClient = .shared) {
        self.client = client
    }

    func getPositions() async throws -> [Position] {
        // Check cache
        if let cached: [Position] = await cache.get("positions") {
            return cached
        }

        // Deduplicate concurrent requests
        let positions: [Position] = try await deduplicator.deduplicate(key: "positions") {
            try await self.retryHandler.execute {
                try await self.client.request("/api/positions")
            }
        }

        // Cache result
        await cache.set("positions", value: positions, ttl: CacheTTL.positions)
        return positions
    }

    func getUserProfile() async throws -> User {
        if let cached: User = await cache.get("profile") {
            return cached
        }

        let user: User = try await client.request("/api/user/profile")
        await cache.set("profile", value: user, ttl: CacheTTL.userProfile)
        return user
    }

    func getAccountsSummary() async throws -> AccountsSummaryResponse {
        try await client.request("/api/analytics/summary")
    }
}
```

## Connectivity Monitoring

```swift
import Network

class ConnectivityMonitor: ObservableObject {
    static let shared = ConnectivityMonitor()

    @Published private(set) var isConnected = true
    @Published private(set) var connectionType: ConnectionType = .unknown

    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "connectivity")

    enum ConnectionType {
        case wifi, cellular, ethernet, unknown
    }

    private init() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isConnected = path.status == .satisfied
                self?.connectionType = self?.getConnectionType(path) ?? .unknown
            }
        }
        monitor.start(queue: queue)
    }

    private func getConnectionType(_ path: NWPath) -> ConnectionType {
        if path.usesInterfaceType(.wifi) { return .wifi }
        if path.usesInterfaceType(.cellular) { return .cellular }
        if path.usesInterfaceType(.wiredEthernet) { return .ethernet }
        return .unknown
    }
}
```

## Network Errors

```swift
enum NetworkError: LocalizedError {
    case invalidResponse
    case unauthorized
    case forbidden
    case notFound
    case serverError(Int)
    case httpError(Int)
    case timeout
    case noConnection
    case decodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid server response"
        case .unauthorized:
            return "Please log in again"
        case .forbidden:
            return "You don't have access to this resource"
        case .notFound:
            return "Resource not found"
        case .serverError(let code):
            return "Server error (\(code))"
        case .httpError(let code):
            return "Request failed (\(code))"
        case .timeout:
            return "Request timed out"
        case .noConnection:
            return "No internet connection"
        case .decodingError:
            return "Failed to process server response"
        }
    }
}
```
