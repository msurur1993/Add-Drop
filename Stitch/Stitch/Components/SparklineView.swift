import SwiftUI

struct SparklineView: View {
    let dataPoints: [Double]
    let isPositive: Bool

    var body: some View {
        GeometryReader { geometry in
            let width = geometry.size.width
            let height = geometry.size.height
            let stepX = width / CGFloat(max(dataPoints.count - 1, 1))

            let minVal = dataPoints.min() ?? 0
            let maxVal = dataPoints.max() ?? 1
            let range = max(maxVal - minVal, 0.001)

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
            .stroke(
                isPositive ? AppTheme.growthGreen : AppTheme.lossRed,
                style: StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round)
            )
        }
    }
}
