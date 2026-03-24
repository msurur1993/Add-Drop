import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var viewModel: PortfolioViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 28) {
                    heroSection
                    performanceChart
                    bentoGrid
                    watchlistSection
                    marketIntelligence
                }
                .padding(.horizontal, 16)
                .padding(.top, 8)
                .padding(.bottom, 100)
            }
            .background(Color.white)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    HStack(spacing: 8) {
                        Circle()
                            .fill(AppTheme.surfaceGray)
                            .frame(width: 32, height: 32)
                            .overlay(
                                Image(systemName: "person.fill")
                                    .font(.system(size: 14))
                                    .foregroundColor(AppTheme.labelSecondary)
                            )
                        Text("The Precision Ledger")
                            .font(.system(size: 18, weight: .bold))
                            .tracking(-0.3)
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        // notifications
                    } label: {
                        Image(systemName: "bell.fill")
                            .foregroundColor(AppTheme.primary)
                    }
                }
            }
        }
    }

    // MARK: - Hero Section

    private var heroSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("TOTAL ACCOUNT VALUE")
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(AppTheme.labelSecondary)
                .tracking(-0.2)

            Text(AppTheme.formatCurrency(viewModel.portfolio.totalAccountValue))
                .font(.system(size: 36, weight: .heavy))
                .tracking(-0.5)

            HStack(spacing: 8) {
                HStack(spacing: 2) {
                    Image(systemName: "arrow.up.right")
                        .font(.system(size: 12, weight: .bold))
                    Text(AppTheme.formatPercent(viewModel.dailyGainPercent))
                        .font(.system(size: 15, weight: .bold))
                }
                .foregroundColor(AppTheme.growthGreen)

                Text(AppTheme.formatGainLoss(viewModel.dailyGain) + " today")
                    .font(.system(size: 15))
                    .foregroundColor(AppTheme.labelSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: - Chart

    private var performanceChart: some View {
        PerformanceChartView(dataPoints: viewModel.portfolioHistory)
    }

    // MARK: - Bento Grid

    private var bentoGrid: some View {
        HStack(spacing: 12) {
            // Liquid Cash card
            VStack(alignment: .leading) {
                HStack {
                    Image(systemName: "wallet.pass.fill")
                        .foregroundColor(AppTheme.primary)
                        .font(.system(size: 20))
                    Spacer()
                    Text("LIQUID CASH")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(AppTheme.labelSecondary)
                        .tracking(-0.2)
                }

                Spacer()

                VStack(alignment: .leading, spacing: 2) {
                    Text(AppTheme.formatCurrency(viewModel.portfolio.cashBalance))
                        .font(.system(size: 22, weight: .bold))
                        .tracking(-0.3)
                    Text("Available")
                        .font(.system(size: 11))
                        .foregroundColor(AppTheme.labelSecondary)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity)
            .aspectRatio(1, contentMode: .fit)
            .background(AppTheme.surfaceGray)
            .clipShape(RoundedRectangle(cornerRadius: 14))

            // Top performer card
            if let top = viewModel.topPerformer {
                VStack(alignment: .leading) {
                    Text("TOP PERFORMER")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(.white.opacity(0.7))
                        .tracking(-0.2)

                    Text(top.id)
                        .font(.system(size: 22, weight: .bold))
                        .foregroundColor(.white)

                    Text(AppTheme.formatPercent(top.totalGainLossPercent) + " Total")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.7))

                    Spacer()

                    NavigationLink(value: top.stock) {
                        Text("Details")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                            .background(Color.white.opacity(0.2))
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                }
                .padding(16)
                .frame(maxWidth: .infinity)
                .aspectRatio(1, contentMode: .fit)
                .background(AppTheme.primary)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }
        }
    }

    // MARK: - Watchlist

    private var watchlistSection: some View {
        VStack(spacing: 8) {
            HStack {
                Text("Watchlist")
                    .font(.system(size: 20, weight: .bold))
                    .tracking(-0.3)
                Spacer()
                Button("Edit") {}
                    .font(.system(size: 15, weight: .medium))
                    .foregroundColor(AppTheme.primary)
            }

            VStack(spacing: 0) {
                ForEach(viewModel.watchlist) { stock in
                    NavigationLink(value: stock) {
                        WatchlistRowView(stock: stock)
                    }
                    .buttonStyle(.plain)

                    if stock.id != viewModel.watchlist.last?.id {
                        Divider()
                            .padding(.leading, 68)
                    }
                }
            }
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(Color.gray.opacity(0.1), lineWidth: 1)
            )
        }
        .navigationDestination(for: Stock.self) { stock in
            StockDetailView(stock: stock)
                .environmentObject(viewModel)
        }
    }

    // MARK: - Market Intelligence

    private var marketIntelligence: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Market Intelligence")
                .font(.system(size: 20, weight: .bold))
                .tracking(-0.3)

            // News item
            HStack(alignment: .top, spacing: 12) {
                RoundedRectangle(cornerRadius: 12)
                    .fill(AppTheme.surfaceGray)
                    .frame(width: 80, height: 80)
                    .overlay(
                        Image(systemName: "chart.line.uptrend.xyaxis")
                            .font(.system(size: 24))
                            .foregroundColor(AppTheme.labelSecondary)
                    )

                VStack(alignment: .leading, spacing: 4) {
                    Text("BULLISH SIGNAL")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(AppTheme.primary)
                        .tracking(0.5)

                    Text("Tech sector shows resilience amid shifting interest rates.")
                        .font(.system(size: 15, weight: .bold))
                        .lineLimit(2)

                    Text("2h ago · 4 min read")
                        .font(.system(size: 12))
                        .foregroundColor(AppTheme.labelSecondary)
                }
            }

            // Editor's pick
            VStack(alignment: .leading, spacing: 6) {
                Text("EDITOR'S PICK")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(AppTheme.primary)
                    .tracking(0.5)

                Text("\"Market precision is not about guessing the future, but managing the risk of the present.\"")
                    .font(.system(size: 14, weight: .medium))
                    .italic()
                    .foregroundColor(.gray)
            }
            .padding(16)
            .background(AppTheme.surfaceGray)
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay(
                Rectangle()
                    .fill(AppTheme.primary)
                    .frame(width: 4),
                alignment: .leading
            )
            .clipShape(RoundedRectangle(cornerRadius: 14))
        }
    }
}
