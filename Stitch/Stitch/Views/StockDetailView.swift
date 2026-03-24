import SwiftUI

struct StockDetailView: View {
    let stock: Stock
    @EnvironmentObject var viewModel: PortfolioViewModel
    @State private var selectedPeriod = "1D"
    let periods = ["1D", "1W", "1M", "3M", "1Y", "ALL"]

    // Simulated chart data
    private var chartData: [Double] {
        var values: [Double] = []
        var value = stock.currentPrice * 0.92
        for _ in 0..<40 {
            value += Double.random(in: -2...3)
            values.append(max(value, stock.currentPrice * 0.85))
        }
        values.append(stock.currentPrice)
        return values
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                stockHeader
                chartSection
                keyStatistics
                analystConsensus
                marketIntel
            }
            .padding(.bottom, 120)
        }
        .background(Color.white)
        .navigationBarTitleDisplayMode(.inline)
        .navigationTitle(stock.id)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button {
                    // more options
                } label: {
                    Image(systemName: "ellipsis")
                        .foregroundColor(AppTheme.primary)
                }
            }
        }
        .safeAreaInset(edge: .bottom) {
            bottomActionBar
        }
    }

    // MARK: - Stock Header

    private var stockHeader: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 4) {
                Text(stock.name)
                    .font(.system(size: 34, weight: .bold))
                    .tracking(-0.5)
                    .lineLimit(1)
                    .minimumScaleFactor(0.6)

                HStack(spacing: 8) {
                    Text("\(stock.exchange): \(stock.id)")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(AppTheme.labelSecondary)
                        .textCase(.uppercase)

                    HStack(spacing: 2) {
                        Image(systemName: stock.isDailyPositive ? "arrow.up" : "arrow.down")
                            .font(.system(size: 11, weight: .bold))
                        Text(AppTheme.formatPercent(stock.dailyChange))
                            .font(.system(size: 13, weight: .semibold))
                    }
                    .foregroundColor(AppTheme.changeColor(for: stock.dailyChange))
                }
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text(AppTheme.formatCurrency(stock.currentPrice))
                    .font(.system(size: 34, weight: .bold))
                    .tracking(-0.5)

                if let afterHours = stock.afterHoursPrice {
                    Text("After Hours: \(AppTheme.formatCurrency(afterHours))")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundColor(AppTheme.labelSecondary)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 20)
    }

    // MARK: - Chart

    private var chartSection: some View {
        VStack(spacing: 0) {
            // Period selector
            HStack(spacing: 0) {
                ForEach(periods, id: \.self) { period in
                    Button {
                        withAnimation { selectedPeriod = period }
                    } label: {
                        Text(period)
                            .font(.system(size: 13, weight: selectedPeriod == period ? .semibold : .medium))
                            .foregroundColor(selectedPeriod == period ? .primary : AppTheme.labelSecondary)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 6)
                            .background(
                                selectedPeriod == period
                                    ? RoundedRectangle(cornerRadius: 7)
                                        .fill(Color.white)
                                        .shadow(color: .black.opacity(0.08), radius: 2, y: 1)
                                    : nil
                            )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(2)
            .background(AppTheme.surfaceGray)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .padding(16)

            // Chart
            chartBody
                .frame(height: 240)
                .padding(.horizontal, 24)

            // Time labels
            HStack {
                Text("09:30 AM")
                Spacer()
                Text("04:00 PM")
            }
            .font(.system(size: 11, weight: .medium))
            .foregroundColor(AppTheme.labelSecondary)
            .textCase(.uppercase)
            .padding(.horizontal, 24)
            .padding(.top, 8)
            .padding(.bottom, 16)
        }
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(Color.gray.opacity(0.1), lineWidth: 1)
        )
        .padding(.horizontal, 16)
    }

    private var chartBody: some View {
        GeometryReader { geometry in
            let data = chartData
            let width = geometry.size.width
            let height = geometry.size.height
            let stepX = width / CGFloat(max(data.count - 1, 1))
            let minVal = (data.min() ?? 0) * 0.99
            let maxVal = (data.max() ?? 1) * 1.01
            let range = max(maxVal - minVal, 1)

            ZStack {
                // Gradient fill
                Path { path in
                    for (i, val) in data.enumerated() {
                        let x = CGFloat(i) * stepX
                        let y = height - ((CGFloat(val - minVal) / CGFloat(range)) * height)
                        if i == 0 { path.move(to: CGPoint(x: x, y: y)) }
                        else { path.addLine(to: CGPoint(x: x, y: y)) }
                    }
                    path.addLine(to: CGPoint(x: width, y: height))
                    path.addLine(to: CGPoint(x: 0, y: height))
                    path.closeSubpath()
                }
                .fill(
                    LinearGradient(
                        colors: [AppTheme.growthGreen.opacity(0.1), AppTheme.growthGreen.opacity(0)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )

                // Line
                Path { path in
                    for (i, val) in data.enumerated() {
                        let x = CGFloat(i) * stepX
                        let y = height - ((CGFloat(val - minVal) / CGFloat(range)) * height)
                        if i == 0 { path.move(to: CGPoint(x: x, y: y)) }
                        else { path.addLine(to: CGPoint(x: x, y: y)) }
                    }
                }
                .stroke(AppTheme.growthGreen, style: StrokeStyle(lineWidth: 2.5, lineCap: .round, lineJoin: .round))
            }
        }
    }

    // MARK: - Key Statistics

    private var keyStatistics: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("KEY STATISTICS")
                .font(.system(size: 13, weight: .medium))
                .foregroundColor(AppTheme.labelSecondary)
                .tracking(0.5)
                .padding(.horizontal, 20)
                .padding(.top, 24)
                .padding(.bottom, 8)

            VStack(spacing: 0) {
                statRow("Market Cap", stock.marketCap)
                statRow("P/E Ratio", String(format: "%.2f", stock.peRatio))
                statRow("Div. Yield", String(format: "%.2f%%", stock.divYield))
                statRow("Avg. Volume", stock.avgVolume)
                statRow("52W High", String(format: "%.2f", stock.high52Week), isLast: true)
            }
            .background(Color.white)
            .overlay(
                VStack {
                    Divider()
                    Spacer()
                    Divider()
                }
            )
        }
    }

    private func statRow(_ label: String, _ value: String, isLast: Bool = false) -> some View {
        VStack(spacing: 0) {
            HStack {
                Text(label)
                    .font(.system(size: 17))
                Spacer()
                Text(value)
                    .font(.system(size: 17, weight: .medium))
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)

            if !isLast {
                Divider()
                    .padding(.leading, 16)
            }
        }
    }

    // MARK: - Analyst Consensus

    private var analystConsensus: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("ANALYST CONSENSUS")
                .font(.system(size: 11, weight: .bold))
                .tracking(1)
                .foregroundColor(.white.opacity(0.7))

            HStack(alignment: .bottom, spacing: 12) {
                Text("Strong Buy")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundColor(.white)

                Text("92% BUY")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Color.white.opacity(0.2))
                    .clipShape(RoundedRectangle(cornerRadius: 4))
                    .padding(.bottom, 4)
            }

            Text("Based on 48 ratings in the last 90 days. Average price target: $145.00 (+12.8%)")
                .font(.system(size: 13))
                .foregroundColor(.white.opacity(0.8))
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AppTheme.primary)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: AppTheme.primary.opacity(0.2), radius: 12, y: 6)
        .padding(.horizontal, 16)
        .padding(.top, 28)
    }

    // MARK: - Market Intel

    private var marketIntel: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Market Intel")
                .font(.system(size: 22, weight: .bold))
                .padding(.horizontal, 4)

            newsCard(
                tag: "EARNINGS IMPACT",
                tagColor: AppTheme.primary,
                headline: "NVIDIA's Data Center revenue exceeds analyst forecasts as AI demand surges.",
                source: "2h ago · Financial Times",
                icon: "cpu"
            )

            newsCard(
                tag: "COMPETITOR WATCH",
                tagColor: AppTheme.labelSecondary,
                headline: "How Blackwell architecture maintains lead over AMD.",
                source: "5h ago · Reuters",
                icon: "brain"
            )
        }
        .padding(.horizontal, 16)
        .padding(.top, 28)
    }

    private func newsCard(tag: String, tagColor: Color, headline: String, source: String, icon: String) -> some View {
        HStack(spacing: 12) {
            RoundedRectangle(cornerRadius: 10)
                .fill(AppTheme.surfaceGray)
                .frame(width: 96, height: 96)
                .overlay(
                    Image(systemName: icon)
                        .font(.system(size: 28))
                        .foregroundColor(AppTheme.labelSecondary)
                )

            VStack(alignment: .leading, spacing: 6) {
                Text(tag)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(tagColor)
                    .tracking(0.5)

                Text(headline)
                    .font(.system(size: 15, weight: .semibold))
                    .lineLimit(2)

                Text(source)
                    .font(.system(size: 11))
                    .foregroundColor(AppTheme.labelSecondary)
            }
        }
        .padding(12)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color.gray.opacity(0.08), lineWidth: 1)
        )
    }

    // MARK: - Bottom Action Bar

    private var bottomActionBar: some View {
        HStack(spacing: 12) {
            Button {
                // toggle watchlist
            } label: {
                Image(systemName: "star")
                    .font(.system(size: 22))
                    .foregroundColor(AppTheme.primary)
                    .frame(width: 48, height: 48)
                    .background(AppTheme.surfaceGray)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }

            NavigationLink {
                TradeView(stock: stock)
                    .environmentObject(viewModel)
            } label: {
                HStack(spacing: 6) {
                    Text("Trade \(stock.id)")
                        .font(.system(size: 17, weight: .semibold))
                    Image(systemName: "arrow.left.arrow.right")
                        .font(.system(size: 16))
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(AppTheme.primary)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }
        }
        .padding(.horizontal, 20)
        .padding(.top, 12)
        .padding(.bottom, 28)
        .background(
            Color.white.opacity(0.9)
                .background(.ultraThinMaterial)
        )
        .overlay(Divider().opacity(0.3), alignment: .top)
    }
}
