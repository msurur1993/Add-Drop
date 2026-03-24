import SwiftUI

struct PortfolioView: View {
    @EnvironmentObject var viewModel: PortfolioViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    heroBalance
                    cashCard
                    assetAllocation
                    holdingsSection
                    insightsCard
                    taxStatement
                }
                .padding(.horizontal, 16)
                .padding(.top, 8)
                .padding(.bottom, 100)
            }
            .background(AppTheme.surfaceGray)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    HStack(spacing: 8) {
                        Circle()
                            .fill(Color.gray.opacity(0.2))
                            .frame(width: 32, height: 32)
                            .overlay(
                                Image(systemName: "person.fill")
                                    .font(.system(size: 14))
                                    .foregroundColor(AppTheme.labelSecondary)
                            )
                        Text("Portfolio")
                            .font(.system(size: 18, weight: .bold))
                            .tracking(-0.3)
                    }
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        // notifications
                    } label: {
                        Image(systemName: "bell")
                            .foregroundColor(AppTheme.primary)
                    }
                }
            }
        }
    }

    // MARK: - Hero Balance

    private var heroBalance: some View {
        VStack(spacing: 8) {
            Text("TOTAL NET WORTH")
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(AppTheme.labelSecondary)
                .tracking(0.5)

            Text(AppTheme.formatCurrency(viewModel.portfolio.totalAccountValue))
                .font(.system(size: 36, weight: .heavy))
                .tracking(-0.5)

            HStack(spacing: 4) {
                Text("\(AppTheme.formatGainLoss(viewModel.portfolio.totalGainLoss)) (\(String(format: "%.1f", viewModel.portfolio.totalGainLossPercent))%)")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(AppTheme.growthGreen)

                Text("Past 30 days")
                    .font(.system(size: 15))
                    .foregroundColor(AppTheme.labelSecondary)
            }
        }
        .padding(.vertical, 20)
    }

    // MARK: - Cash Card

    private var cashCard: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Available Cash")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(AppTheme.labelSecondary)
                Text(AppTheme.formatCurrency(viewModel.portfolio.cashBalance))
                    .font(.system(size: 20, weight: .bold))
            }

            Spacer()

            Button {
                // deposit action
            } label: {
                Text("Deposit")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 10)
                    .background(AppTheme.primary)
                    .clipShape(Capsule())
            }
        }
        .padding(16)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .shadow(color: .black.opacity(0.03), radius: 4, y: 2)
    }

    // MARK: - Asset Allocation

    private var assetAllocation: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Asset Allocation")
                    .font(.system(size: 17, weight: .bold))
                Spacer()
                Button("See All") {}
                    .font(.system(size: 15))
                    .foregroundColor(AppTheme.primary)
            }

            // Allocation bar
            GeometryReader { geometry in
                let totalWidth = geometry.size.width
                HStack(spacing: 0) {
                    ForEach(Array(viewModel.portfolio.allocations.enumerated()), id: \.offset) { index, alloc in
                        let colorIndex = min(index, AppTheme.allocationColors.count - 1)
                        RoundedRectangle(cornerRadius: index == 0 ? 4 : (index == viewModel.portfolio.allocations.count - 1 ? 4 : 0))
                            .fill(AppTheme.allocationColors[colorIndex])
                            .frame(width: totalWidth * (alloc.percent / 100))
                    }
                }
            }
            .frame(height: 8)
            .clipShape(RoundedRectangle(cornerRadius: 4))

            // Legend
            let allocations = viewModel.portfolio.allocations
            HStack(spacing: 16) {
                ForEach(Array(allocations.prefix(3).enumerated()), id: \.offset) { index, alloc in
                    let colorIndex = min(index, AppTheme.allocationColors.count - 1)
                    HStack(spacing: 6) {
                        Circle()
                            .fill(AppTheme.allocationColors[colorIndex])
                            .frame(width: 8, height: 8)
                        Text("\(alloc.ticker) \(Int(alloc.percent))%")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(AppTheme.labelSecondary)
                    }
                }
            }
        }
    }

    // MARK: - Holdings

    private var holdingsSection: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Holdings")
                    .font(.system(size: 17, weight: .bold))
                Spacer()
                Text("\(viewModel.portfolio.holdings.count) Assets")
                    .font(.system(size: 13))
                    .foregroundColor(AppTheme.labelSecondary)
            }
            .padding(.horizontal, 4)
            .padding(.bottom, 8)

            VStack(spacing: 0) {
                ForEach(viewModel.portfolio.holdings) { holding in
                    NavigationLink(value: holding.stock) {
                        HoldingRowView(holding: holding)
                    }
                    .buttonStyle(.plain)

                    if holding.id != viewModel.portfolio.holdings.last?.id {
                        Divider()
                            .padding(.leading, 68)
                    }
                }
            }
            .background(Color.white)
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .shadow(color: .black.opacity(0.03), radius: 4, y: 2)
            .navigationDestination(for: Stock.self) { stock in
                StockDetailView(stock: stock)
                    .environmentObject(viewModel)
            }
        }
    }

    // MARK: - Insights

    private var insightsCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: "lightbulb.fill")
                    .font(.system(size: 16))
                    .foregroundColor(AppTheme.primary)
                Text("INSIGHTS")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(AppTheme.primary)
                    .tracking(0.5)
            }

            if let top = viewModel.topPerformer {
                Text("Your \(top.id) position has outperformed the market by ")
                    .font(.system(size: 15))
                +
                Text("\(Int(top.totalGainLossPercent))%")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundColor(AppTheme.growthGreen)
                +
                Text(". Consider rebalancing if tech exposure exceeds 30%.")
                    .font(.system(size: 15))
            }
        }
        .padding(16)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .shadow(color: .black.opacity(0.03), radius: 4, y: 2)
    }

    // MARK: - Tax Statement

    private var taxStatement: some View {
        HStack(spacing: 12) {
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.gray.opacity(0.05))
                .frame(width: 40, height: 40)
                .overlay(
                    Image(systemName: "doc.text")
                        .foregroundColor(AppTheme.labelSecondary)
                )

            VStack(alignment: .leading, spacing: 2) {
                Text("Q3 2023 Tax Statement")
                    .font(.system(size: 15, weight: .bold))
                Text("Ready to download")
                    .font(.system(size: 12))
                    .foregroundColor(AppTheme.labelSecondary)
            }

            Spacer()

            Button {
                // download
            } label: {
                Image(systemName: "arrow.down.circle")
                    .font(.system(size: 22))
                    .foregroundColor(AppTheme.primary)
            }
        }
        .padding(16)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .shadow(color: .black.opacity(0.03), radius: 4, y: 2)
    }
}
