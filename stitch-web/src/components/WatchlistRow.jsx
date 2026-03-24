import StockIcon from "./StockIcon";
import Sparkline from "./Sparkline";
import { formatCurrency, formatPercent, changeColor } from "../data/helpers";

export default function WatchlistRow({ stock, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-4 py-3 active:bg-gray-50 transition-colors text-left"
    >
      <StockIcon ticker={stock.id} />
      <div className="min-w-0 flex-1">
        <p className="font-bold text-[16px]">{stock.id}</p>
        <p className="text-[13px] text-label-secondary truncate">{stock.name}</p>
      </div>
      <Sparkline data={stock.sparkline} positive={stock.dailyChange >= 0} />
      <div className="text-right">
        <p className="font-bold text-[16px]">{formatCurrency(stock.currentPrice)}</p>
        <p className={`text-[13px] font-bold ${changeColor(stock.dailyChange)}`}>
          {formatPercent(stock.dailyChange)}
        </p>
      </div>
    </button>
  );
}
