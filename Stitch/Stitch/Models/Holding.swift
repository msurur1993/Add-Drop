import Foundation

struct Holding: Identifiable {
    let id: String // ticker
    let stock: Stock
    var shares: Double
    var averageCost: Double

    var currentValue: Double {
        shares * stock.currentPrice
    }

    var totalCost: Double {
        shares * averageCost
    }

    var totalGainLoss: Double {
        currentValue - totalCost
    }

    var totalGainLossPercent: Double {
        guard totalCost > 0 else { return 0 }
        return (totalGainLoss / totalCost) * 100
    }

    var isPositive: Bool {
        totalGainLoss >= 0
    }
}

extension Holding {
    static let sampleHoldings: [Holding] = [
        Holding(id: "SPUS", stock: .spus, shares: 1117.5, averageCost: 30.35),
        Holding(id: "NVDA", stock: .nvda, shares: 245.1, averageCost: 91.30),
        Holding(id: "SPDR GLD", stock: .gld, shares: 113.5, averageCost: 214.63),
        Holding(id: "CRWV", stock: .crwv, shares: 14.27, averageCost: 868.32),
    ]
}
