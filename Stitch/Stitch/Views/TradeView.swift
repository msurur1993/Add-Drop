import SwiftUI

struct TradeView: View {
    let stock: Stock
    @EnvironmentObject var viewModel: PortfolioViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var order: TradeOrder
    @State private var amountText = ""
    @State private var showConfirmation = false

    init(stock: Stock) {
        self.stock = stock
        _order = State(initialValue: TradeOrder(stock: stock))
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                stockHeader
                segmentedControl
                amountInputCard
                orderDetailsCard
                confirmButton
            }
            .padding(.horizontal, 16)
            .padding(.top, 16)
            .padding(.bottom, 40)
        }
        .background(AppTheme.surfaceGray)
        .navigationBarTitleDisplayMode(.inline)
        .navigationTitle("Trade")
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button("Details") {}
                    .foregroundColor(AppTheme.primary)
            }
        }
        .alert("Trade Confirmed!", isPresented: $showConfirmation) {
            Button("Done") { dismiss() }
        } message: {
            let sharesText = String(format: "%.4f", order.estimatedShares)
            Text("You \(order.side == .buy ? "bought" : "sold") \(sharesText) shares of \(stock.id) for \(AppTheme.formatCurrency(order.amountInDollars)).")
        }
    }

    // MARK: - Stock Header

    private var stockHeader: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(stock.id)
                    .font(.system(size: 28, weight: .heavy))
                    .foregroundColor(AppTheme.brandBlue)
                    .tracking(-0.5)
                Text(stock.name)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(AppTheme.labelSecondary)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 2) {
                Text(AppTheme.formatCurrency(stock.currentPrice))
                    .font(.system(size: 24, weight: .bold))
                Text(AppTheme.formatPercent(stock.dailyChange) + " today")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(AppTheme.changeColor(for: stock.dailyChange))
            }
        }
        .padding(.horizontal, 4)
    }

    // MARK: - Segmented Control

    private var segmentedControl: some View {
        HStack(spacing: 0) {
            ForEach(TradeOrder.OrderSide.allCases, id: \.self) { side in
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        order.side = side
                    }
                } label: {
                    Text(side.rawValue)
                        .font(.system(size: 14, weight: .semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(
                            order.side == side
                                ? RoundedRectangle(cornerRadius: 7)
                                    .fill(Color.white)
                                    .shadow(color: .black.opacity(0.12), radius: 1.5, y: 1)
                                : nil
                        )
                }
                .buttonStyle(.plain)
            }
        }
        .padding(2)
        .background(Color(hex: "EFEFF0"))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: - Amount Input

    private var amountInputCard: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Amount")
                    .font(.system(size: 15, weight: .semibold))
                Spacer()
                HStack(spacing: 2) {
                    Text("USD")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(AppTheme.primary)
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.system(size: 12))
                        .foregroundColor(AppTheme.primary)
                }
            }
            .padding(.bottom, 24)

            // Dollar input
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text("$")
                    .font(.system(size: 36, weight: .bold))
                    .foregroundColor(AppTheme.brandBlue)

                TextField("0", text: $amountText)
                    .font(.system(size: 56, weight: .bold))
                    .foregroundColor(AppTheme.brandBlue)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.center)
                    .onChange(of: amountText) { _, newValue in
                        order.amountInDollars = Double(newValue) ?? 0
                    }
            }
            .padding(.vertical, 16)

            Divider()
                .padding(.top, 16)

            // Estimated shares & price
            VStack(spacing: 8) {
                HStack {
                    Text("Est. Shares")
                        .font(.system(size: 14))
                        .foregroundColor(AppTheme.labelSecondary)
                    Spacer()
                    Text(String(format: "%.4f", order.estimatedShares))
                        .font(.system(size: 14, weight: .semibold))
                }

                HStack {
                    Text("Market Price")
                        .font(.system(size: 14))
                        .foregroundColor(AppTheme.labelSecondary)
                    Spacer()
                    Text(AppTheme.formatCurrency(stock.currentPrice))
                        .font(.system(size: 14, weight: .semibold))
                }
            }
            .padding(.top, 16)
        }
        .padding(16)
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color.black.opacity(0.04), lineWidth: 1)
        )
    }

    // MARK: - Order Details

    private var orderDetailsCard: some View {
        VStack(spacing: 0) {
            // Buying Power
            HStack {
                HStack(spacing: 10) {
                    Image(systemName: "wallet.pass.fill")
                        .foregroundColor(AppTheme.primary)
                    Text("Buying Power")
                        .font(.system(size: 15, weight: .medium))
                }
                Spacer()
                HStack(spacing: 4) {
                    Text(AppTheme.formatCurrency(viewModel.portfolio.cashBalance))
                        .font(.system(size: 15, weight: .semibold))
                    Image(systemName: "chevron.right")
                        .font(.system(size: 14))
                        .foregroundColor(Color.gray.opacity(0.3))
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)

            Divider().padding(.leading, 16)

            // Order Type
            HStack {
                Text("Order Type")
                    .font(.system(size: 15, weight: .medium))
                Spacer()
                HStack(spacing: 4) {
                    Text(order.orderType.rawValue)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(AppTheme.primary)
                    Image(systemName: "chevron.right")
                        .font(.system(size: 14))
                        .foregroundColor(AppTheme.primary)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)

            Divider().padding(.leading, 16)

            // Expires
            HStack {
                Text("Expires")
                    .font(.system(size: 15, weight: .medium))
                Spacer()
                HStack(spacing: 4) {
                    Text(order.expiry.rawValue)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(AppTheme.primary)
                    Image(systemName: "chevron.right")
                        .font(.system(size: 14))
                        .foregroundColor(AppTheme.primary)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        .background(Color.white)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color.black.opacity(0.04), lineWidth: 1)
        )
    }

    // MARK: - Confirm

    private var confirmButton: some View {
        VStack(spacing: 16) {
            Button {
                viewModel.executeTrade(order)
                showConfirmation = true
            } label: {
                Text("Confirm Trade")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(AppTheme.brandBlue)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .disabled(order.amountInDollars <= 0)
            .opacity(order.amountInDollars > 0 ? 1 : 0.5)

            Text("By confirming, you agree to the Execution Policy and the risks associated with simulated trading.")
                .font(.system(size: 12))
                .foregroundColor(AppTheme.labelSecondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)
        }
        .padding(.top, 16)
    }
}
