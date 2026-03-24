import SwiftUI

enum AppTheme {
    // MARK: - Colors (iOS Native + Precision Ledger accents)
    static let primary = Color(hex: "007AFF")       // iOS System Blue
    static let brandBlue = Color(hex: "00346F")      // Deep institutional blue
    static let growthGreen = Color(hex: "34C759")     // iOS System Green
    static let lossRed = Color(hex: "FF3B30")         // iOS System Red
    static let surfaceGray = Color(hex: "F2F2F7")     // iOS System Gray 6
    static let labelSecondary = Color(hex: "8E8E93")  // iOS System Gray
    static let separator = Color(hex: "C6C6C8")       // iOS System Gray 4
    static let warmSurface = Color(hex: "FCF9F8")      // Design system surface

    // MARK: - Allocation colors
    static let allocationColors: [Color] = [
        brandBlue,
        growthGreen,
        .orange,
        Color(hex: "5AC8FA"), // iOS System Teal
        labelSecondary
    ]

    // MARK: - Convenience
    static func changeColor(for value: Double) -> Color {
        value >= 0 ? growthGreen : lossRed
    }

    static func formatCurrency(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.locale = Locale(identifier: "en_US")
        formatter.maximumFractionDigits = 2
        formatter.minimumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "$0.00"
    }

    static func formatPercent(_ value: Double) -> String {
        let sign = value >= 0 ? "+" : ""
        return "\(sign)\(String(format: "%.1f", value))%"
    }

    static func formatGainLoss(_ value: Double) -> String {
        let sign = value >= 0 ? "+" : ""
        return "\(sign)\(formatCurrency(value))"
    }
}

// MARK: - Color Hex Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 6:
            (a, r, g, b) = (255, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = ((int >> 24) & 0xFF, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
