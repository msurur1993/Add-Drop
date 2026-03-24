import SwiftUI

@main
struct StitchApp: App {
    @StateObject private var viewModel = PortfolioViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var viewModel: PortfolioViewModel
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView()
                .tabItem {
                    Image(systemName: selectedTab == 0 ? "square.grid.2x2.fill" : "square.grid.2x2")
                    Text("Summary")
                }
                .tag(0)

            MarketsView()
                .tabItem {
                    Image(systemName: "chart.line.uptrend.xyaxis")
                    Text("Markets")
                }
                .tag(1)

            PortfolioView()
                .tabItem {
                    Image(systemName: selectedTab == 2 ? "chart.pie.fill" : "chart.pie")
                    Text("Portfolio")
                }
                .tag(2)

            SettingsView()
                .tabItem {
                    Image(systemName: "gearshape")
                    Text("Settings")
                }
                .tag(3)
        }
        .tint(AppTheme.primary)
    }
}

// MARK: - Placeholder Views

struct MarketsView: View {
    @EnvironmentObject var viewModel: PortfolioViewModel

    var body: some View {
        NavigationStack {
            List {
                ForEach(Stock.all) { stock in
                    NavigationLink(value: stock) {
                        WatchlistRowView(stock: stock)
                    }
                    .listRowInsets(EdgeInsets())
                }
            }
            .listStyle(.plain)
            .navigationTitle("Markets")
            .navigationDestination(for: Stock.self) { stock in
                StockDetailView(stock: stock)
                    .environmentObject(viewModel)
            }
        }
    }
}

struct SettingsView: View {
    var body: some View {
        NavigationStack {
            List {
                Section("Account") {
                    HStack {
                        Image(systemName: "person.circle.fill")
                            .font(.system(size: 40))
                            .foregroundColor(AppTheme.primary)
                        VStack(alignment: .leading) {
                            Text("Paper Trader")
                                .font(.headline)
                            Text("Virtual Account")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding(.vertical, 4)
                }

                Section("Preferences") {
                    Label("Notifications", systemImage: "bell")
                    Label("Appearance", systemImage: "paintbrush")
                    Label("Currency", systemImage: "dollarsign.circle")
                }

                Section("About") {
                    Label("Help & Support", systemImage: "questionmark.circle")
                    Label("Terms of Service", systemImage: "doc.text")
                    Label("Privacy Policy", systemImage: "lock.shield")
                }

                Section {
                    HStack {
                        Spacer()
                        Text("The Precision Ledger v1.0")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Spacer()
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}
