import Foundation

struct Portfolio {
    var cashBalance: Double
    var holdings: [Holding]

    var totalInvestedValue: Double {
        holdings.reduce(0) { $0 + $1.currentValue }
    }

    var totalAccountValue: Double {
        cashBalance + totalInvestedValue
    }

    var totalGainLoss: Double {
        holdings.reduce(0) { $0 + $1.totalGainLoss }
    }

    var totalGainLossPercent: Double {
        let totalCost = holdings.reduce(0) { $0 + $1.totalCost }
        guard totalCost > 0 else { return 0 }
        return (totalGainLoss / totalCost) * 100
    }

    // Asset allocation percentages
    var allocations: [(ticker: String, percent: Double)] {
        guard totalInvestedValue > 0 else { return [] }
        return holdings.map { holding in
            (ticker: holding.id, percent: (holding.currentValue / totalInvestedValue) * 100)
        }.sorted { $0.percent > $1.percent }
    }
}

extension Portfolio {
    static let sample = Portfolio(
        cashBalance: 18_422.15,
        holdings: Holding.sampleHoldings
    )
}

struct TradeOrder {
    enum OrderSide: String, CaseIterable {
        case buy = "Buy"
        case sell = "Sell"
    }

    enum OrderType: String, CaseIterable {
        case market = "Market"
        case limit = "Limit"
    }

    enum Expiry: String, CaseIterable {
        case endOfDay = "End of Day"
        case goodTilCanceled = "Good til Canceled"
    }

    var stock: Stock
    var side: OrderSide = .buy
    var amountInDollars: Double = 0
    var orderType: OrderType = .market
    var expiry: Expiry = .endOfDay

    var estimatedShares: Double {
        guard stock.currentPrice > 0 else { return 0 }
        return amountInDollars / stock.currentPrice
    }
}
