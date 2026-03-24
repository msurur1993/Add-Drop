import SwiftUI

struct HoldingRowView: View {
    let holding: Holding

    var body: some View {
        HStack(spacing: 12) {
            StockIconView(ticker: holding.id)

            VStack(alignment: .leading, spacing: 2) {
                Text(holding.id)
                    .font(.system(size: 16, weight: .bold))
                Text(holding.stock.name)
                    .font(.system(size: 13))
                    .foregroundColor(AppTheme.labelSecondary)
                    .lineLimit(1)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text(AppTheme.formatCurrency(holding.currentValue))
                    .font(.system(size: 16, weight: .bold))

                HStack(spacing: 2) {
                    Text("\(AppTheme.formatGainLoss(holding.totalGainLoss)) (\(String(format: "%.1f", abs(holding.totalGainLossPercent)))%)")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(AppTheme.changeColor(for: holding.totalGainLoss))
                }
            }
        }
        .padding(16)
    }
}
