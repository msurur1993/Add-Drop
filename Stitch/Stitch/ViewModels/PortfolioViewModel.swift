import SwiftUI

@MainActor
class PortfolioViewModel: ObservableObject {
    @Published var portfolio: Portfolio
    @Published var watchlist: [Stock]
    @Published var selectedStock: Stock?

    // Chart data points (simulated portfolio value over time)
    @Published var portfolioHistory: [Double] = []

    // Daily gain for dashboard hero
    var dailyGain: Double { 2_391.12 }
    var dailyGainPercent: Double { 2.45 }

    init() {
        self.portfolio = .sample
        self.watchlist = Stock.all
        self.portfolioHistory = Self.generatePortfolioHistory()
    }

    // MARK: - Trading

    func executeTrade(_ order: TradeOrder) {
        guard order.amountInDollars > 0 else { return }

        switch order.side {
        case .buy:
            executeBuy(order)
        case .sell:
            executeSell(order)
        }
    }

    private func executeBuy(_ order: TradeOrder) {
        guard portfolio.cashBalance >= order.amountInDollars else { return }

        let shares = order.estimatedShares
        portfolio.cashBalance -= order.amountInDollars

        if let index = portfolio.holdings.firstIndex(where: { $0.id == order.stock.id }) {
            // Update existing holding with new average cost
            let existing = portfolio.holdings[index]
            let totalShares = existing.shares + shares
            let totalCost = (existing.shares * existing.averageCost) + order.amountInDollars
            let newAvgCost = totalCost / totalShares

            portfolio.holdings[index] = Holding(
                id: existing.id,
                stock: existing.stock,
                shares: totalShares,
                averageCost: newAvgCost
            )
        } else {
            // Create new holding
            let holding = Holding(
                id: order.stock.id,
                stock: order.stock,
                shares: shares,
                averageCost: order.stock.currentPrice
            )
            portfolio.holdings.append(holding)
        }
    }

    private func executeSell(_ order: TradeOrder) {
        guard let index = portfolio.holdings.firstIndex(where: { $0.id == order.stock.id }) else { return }

        let shares = order.estimatedShares
        let holding = portfolio.holdings[index]
        guard holding.shares >= shares else { return }

        portfolio.cashBalance += order.amountInDollars

        let remainingShares = holding.shares - shares
        if remainingShares <= 0.0001 {
            portfolio.holdings.remove(at: index)
        } else {
            portfolio.holdings[index] = Holding(
                id: holding.id,
                stock: holding.stock,
                shares: remainingShares,
                averageCost: holding.averageCost
            )
        }
    }

    // MARK: - Top Performer

    var topPerformer: Holding? {
        portfolio.holdings.max(by: { $0.totalGainLossPercent < $1.totalGainLossPercent })
    }

    // MARK: - Simulated History

    private static func generatePortfolioHistory() -> [Double] {
        // Generate a realistic upward-trending portfolio curve
        var values: [Double] = []
        var value = 95_000.0
        let points = 50
        for i in 0..<points {
            let trend = 200.0
            let noise = Double.random(in: -800...800)
            let momentum = Double(i) * 40
            value += trend + noise + momentum / Double(points)
            values.append(max(value, 90_000))
        }
        return values
    }
}
