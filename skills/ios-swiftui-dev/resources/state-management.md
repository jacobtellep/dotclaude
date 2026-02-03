# State Management Patterns

## Provider Architecture

### Why Providers?

- **Granular updates**: Changes to one provider don't trigger re-renders in unrelated views
- **Clear ownership**: Each provider owns its domain
- **Testability**: Providers can be tested with mock services
- **Scalability**: Easy to add new providers for new features

### Provider Template

```swift
import Foundation
import Combine

@MainActor
class FeatureProvider: ObservableObject {
    // MARK: - Published State

    @Published private(set) var items: [Item] = []
    @Published private(set) var selectedItem: Item?
    @Published var loadingState: LoadingState = .idle
    @Published var error: OptionsTrackerError?

    // MARK: - Dependencies

    private let apiService: APIServiceProtocol
    private let errorHandler: ErrorHandler
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Init

    init(
        apiService: APIServiceProtocol? = nil,
        errorHandler: ErrorHandler = ErrorHandler()
    ) {
        self.apiService = apiService ?? APIServiceFactory.createService()
        self.errorHandler = errorHandler
    }

    // MARK: - Public Methods

    func loadItems(forceRefresh: Bool = false) async {
        guard case .idle = loadingState else { return }

        loadingState = .loading("Loading items...")
        defer { loadingState = .idle }

        do {
            items = try await apiService.getItems()
        } catch {
            self.error = errorHandler.wrap(error)
            loadingState = .error(error)
        }
    }

    func selectItem(_ item: Item) {
        selectedItem = item
    }

    func clearSelection() {
        selectedItem = nil
    }

    // MARK: - Computed Properties

    var hasItems: Bool {
        !items.isEmpty
    }

    var itemCount: Int {
        items.count
    }
}
```

## Coordinator Pattern

For coordinating multiple providers:

```swift
@MainActor
class PositionStore: ObservableObject {
    // Child providers
    @Published var personalProvider: PersonalPositionsProvider
    @Published var curatedProvider: CuratedPicksProvider

    // Shared state
    @Published private(set) var isLoading = false
    @Published private(set) var lastSyncDate: Date?

    private var cancellables = Set<AnyCancellable>()

    init() {
        self.personalProvider = PersonalPositionsProvider()
        self.curatedProvider = CuratedPicksProvider()

        setupBindings()
    }

    private func setupBindings() {
        // Combine loading states
        Publishers.CombineLatest(
            personalProvider.$loadingState,
            curatedProvider.$loadingState
        )
        .map { personal, curated in
            if case .loading = personal { return true }
            if case .loading = curated { return true }
            return false
        }
        .assign(to: &$isLoading)
    }

    func refreshAll() async {
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.personalProvider.loadPositions(forceRefresh: true) }
            group.addTask { await self.curatedProvider.loadPicks(forceRefresh: true) }
        }
        lastSyncDate = Date()
    }
}
```

## @State vs @Published

### Use @State for:
- Local UI state (selections, toggles, text input)
- State that doesn't need to be shared

```swift
struct PositionFilterView: View {
    @State private var selectedStatus: PositionStatus?
    @State private var searchText = ""
    @State private var showFilters = false
}
```

### Use @Published for:
- State that needs to be observed by views
- Data from network/database
- State shared across multiple views

```swift
class Provider: ObservableObject {
    @Published private(set) var data: [Item] = []
    @Published var loadingState: LoadingState = .idle
}
```

## LoadingState Pattern

```swift
enum LoadingState: Equatable {
    case idle
    case loading(String)
    case error(Error)

    var isLoading: Bool {
        if case .loading = self { return true }
        return false
    }

    var errorMessage: String? {
        if case .error(let error) = self {
            return error.localizedDescription
        }
        return nil
    }

    // Equatable conformance for Error
    static func == (lhs: LoadingState, rhs: LoadingState) -> Bool {
        switch (lhs, rhs) {
        case (.idle, .idle): return true
        case (.loading(let a), .loading(let b)): return a == b
        case (.error, .error): return true  // Errors always compare as equal for state purposes
        default: return false
        }
    }
}
```

### Usage in Views

```swift
var body: some View {
    Group {
        switch provider.loadingState {
        case .idle:
            ContentView(items: provider.items)

        case .loading(let message):
            VStack {
                ProgressView()
                Text(message)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

        case .error(let error):
            ErrorView(
                error: error,
                retryAction: {
                    Task { await provider.reload() }
                }
            )
        }
    }
}
```

## Environment Injection

### Setup in App

```swift
@main
struct MyApp: App {
    @StateObject private var positionsProvider = PersonalPositionsProvider()
    @StateObject private var authStore = AuthenticationStore()
    @StateObject private var errorHandler = ErrorHandler()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(positionsProvider)
                .environmentObject(authStore)
                .environmentObject(errorHandler)
        }
    }
}
```

### Access in Views

```swift
struct PositionListView: View {
    @EnvironmentObject var provider: PersonalPositionsProvider
    @EnvironmentObject var errorHandler: ErrorHandler

    var body: some View {
        // Use provider.positions, etc.
    }
}
```

## Combine for Complex State

### Debounced Search

```swift
class SearchProvider: ObservableObject {
    @Published var searchText = ""
    @Published private(set) var results: [Result] = []

    private var cancellables = Set<AnyCancellable>()

    init() {
        $searchText
            .debounce(for: .milliseconds(300), scheduler: RunLoop.main)
            .removeDuplicates()
            .sink { [weak self] text in
                Task { await self?.search(text) }
            }
            .store(in: &cancellables)
    }

    private func search(_ text: String) async {
        guard !text.isEmpty else {
            results = []
            return
        }
        // Perform search...
    }
}
```

### Derived State

```swift
class AnalyticsProvider: ObservableObject {
    @Published private(set) var positions: [Position] = []

    // Computed from positions
    var totalPremium: Currency {
        positions.reduce(Currency(cents: 0)) { $0 + $1.premium }
    }

    var winRate: Double {
        let closed = positions.filter { $0.status == .closed }
        guard !closed.isEmpty else { return 0 }
        let winners = closed.filter { $0.outcome == .profit }
        return Double(winners.count) / Double(closed.count) * 100
    }

    var openPositions: [Position] {
        positions.filter { $0.status == .open }
    }
}
```

## Testing Providers

```swift
@MainActor
class ProviderTests: XCTestCase {
    var mockService: MockAPIService!
    var provider: PersonalPositionsProvider!

    override func setUp() {
        super.setUp()
        mockService = MockAPIService()
        provider = PersonalPositionsProvider(apiService: mockService)
    }

    func testLoadPositions_Success() async {
        // Arrange
        mockService.mockPositions = [.mock(), .mock()]

        // Act
        await provider.loadPositions()

        // Assert
        XCTAssertEqual(provider.positions.count, 2)
        XCTAssertEqual(provider.loadingState, .idle)
    }

    func testLoadPositions_Error() async {
        // Arrange
        mockService.shouldFail = true

        // Act
        await provider.loadPositions()

        // Assert
        XCTAssertTrue(provider.positions.isEmpty)
        if case .error = provider.loadingState {
            // Expected
        } else {
            XCTFail("Expected error state")
        }
    }
}
```
