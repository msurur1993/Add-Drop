import { Bell, TrendingUp, TrendingDown, Wallet, ArrowUpRight } from "lucide-react";
import PerformanceChart from "../components/PerformanceChart";
import WatchlistRow from "../components/WatchlistRow";
import { usePortfolioChart } from "../hooks/useChartData";
import { formatCurrency, formatPercent, formatGainLoss, changeColor } from "../data/helpers";

export default function Dashboard({ portfolio, onSelectStock }) {
  const { chartData, period, setPeriod, loading } = usePortfolioChart(portfolio.holdings, "1M");

  return (
    <div className="pb-6 space-y-7 px-4">
      {/* Nav */}
      <div className="flex items-center justify-between pt-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-surface flex items-center justify-center">
            <span className="text-label-secondary text-sm">👤</span>
          </div>
          <span className="text-lg font-bold tracking-tight">The Precision Ledger</span>
        </div>
        <button className="text-primary p-1">
          <Bell size={22} />
        </button>
      </div>

      {/* Hero */}
      <div>
        <p className="text-[13px] font-semibold text-label-secondary uppercase tracking-tight">
          Total Account Value
        </p>
        <h1 className="text-4xl font-extrabold tracking-tight mt-1">
          {formatCurrency(portfolio.totalAccountValue)}
        </h1>
        <div className="flex items-center gap-2 mt-1">
          <span className={`flex items-center font-bold text-[15px] gap-0.5 ${changeColor(portfolio.dailyGain)}`}>
            {portfolio.dailyGain >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {formatPercent(portfolio.dailyGainPercent)}
          </span>
          <span className="text-label-secondary text-[15px]">
            {formatGainLoss(portfolio.dailyGain)} today
          </span>
        </div>
      </div>

      {/* Chart */}
      <PerformanceChart
        data={chartData}
        period={period}
        onPeriodChange={setPeriod}
        loading={loading}
      />

      {/* Bento Grid */}
      <div className="grid grid-cols-2 gap-3">
        {/* Cash */}
        <div className="bg-surface p-4 rounded-xl flex flex-col justify-between aspect-square">
          <div className="flex justify-between items-start">
            <Wallet size={22} className="text-primary" />
            <span className="text-[10px] font-bold uppercase tracking-tight text-label-secondary">
              Liquid Cash
            </span>
          </div>
          <div>
            <h3 className="text-[22px] font-bold tracking-tight">
              {formatCurrency(portfolio.cash)}
            </h3>
            <p className="text-[11px] text-label-secondary font-medium">Available</p>
          </div>
        </div>

        {/* Top Performer */}
        {portfolio.topPerformer && (
          <div
            className="bg-primary p-4 rounded-xl flex flex-col justify-between aspect-square cursor-pointer"
            onClick={() => onSelectStock(portfolio.topPerformer.stock)}
          >
            <div>
              <span className="text-[10px] font-bold uppercase tracking-tight text-white/70">
                Top Performer
              </span>
              <h3 className="text-[22px] font-bold text-white mt-1">
                {portfolio.topPerformer.id}
              </h3>
              <p className="text-[11px] text-white/70">
                {formatPercent(portfolio.topPerformer.gainLossPercent)} Total
              </p>
            </div>
            <button className="w-full bg-white/20 text-white text-[12px] font-bold py-2.5 rounded-lg active:bg-white/30 transition-colors">
              Details
            </button>
          </div>
        )}
      </div>

      {/* Watchlist */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-xl font-bold tracking-tight">Watchlist</h2>
          <button className="text-primary text-[15px] font-medium">Edit</button>
        </div>
        <div className="bg-white border border-gray-100 rounded-xl overflow-hidden divide-y divide-gray-100">
          {portfolio.watchlist.map((stock) => (
            <WatchlistRow
              key={stock.id}
              stock={stock}
              onClick={() => onSelectStock(stock)}
            />
          ))}
        </div>
      </div>

      {/* Market Intelligence */}
      <div>
        <h2 className="text-xl font-bold tracking-tight mb-4">Market Intelligence</h2>
        <div className="flex gap-4 items-start">
          <div className="w-20 h-20 shrink-0 rounded-xl bg-surface flex items-center justify-center border border-gray-100">
            <ArrowUpRight size={28} className="text-label-secondary" />
          </div>
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase text-primary tracking-tight">
              Bullish Signal
            </span>
            <h4 className="font-bold text-[15px] leading-snug">
              Tech sector shows resilience amid shifting interest rates.
            </h4>
            <p className="text-[12px] text-label-secondary">2h ago · 4 min read</p>
          </div>
        </div>

        <div className="mt-4 bg-surface p-4 rounded-xl border-l-4 border-primary">
          <p className="text-[11px] font-bold text-primary uppercase tracking-tight mb-1">
            Editor&apos;s Pick
          </p>
          <p className="text-[14px] font-medium italic text-gray-600">
            &quot;Market precision is not about guessing the future, but managing the risk of the
            present.&quot;
          </p>
        </div>
      </div>
    </div>
  );
}
