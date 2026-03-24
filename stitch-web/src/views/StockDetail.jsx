import { ChevronLeft, MoreHorizontal, Star, ArrowLeftRight, ArrowUp, ArrowDown, Cpu, Brain } from "lucide-react";
import { formatCurrency, formatPercent, changeColor } from "../data/helpers";
import { useChartData } from "../hooks/useChartData";

const PERIODS = ["1D", "1W", "1M", "3M", "1Y", "ALL"];

export default function StockDetail({ stock, onBack, onTrade }) {
  const { chartData, period, setPeriod, loading } = useChartData(stock.id, "1D");

  const stats = [
    ["Market Cap", stock.marketCap],
    ["P/E Ratio", stock.peRatio.toFixed(2)],
    ["Div. Yield", `${stock.divYield.toFixed(2)}%`],
    ["Avg. Volume", stock.avgVolume],
    ["52W High", stock.high52Week.toFixed(2)],
  ];

  // Chart rendering
  const renderChart = () => {
    if (!chartData || chartData.length < 2) {
      return (
        <div className="w-full h-[200px] flex items-center justify-center text-label-secondary text-sm">
          {loading ? <span className="animate-pulse">Loading chart...</span> : "No data available"}
        </div>
      );
    }

    const w = 1000, h = 300;
    const min = Math.min(...chartData) * 0.999;
    const max = Math.max(...chartData) * 1.001;
    const range = max - min || 1;
    const stepX = w / (chartData.length - 1);
    const linePoints = chartData.map((v, i) => `${i * stepX},${h - ((v - min) / range) * h}`).join(" ");
    const areaPoints = `${linePoints} ${w},${h} 0,${h}`;

    const isUp = chartData[chartData.length - 1] >= chartData[0];
    const strokeColor = isUp ? "#34C759" : "#FF3B30";

    return (
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-[200px]">
        <defs>
          <linearGradient id="detailGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.1" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={areaPoints} fill="url(#detailGrad)" />
        <polyline points={linePoints} fill="none" stroke={strokeColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  };

  // Time labels based on period
  const timeLabels = {
    "1D": ["09:30 AM", "04:00 PM"],
    "1W": ["Mon", "Fri"],
    "1M": ["1 month ago", "Today"],
    "3M": ["3 months ago", "Today"],
    "1Y": ["1 year ago", "Today"],
    ALL: ["Inception", "Today"],
  };
  const [leftLabel, rightLabel] = timeLabels[period] || ["", ""];

  return (
    <div className="pb-28">
      {/* Nav bar */}
      <div className="sticky top-0 z-20 bg-white/80 backdrop-blur-md border-b border-gray-100 px-4 py-2.5 flex items-center justify-between">
        <button onClick={onBack} className="flex items-center text-primary gap-0.5">
          <ChevronLeft size={24} />
          <span className="text-[17px]">Back</span>
        </button>
        <span className="text-[17px] font-semibold absolute left-1/2 -translate-x-1/2">
          {stock.id}
        </span>
        <button className="text-primary">
          <MoreHorizontal size={22} />
        </button>
      </div>

      {/* Header */}
      <div className="px-4 py-5 flex justify-between items-start">
        <div>
          <h1 className="text-[30px] font-bold tracking-tight leading-tight">{stock.name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[13px] font-medium text-label-secondary uppercase">
              {stock.exchange}: {stock.id}
            </span>
            <span className={`flex items-center gap-0.5 text-[13px] font-semibold ${changeColor(stock.dailyChange)}`}>
              {stock.dailyChange >= 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
              {formatPercent(stock.dailyChange)}
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[30px] font-bold tracking-tight">{formatCurrency(stock.currentPrice)}</div>
          {stock.afterHoursPrice && (
            <div className="text-[12px] font-medium text-label-secondary">
              After Hours: {formatCurrency(stock.afterHoursPrice)}
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="mx-4 bg-white border border-gray-100 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-gray-50">
          <div className="bg-surface p-0.5 rounded-lg flex">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`flex-1 py-1 text-[13px] rounded-md transition-all ${
                  period === p ? "bg-white shadow-sm font-semibold" : "font-medium text-label-secondary"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
        <div className="p-6">
          {renderChart()}
          <div className="flex justify-between mt-2">
            <span className="text-[11px] font-medium text-label-secondary uppercase">{leftLabel}</span>
            <span className="text-[11px] font-medium text-label-secondary uppercase">{rightLabel}</span>
          </div>
        </div>
      </div>

      {/* Key Stats */}
      <div className="mt-6">
        <h3 className="text-[13px] font-medium text-label-secondary uppercase tracking-wide px-5 mb-2">
          Key Statistics
        </h3>
        <div className="border-y border-gray-200 divide-y divide-gray-200 bg-white">
          {stats.map(([label, value]) => (
            <div key={label} className="flex justify-between items-center py-2.5 px-4">
              <span className="text-[17px]">{label}</span>
              <span className="text-[17px] font-medium">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Analyst Consensus */}
      <div className="mx-4 mt-8 bg-primary text-white rounded-2xl p-5 shadow-lg">
        <h3 className="text-[11px] font-bold uppercase tracking-widest opacity-70 mb-1">
          Analyst Consensus
        </h3>
        <div className="flex items-end gap-3 mb-2">
          <div className="text-[28px] font-bold">Strong Buy</div>
          <div className="bg-white/20 px-2 py-0.5 rounded text-[11px] font-bold mb-1.5 uppercase">
            92% Buy
          </div>
        </div>
        <p className="text-[13px] opacity-80">
          Based on 48 ratings in the last 90 days. Average price target: $145.00 (+12.8%)
        </p>
      </div>

      {/* News */}
      <div className="px-4 mt-8 space-y-4">
        <h2 className="text-[22px] font-bold">Market Intel</h2>
        {[
          { tag: "EARNINGS IMPACT", color: "text-primary", title: "NVIDIA's Data Center revenue exceeds analyst forecasts as AI demand surges.", source: "2h ago · Financial Times", Icon: Cpu },
          { tag: "COMPETITOR WATCH", color: "text-label-secondary", title: "How Blackwell architecture maintains lead over AMD.", source: "5h ago · Reuters", Icon: Brain },
        ].map((news) => (
          <div key={news.tag} className="flex gap-3 bg-white rounded-xl p-3 border border-gray-100">
            <div className="w-24 h-24 rounded-lg bg-surface flex items-center justify-center shrink-0">
              <news.Icon size={28} className="text-label-secondary" />
            </div>
            <div className="flex flex-col justify-between py-0.5">
              <div>
                <span className={`text-[11px] font-bold uppercase tracking-wider ${news.color}`}>
                  {news.tag}
                </span>
                <h4 className="text-[15px] font-semibold leading-tight mt-1 line-clamp-2">{news.title}</h4>
              </div>
              <p className="text-[11px] text-label-secondary">{news.source}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Action Bar */}
      <div className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[430px] bg-white/90 backdrop-blur-xl border-t border-gray-200 z-30 px-5 pt-3 pb-6">
        <div className="flex items-center gap-3">
          <button className="w-12 h-12 flex items-center justify-center rounded-xl bg-surface text-primary">
            <Star size={22} />
          </button>
          <button
            onClick={() => onTrade(stock)}
            className="flex-1 bg-primary text-white h-12 rounded-xl font-semibold text-[17px] active:brightness-90 transition-all flex items-center justify-center gap-2"
          >
            Trade {stock.id}
            <ArrowLeftRight size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
