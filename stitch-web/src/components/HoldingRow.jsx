import StockIcon from "./StockIcon";
import { formatCurrency, formatGainLoss, changeColor } from "../data/helpers";

export default function HoldingRow({ holding, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 p-4 active:bg-gray-100 transition-colors text-left"
    >
      <StockIcon ticker={holding.id} />
      <div className="min-w-0 flex-1">
        <p className="font-bold text-[16px]">{holding.id}</p>
        <p className="text-[13px] text-label-secondary truncate">{holding.stock.name}</p>
      </div>
      <div className="text-right">
        <p className="font-bold text-[16px]">{formatCurrency(holding.currentValue)}</p>
        <p className={`text-[13px] font-medium ${changeColor(holding.gainLoss)}`}>
          {formatGainLoss(holding.gainLoss)} ({Math.abs(holding.gainLossPercent).toFixed(1)}%)
        </p>
      </div>
    </button>
  );
}
