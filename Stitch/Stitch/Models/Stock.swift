import Foundation

struct Stock: Identifiable, Hashable {
    let id: String // ticker symbol
    let name: String
    let exchange: String
    var currentPrice: Double
    var dailyChange: Double // percentage
    var afterHoursPrice: Double?

    // Key statistics
    var marketCap: String
    var peRatio: Double
    var divYield: Double
    var avgVolume: String
    var high52Week: Double

    // Sparkline data (normalized 0-1)
    var sparkline: [Double]

    var isDailyPositive: Bool { dailyChange >= 0 }
}

extension Stock {
    static let spus = Stock(
        id: "SPUS",
        name: "S&P 500 Sharia Industry Exclusions ETF",
        exchange: "NYSE",
        currentPrice: 34.12,
        dailyChange: 0.84,
        marketCap: "1.2B",
        peRatio: 22.15,
        divYield: 1.12,
        avgVolume: "45.2M",
        high52Week: 38.50,
        sparkline: [0.7, 0.6, 0.8, 0.3, 0.4, 0.1]
    )

    static let gld = Stock(
        id: "SPDR GLD",
        name: "SPDR Gold Shares",
        exchange: "NYSE",
        currentPrice: 212.45,
        dailyChange: -0.21,
        marketCap: "62.8B",
        peRatio: 0,
        divYield: 0,
        avgVolume: "8.1M",
        high52Week: 225.30,
        sparkline: [0.2, 0.3, 0.25, 0.5, 0.45, 0.8]
    )

    static let nvda = Stock(
        id: "NVDA",
        name: "NVIDIA Corporation",
        exchange: "NASDAQ",
        currentPrice: 128.54,
        dailyChange: 2.45,
        afterHoursPrice: 128.60,
        marketCap: "3.16T",
        peRatio: 74.21,
        divYield: 0.02,
        avgVolume: "412.8M",
        high52Week: 140.76,
        sparkline: [0.85, 0.7, 0.3, 0.4, 0.1, 0.05]
    )

    static let crwv = Stock(
        id: "CRWV",
        name: "CrowdStrike Holdings",
        exchange: "NASDAQ",
        currentPrice: 875.28,
        dailyChange: 4.28,
        marketCap: "210.5B",
        peRatio: 680.12,
        divYield: 0,
        avgVolume: "3.2M",
        high52Week: 920.00,
        sparkline: [0.9, 0.75, 0.5, 0.55, 0.2, 0.05]
    )

    static let all: [Stock] = [spus, gld, nvda, crwv]
}
