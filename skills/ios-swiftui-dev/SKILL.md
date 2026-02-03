---
name: ios-swiftui-dev
description: iOS/SwiftUI development patterns for modern Swift applications. Use when creating views, managing state with @Published/@ObservableObject, implementing MVVM with providers, working with Auth0 authentication, building API clients with async/await, handling financial calculations with Currency types, or structuring iOS projects. Covers provider-based architecture, Combine, error handling, and testing strategies.
---

# iOS/SwiftUI Development Guidelines

## Purpose

Establish consistency and best practices for iOS applications using SwiftUI, provider-based MVVM architecture, Auth0 authentication, and type-safe patterns for financial applications.

## When to Use This Skill

Automatically activates when working on:
- Creating SwiftUI views and components
- Managing state with @Published, @ObservableObject
- Building providers and view models
- Implementing Auth0 authentication
- API client and networking
- Financial calculations requiring precision
- iOS testing

---

## Quick Start

### New Feature Checklist

- [ ] **View**: SwiftUI view in `Views/[Feature]/`
- [ ] **Provider** (if state needed): ObservableObject in `ViewModels/`
- [ ] **Models**: Codable structs in `Models/`
- [ ] **Service** (if API needed): APIServiceProtocol method
- [ ] **Error Handling**: Use OptionsTrackerError types
- [ ] **@MainActor**: On all ObservableObject classes

---

## Architecture Overview

### Provider-Based MVVM

```
┌─────────────────────────────────────────────────────────────┐
│                        SwiftUI View                          │
│              @EnvironmentObject providers                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         Providers                            │
│  PersonalPositionsProvider │ CuratedPicksProvider │ ...     │
│         @MainActor @ObservableObject                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│           APIService │ Auth0Manager │ Cache                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Client                              │
│        URLSession │ JSON Decoding │ Auth Headers             │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
OptionsTracker/
├── Core/Services/          # Networking, auth, sync services
│   ├── APIClient.swift
│   ├── APIService.swift
│   └── Auth0Manager.swift
├── Models/                 # Data models (Codable)
│   ├── Position.swift
│   ├── User.swift
│   └── Currency.swift
├── ViewModels/             # Providers and stores
│   ├── PersonalPositionsProvider.swift
│   ├── CuratedPicksProvider.swift
│   └── PositionStore.swift
├── Views/                  # SwiftUI views by feature
│   ├── Authentication/
│   ├── Analytics/
│   ├── Components/
│   └── Positions/
├── Utils/                  # Utilities, extensions, error handling
│   ├── ErrorHandler.swift
│   └── Extensions/
└── Tests/                  # XCTest suite
```

---

## State Management

### Provider Pattern

```swift
@MainActor
class PersonalPositionsProvider: ObservableObject {
    // Published state
    @Published private(set) var positions: [Position] = []
    @Published private(set) var accountsSummary: AccountsSummaryResponse?
    @Published var loadingState: LoadingState = .idle

    // Dependencies (injected for testability)
    private let apiService: APIServiceProtocol
    private let errorHandler: ErrorHandler

    init(
        apiService: APIServiceProtocol? = nil,
        errorHandler: ErrorHandler = ErrorHandler()
    ) {
        self.apiService = apiService ?? APIServiceFactory.createService()
        self.errorHandler = errorHandler
    }

    func loadPositions(forceRefresh: Bool = false) async {
        // Prevent duplicate loads
        if case .loading = loadingState, !forceRefresh { return }

        loadingState = .loading("Loading positions...")
        defer { loadingState = .idle }

        do {
            // Concurrent fetch with async let
            async let positionsTask = apiService.getPositions()
            async let summaryTask = apiService.getAccountsSummary()

            let (fetchedPositions, fetchedSummary) = try await (positionsTask, summaryTask)
            positions = fetchedPositions
            accountsSummary = fetchedSummary
        } catch {
            errorHandler.handle(error)
            loadingState = .error(error)
        }
    }
}
```

### LoadingState Enum

```swift
enum LoadingState: Equatable {
    case idle
    case loading(String)  // Message to display
    case error(Error)

    static func == (lhs: LoadingState, rhs: LoadingState) -> Bool {
        switch (lhs, rhs) {
        case (.idle, .idle): return true
        case (.loading(let a), .loading(let b)): return a == b
        case (.error, .error): return true
        default: return false
        }
    }
}
```

### Environment Injection

```swift
// In App.swift or SceneDelegate
@main
struct OptionsTrackerApp: App {
    @StateObject private var positionsProvider = PersonalPositionsProvider()
    @StateObject private var authStore = AuthenticationStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(positionsProvider)
                .environmentObject(authStore)
        }
    }
}

// In views
struct PositionListView: View {
    @EnvironmentObject var provider: PersonalPositionsProvider

    var body: some View {
        List(provider.positions) { position in
            PositionRow(position: position)
        }
    }
}
```

See [state-management.md](resources/state-management.md) for more patterns.

---

## Financial Precision

### Currency Type

**Never use Double for money.** Use the Currency struct:

```swift
struct Currency: Codable, Hashable, Comparable {
    private let cents: Int

    init(dollars: Double) {
        self.cents = Int((dollars * 100).rounded())
    }

    init(cents: Int) {
        self.cents = cents
    }

    var amount: Decimal {
        Decimal(cents) / 100
    }

    var formatted: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        return formatter.string(from: NSDecimalNumber(decimal: amount)) ?? "$0.00"
    }

    // Arithmetic
    static func + (lhs: Currency, rhs: Currency) -> Currency {
        Currency(cents: lhs.cents + rhs.cents)
    }

    static func - (lhs: Currency, rhs: Currency) -> Currency {
        Currency(cents: lhs.cents - rhs.cents)
    }

    static func * (lhs: Currency, rhs: Double) -> Currency {
        Currency(cents: Int((Double(lhs.cents) * rhs).rounded()))
    }

    static func < (lhs: Currency, rhs: Currency) -> Bool {
        lhs.cents < rhs.cents
    }
}
```

### Usage

```swift
let premium = Currency(dollars: 125.50)
let cost = Currency(dollars: 5000.00)
let profit = premium - Currency(dollars: 10.00)

print(premium.formatted)  // "$125.50"
```

---

## Networking

### APIClient Singleton

```swift
final class APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let baseURL: URL
    private let credentialsManager: CredentialsManager

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
        self.baseURL = URL(string: AppConfiguration.apiBaseURL)!
        self.credentialsManager = Auth0Manager.shared.credentialsManager
    }

    func request<T: Decodable>(
        _ endpoint: String,
        method: String = "GET",
        body: Data? = nil
    ) async throws -> T {
        var request = URLRequest(url: baseURL.appendingPathComponent(endpoint))
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token
        if let credentials = try? await credentialsManager.credentials() {
            request.setValue("Bearer \(credentials.accessToken)", forHTTPHeaderField: "Authorization")
        }

        request.httpBody = body

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NetworkError.invalidResponse
        }

        guard 200...299 ~= httpResponse.statusCode else {
            throw NetworkError.httpError(httpResponse.statusCode)
        }

        return try JSONDecoder().decode(T.self, from: data)
    }
}
```

### APIService Protocol

```swift
protocol APIServiceProtocol {
    func getPositions() async throws -> [Position]
    func getUserProfile() async throws -> User
    func getAccountsSummary() async throws -> AccountsSummaryResponse
}

final class APIService: APIServiceProtocol {
    private let client: APIClient
    private let cache = APICache()

    init(client: APIClient = .shared) {
        self.client = client
    }

    func getPositions() async throws -> [Position] {
        // Check cache first
        if let cached: [Position] = cache.get("positions") {
            return cached
        }

        let positions: [Position] = try await client.request("/api/positions")
        cache.set("positions", value: positions, ttl: 300)  // 5 min
        return positions
    }
}
```

See [networking.md](resources/networking.md) for retry, caching, and deduplication patterns.

---

## Authentication

### Auth0Manager

```swift
final class Auth0Manager {
    static let shared = Auth0Manager()

    let credentialsManager: CredentialsManager

    private init() {
        self.credentialsManager = CredentialsManager(authentication: Auth0.authentication())
    }

    func login() async -> Result<Credentials, AuthenticationError> {
        await withCheckedContinuation { continuation in
            Auth0
                .webAuth()
                .audience(AppConfiguration.auth0Audience)
                .scope("openid profile email offline_access")
                .start { result in
                    switch result {
                    case .success(let credentials):
                        _ = self.credentialsManager.store(credentials: credentials)
                        continuation.resume(returning: .success(credentials))
                    case .failure(let error):
                        continuation.resume(returning: .failure(.auth0Error(error)))
                    }
                }
        }
    }

    func logout() async {
        await withCheckedContinuation { continuation in
            Auth0.webAuth().clearSession { _ in
                _ = self.credentialsManager.clear()
                continuation.resume()
            }
        }
    }

    var isAuthenticated: Bool {
        credentialsManager.hasValid()
    }
}
```

---

## Error Handling

### Error Types

```swift
enum OptionsTrackerError: LocalizedError, Identifiable {
    case network(NetworkError)
    case authentication(AuthenticationError)
    case calculation(CalculationError)
    case dataAccess(DataAccessError)
    case general(GeneralError)

    var id: String { localizedDescription }

    var severity: ErrorSeverity {
        switch self {
        case .authentication: return .high
        case .network: return .medium
        default: return .low
        }
    }

    var errorDescription: String? {
        switch self {
        case .network(let error): return error.localizedDescription
        case .authentication(let error): return error.localizedDescription
        // ... etc
        }
    }
}
```

### ErrorHandler

```swift
@MainActor
class ErrorHandler: ObservableObject {
    @Published var currentError: OptionsTrackerError?
    @Published var showingError: Bool = false

    func handle(_ error: Error) {
        let trackerError: OptionsTrackerError
        if let e = error as? OptionsTrackerError {
            trackerError = e
        } else if let e = error as? NetworkError {
            trackerError = .network(e)
        } else {
            trackerError = .general(.unknown(error.localizedDescription))
        }

        currentError = trackerError
        showingError = true

        // Log for debugging
        print("Error: \(trackerError.localizedDescription)")
    }
}
```

See [error-handling.md](resources/error-handling.md) for view integration.

---

## SwiftUI View Patterns

### View with Provider

```swift
struct PositionListView: View {
    @EnvironmentObject var provider: PersonalPositionsProvider
    @State private var selectedStatus: PositionStatus?

    var filteredPositions: [Position] {
        provider.positions.filter { position in
            selectedStatus == nil || position.status == selectedStatus
        }
    }

    var body: some View {
        Group {
            switch provider.loadingState {
            case .loading(let message):
                ProgressView(message)

            case .error(let error):
                ErrorView(error: error, retry: {
                    Task { await provider.loadPositions(forceRefresh: true) }
                })

            case .idle:
                List(filteredPositions) { position in
                    PositionRow(position: position)
                }
            }
        }
        .task {
            await provider.loadPositions()
        }
        .refreshable {
            await provider.loadPositions(forceRefresh: true)
        }
    }
}
```

### Reusable Components

```swift
struct MetricCard: View {
    let title: String
    let value: String
    var trend: Double? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
            Text(value)
                .font(.title2)
                .fontWeight(.semibold)
            if let trend = trend {
                HStack(spacing: 2) {
                    Image(systemName: trend >= 0 ? "arrow.up" : "arrow.down")
                    Text("\(abs(trend), specifier: "%.1f")%")
                }
                .font(.caption)
                .foregroundColor(trend >= 0 ? .green : .red)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
    }
}
```

---

## Testing

```swift
@MainActor
class PositionProviderTests: XCTestCase {
    func testLoadPositions() async {
        // Arrange
        let mockService = MockAPIService()
        mockService.mockPositions = [Position.mock()]
        let provider = PersonalPositionsProvider(apiService: mockService)

        // Act
        await provider.loadPositions()

        // Assert
        XCTAssertEqual(provider.positions.count, 1)
        XCTAssertEqual(provider.loadingState, .idle)
    }
}

class MockAPIService: APIServiceProtocol {
    var mockPositions: [Position] = []

    func getPositions() async throws -> [Position] {
        return mockPositions
    }
}
```

---

## Anti-Patterns to Avoid

❌ Using Double for money (use Currency)
❌ Missing @MainActor on ObservableObject
❌ Force unwrapping optionals
❌ Blocking main thread with synchronous network calls
❌ Hardcoded API URLs (use AppConfiguration)
❌ Missing error handling in async functions

---

## Navigation Guide

| Need to... | Read this |
|------------|-----------|
| Manage state | [state-management.md](resources/state-management.md) |
| Build networking | [networking.md](resources/networking.md) |
| Handle errors | [error-handling.md](resources/error-handling.md) |

---

**For complete project details, see the project's `CLAUDE.md` file.**
