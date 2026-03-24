import SwiftUI

struct StockIconView: View {
    let ticker: String
    var size: CGFloat = 40
    var fontSize: CGFloat = 14

    private var backgroundColor: Color {
        switch ticker {
        case "SPUS": return AppTheme.brandBlue.opacity(0.1)
        case "NVDA": return AppTheme.growthGreen.opacity(0.1)
        case "SPDR GLD": return Color.orange.opacity(0.1)
        case "CRWV": return Color.blue.opacity(0.08)
        default: return Color.gray.opacity(0.1)
        }
    }

    private var foregroundColor: Color {
        switch ticker {
        case "SPUS": return AppTheme.brandBlue
        case "NVDA": return AppTheme.growthGreen
        case "SPDR GLD": return .orange
        case "CRWV": return .blue
        default: return .gray
        }
    }

    private var abbreviation: String {
        if ticker.count <= 2 { return ticker }
        return String(ticker.prefix(2)).uppercased()
    }

    var body: some View {
        RoundedRectangle(cornerRadius: 10)
            .fill(backgroundColor)
            .frame(width: size, height: size)
            .overlay(
                Text(abbreviation)
                    .font(.system(size: fontSize, weight: .bold))
                    .foregroundColor(foregroundColor)
            )
    }
}
