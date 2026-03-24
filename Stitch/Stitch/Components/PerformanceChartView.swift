import SwiftUI

struct PerformanceChartView: View {
    let dataPoints: [Double]
    @State private var selectedPeriod = "1D"
    let periods = ["1D", "1W", "1M", "1Y", "All"]

    var body: some View {
        VStack(spacing: 0) {
            // Chart area
            GeometryReader { geometry in
                let width = geometry.size.width
                let height = geometry.size.height
                let stepX = width / CGFloat(max(dataPoints.count - 1, 1))

                let minVal = (dataPoints.min() ?? 0) * 0.98
                let maxVal = (dataPoints.max() ?? 1) * 1.02
                let range = max(maxVal - minVal, 1)

                ZStack {
                    // Gradient fill
                    Path { path in
                        for (index, point) in dataPoints.enumerated() {
                            let x = CGFloat(index) * stepX
                            let y = height - ((CGFloat(point - minVal) / CGFloat(range)) * height)
                            if index == 0 {
                                path.move(to: CGPoint(x: x, y: y))
                            } else {
                                path.addLine(to: CGPoint(x: x, y: y))
                            }
                        }
                        path.addLine(to: CGPoint(x: width, y: height))
                        path.addLine(to: CGPoint(x: 0, y: height))
                        path.closeSubpath()
                    }
                    .fill(
                        LinearGradient(
                            colors: [AppTheme.primary.opacity(0.2), AppTheme.primary.opacity(0)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )

                    // Line
                    Path { path in
                        for (index, point) in dataPoints.enumerated() {
                            let x = CGFloat(index) * stepX
                            let y = height - ((CGFloat(point - minVal) / CGFloat(range)) * height)
                            if index == 0 {
                                path.move(to: CGPoint(x: x, y: y))
                            } else {
                                path.addLine(to: CGPoint(x: x, y: y))
                            }
                        }
                    }
                    .stroke(AppTheme.primary, style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round))

                    // End dot
                    if let last = dataPoints.last {
                        let x = width
                        let y = height - ((CGFloat(last - minVal) / CGFloat(range)) * height)
                        Circle()
                            .fill(AppTheme.primary)
                            .frame(width: 8, height: 8)
                            .position(x: x, y: y)
                    }
                }
            }
            .frame(height: 180)
            .padding(.horizontal, 8)
            .padding(.top, 16)

            // Segmented period control
            HStack(spacing: 0) {
                ForEach(periods, id: \.self) { period in
                    Button {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            selectedPeriod = period
                        }
                    } label: {
                        Text(period)
                            .font(.system(size: 12, weight: selectedPeriod == period ? .bold : .semibold))
                            .foregroundColor(selectedPeriod == period ? .primary : .secondary)
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
            .background(Color(.systemGray5).opacity(0.5))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        .background(AppTheme.surfaceGray)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}
