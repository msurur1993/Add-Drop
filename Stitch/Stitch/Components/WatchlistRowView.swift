import SwiftUI

struct WatchlistRowView: View {
    let stock: Stock

    var body: some View {
        HStack(spacing: 12) {
            StockIconView(ticker: stock.id)

            VStack(alignment: .leading, spacing: 2) {
                Text(stock.id)
                    .font(.system(size: 16, weight: .bold))
                Text(stock.name)
                    .font(.system(size: 13))
                    .foregroundColor(AppTheme.labelSecondary)
                    .lineLimit(1)
            }

            Spacer()

            // Mini sparkline
            SparklineView(
                dataPoints: stock.sparkline,
                isPositive: stock.isDailyPositive
            )
            .frame(width: 64, height: 24)

            VStack(alignment: .trailing, spacing: 2) {
                Text(AppTheme.formatCurrency(stock.currentPrice))
                    .font(.system(size: 16, weight: .bold))
                Text(AppTheme.formatPercent(stock.dailyChange))
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(AppTheme.changeColor(for: stock.dailyChange))
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }
}
