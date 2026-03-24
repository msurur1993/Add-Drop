import { Bell, Lightbulb, FileText, Download } from "lucide-react";
import HoldingRow from "../components/HoldingRow";
import { formatCurrency, formatGainLoss, ALLOC_COLORS, ALLOC_DOT_COLORS } from "../data/helpers";

export default function Portfolio({ portfolio, onSelectStock }) {
  return (
    <div className="bg-surface min-h-screen pb-6 space-y-5 px-4">
      {/* Nav */}
      <div className="flex items-center justify-between pt-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
            <span className="text-label-secondary text-sm">👤</span>
          </div>
          <span className="text-lg font-bold tracking-tight">Portfolio</span>
        </div>
        <button className="text-primary p-1">
          <Bell size={22} />
        </button>
      </div>

      {/* Hero */}
      <div className="text-center py-5">
        <p className="text-[13px] font-semibold text-label-secondary uppercase tracking-wide mb-1">
          Total Net Worth
        </p>
        <h2 className="text-4xl font-extrabold tracking-tight">
          {formatCurrency(portfolio.totalAccountValue)}
        </h2>
        <div className="mt-2 flex justify-center items-center gap-1">
          <span className="text-growth font-semibold text-[15px]">
            {formatGainLoss(portfolio.totalGainLoss)} ({portfolio.totalGainLossPercent.toFixed(1)}%)
          </span>
          <span className="text-label-secondary text-[15px]">Past 30 days</span>
        </div>
      </div>

      {/* Cash Card */}
      <div className="bg-white rounded-xl p-4 flex justify-between items-center shadow-sm">
        <div>
          <p className="text-[13px] font-medium text-label-secondary">Available Cash</p>
          <h3 className="text-xl font-bold">{formatCurrency(portfolio.cash)}</h3>
        </div>
        <button className="bg-primary text-white px-5 py-2 rounded-full font-bold text-[15px] active:opacity-70 transition-opacity">
          Deposit
        </button>
      </div>

      {/* Asset Allocation */}
      <div>
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-[17px] font-bold">Asset Allocation</h3>
          <button className="text-primary text-[15px]">See All</button>
        </div>

        {/* Bar */}
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden flex mb-3">
          {portfolio.allocations.map((alloc, i) => (
            <div
              key={alloc.ticker}
              className={`h-full ${ALLOC_COLORS[Math.min(i, ALLOC_COLORS.length - 1)]}`}
              style={{ width: `${alloc.percent}%` }}
            />
          ))}
        </div>

        {/* Legend */}
        <div className="flex gap-4 flex-wrap">
          {portfolio.allocations.slice(0, 3).map((alloc, i) => (
            <div key={alloc.ticker} className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${ALLOC_DOT_COLORS[Math.min(i, ALLOC_DOT_COLORS.length - 1)]}`} />
              <span className="text-[12px] font-medium text-label-secondary">
                {alloc.ticker} {Math.round(alloc.percent)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Holdings */}
      <div>
        <div className="flex justify-between items-end mb-2 px-1">
          <h3 className="text-[17px] font-bold">Holdings</h3>
          <span className="text-[13px] text-label-secondary">
            {portfolio.holdings.length} Assets
          </span>
        </div>
        <div className="bg-white rounded-xl overflow-hidden shadow-sm divide-y divide-gray-100">
          {portfolio.holdings.map((holding) => (
            <HoldingRow
              key={holding.id}
              holding={holding}
              onClick={() => onSelectStock(holding.stock)}
            />
          ))}
        </div>
      </div>

      {/* Insights */}
      {portfolio.topPerformer && (
        <div className="bg-white rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2 text-primary">
            <Lightbulb size={18} />
            <h4 className="font-bold text-[13px] uppercase tracking-wide">Insights</h4>
          </div>
          <p className="text-[15px] leading-snug">
            Your {portfolio.topPerformer.id} position has outperformed the market by{" "}
            <span className="text-growth font-bold">
              {Math.round(portfolio.topPerformer.gainLossPercent)}%
            </span>
            . Consider rebalancing if tech exposure exceeds 30%.
          </p>
        </div>
      )}

      {/* Tax Statement */}
      <div className="bg-white rounded-xl p-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gray-50 rounded-lg flex items-center justify-center">
            <FileText size={20} className="text-label-secondary" />
          </div>
          <div>
            <p className="text-[15px] font-bold">Q3 2023 Tax Statement</p>
            <p className="text-[12px] text-label-secondary">Ready to download</p>
          </div>
        </div>
        <button className="text-primary">
          <Download size={22} />
        </button>
      </div>
    </div>
  );
}
