# Error Handling Patterns

## Error Type Hierarchy

```swift
enum OptionsTrackerError: LocalizedError, Identifiable {
    case calculation(CalculationError)
    case dataAccess(DataAccessError)
    case network(NetworkError)
    case authentication(AuthenticationError)
    case general(GeneralError)
    case featureDeprecated(String)

    var id: String {
        "\(self)"
    }

    var severity: ErrorSeverity {
        switch self {
        case .authentication: return .critical
        case .network(let e) where e == .noConnection: return .high
        case .network: return .medium
        case .calculation: return .low
        case .dataAccess: return .medium
        case .general: return .low
        case .featureDeprecated: return .low
        }
    }

    var category: ErrorCategory {
        switch self {
        case .network: return .network
        case .authentication: return .authentication
        case .calculation, .dataAccess: return .data
        case .general, .featureDeprecated: return .general
        }
    }

    var errorDescription: String? {
        switch self {
        case .calculation(let error): return error.localizedDescription
        case .dataAccess(let error): return error.localizedDescription
        case .network(let error): return error.localizedDescription
        case .authentication(let error): return error.localizedDescription
        case .general(let error): return error.localizedDescription
        case .featureDeprecated(let feature): return "\(feature) is no longer available"
        }
    }

    var recoverySuggestion: String? {
        switch self {
        case .network(.noConnection):
            return "Check your internet connection and try again"
        case .authentication:
            return "Please log in again"
        case .network(.timeout):
            return "The request took too long. Please try again"
        default:
            return nil
        }
    }
}

enum ErrorSeverity {
    case critical  // Requires immediate attention (logout, crash prevention)
    case high      // Blocks user action
    case medium    // Degraded experience
    case low       // Informational
}

enum ErrorCategory {
    case network
    case authentication
    case data
    case general
}
```

## Specialized Error Types

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
        case .noConnection: return "No internet connection"
        case .timeout: return "Request timed out"
        case .unauthorized: return "Session expired"
        case .serverError(let code): return "Server error (\(code))"
        default: return "Network error"
        }
    }
}

enum AuthenticationError: LocalizedError {
    case notAuthenticated
    case tokenExpired
    case invalidCredentials
    case auth0Error(Error)

    var errorDescription: String? {
        switch self {
        case .notAuthenticated: return "Please log in"
        case .tokenExpired: return "Your session has expired"
        case .invalidCredentials: return "Invalid login credentials"
        case .auth0Error(let error): return error.localizedDescription
        }
    }
}

enum CalculationError: LocalizedError {
    case divisionByZero
    case invalidInput(String)
    case overflow

    var errorDescription: String? {
        switch self {
        case .divisionByZero: return "Cannot divide by zero"
        case .invalidInput(let field): return "Invalid value for \(field)"
        case .overflow: return "Calculation resulted in overflow"
        }
    }
}

enum DataAccessError: LocalizedError {
    case notFound(String)
    case corruptedData
    case saveFailed

    var errorDescription: String? {
        switch self {
        case .notFound(let item): return "\(item) not found"
        case .corruptedData: return "Data could not be read"
        case .saveFailed: return "Failed to save changes"
        }
    }
}

enum GeneralError: LocalizedError {
    case unknown(String)
    case unexpected(String)

    var errorDescription: String? {
        switch self {
        case .unknown(let message): return message
        case .unexpected(let message): return "Unexpected error: \(message)"
        }
    }
}
```

## ErrorHandler Observable

```swift
@MainActor
class ErrorHandler: ObservableObject {
    @Published var currentError: OptionsTrackerError?
    @Published var showingError: Bool = false

    func handle(_ error: Error) {
        let trackerError = wrap(error)
        currentError = trackerError
        showingError = true

        // Log error
        logError(trackerError)

        // Handle critical errors
        if trackerError.severity == .critical {
            handleCriticalError(trackerError)
        }
    }

    func wrap(_ error: Error) -> OptionsTrackerError {
        if let e = error as? OptionsTrackerError {
            return e
        }
        if let e = error as? NetworkError {
            return .network(e)
        }
        if let e = error as? AuthenticationError {
            return .authentication(e)
        }
        if let e = error as? CalculationError {
            return .calculation(e)
        }
        if let e = error as? DataAccessError {
            return .dataAccess(e)
        }
        return .general(.unknown(error.localizedDescription))
    }

    func dismiss() {
        currentError = nil
        showingError = false
    }

    private func logError(_ error: OptionsTrackerError) {
        print("[\(error.severity)] \(error.category): \(error.localizedDescription ?? "Unknown error")")
    }

    private func handleCriticalError(_ error: OptionsTrackerError) {
        // For auth errors, trigger logout
        if case .authentication = error {
            NotificationCenter.default.post(name: .forceLogout, object: nil)
        }
    }
}

extension Notification.Name {
    static let forceLogout = Notification.Name("forceLogout")
}
```

## View Integration

### Error Alert Modifier

```swift
struct ErrorAlertModifier: ViewModifier {
    @ObservedObject var errorHandler: ErrorHandler

    func body(content: Content) -> some View {
        content
            .alert(
                "Error",
                isPresented: $errorHandler.showingError,
                presenting: errorHandler.currentError
            ) { error in
                Button("OK") {
                    errorHandler.dismiss()
                }
                if error.recoverySuggestion != nil {
                    Button("Retry") {
                        // Handle retry
                        errorHandler.dismiss()
                    }
                }
            } message: { error in
                VStack {
                    Text(error.localizedDescription ?? "An error occurred")
                    if let suggestion = error.recoverySuggestion {
                        Text(suggestion)
                            .font(.caption)
                    }
                }
            }
    }
}

extension View {
    func errorHandling(_ handler: ErrorHandler) -> some View {
        modifier(ErrorAlertModifier(errorHandler: handler))
    }
}
```

### Usage

```swift
struct ContentView: View {
    @EnvironmentObject var errorHandler: ErrorHandler

    var body: some View {
        NavigationView {
            MainContent()
        }
        .errorHandling(errorHandler)
    }
}
```

### Inline Error Display

```swift
struct ErrorBanner: View {
    let error: OptionsTrackerError
    let dismissAction: () -> Void

    var body: some View {
        HStack {
            Image(systemName: iconName)
                .foregroundColor(iconColor)

            VStack(alignment: .leading, spacing: 2) {
                Text(error.localizedDescription ?? "Error")
                    .font(.subheadline)
                    .fontWeight(.medium)

                if let suggestion = error.recoverySuggestion {
                    Text(suggestion)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            Button(action: dismissAction) {
                Image(systemName: "xmark")
                    .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(backgroundColor)
        .cornerRadius(8)
    }

    private var iconName: String {
        switch error.severity {
        case .critical: return "exclamationmark.triangle.fill"
        case .high: return "exclamationmark.circle.fill"
        case .medium: return "info.circle.fill"
        case .low: return "info.circle"
        }
    }

    private var iconColor: Color {
        switch error.severity {
        case .critical: return .red
        case .high: return .orange
        case .medium: return .yellow
        case .low: return .blue
        }
    }

    private var backgroundColor: Color {
        switch error.severity {
        case .critical: return .red.opacity(0.1)
        case .high: return .orange.opacity(0.1)
        case .medium: return .yellow.opacity(0.1)
        case .low: return .blue.opacity(0.1)
        }
    }
}
```

## Error Handling in Providers

```swift
@MainActor
class DataProvider: ObservableObject {
    @Published private(set) var loadingState: LoadingState = .idle
    private let errorHandler: ErrorHandler

    func loadData() async {
        loadingState = .loading("Loading...")

        do {
            let data = try await apiService.getData()
            self.data = data
            loadingState = .idle
        } catch {
            errorHandler.handle(error)
            loadingState = .error(error)
        }
    }
}
```

## Result Type Pattern

For operations that can fail:

```swift
extension APIService {
    func getPositionsSafe() async -> Result<[Position], OptionsTrackerError> {
        do {
            let positions = try await getPositions()
            return .success(positions)
        } catch {
            let trackerError: OptionsTrackerError
            if let e = error as? NetworkError {
                trackerError = .network(e)
            } else {
                trackerError = .general(.unknown(error.localizedDescription))
            }
            return .failure(trackerError)
        }
    }
}

// Usage
let result = await apiService.getPositionsSafe()
switch result {
case .success(let positions):
    self.positions = positions
case .failure(let error):
    errorHandler.handle(error)
}
```
