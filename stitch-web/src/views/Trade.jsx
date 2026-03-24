import { useState } from "react";
import { ChevronLeft, ChevronRight, Wallet, ChevronsUpDown } from "lucide-react";
import { formatCurrency, formatPercent, changeColor } from "../data/helpers";

export default function Trade({ stock, cash, onExecute, onBack }) {
  const [side, setSide] = useState("buy");
  const [amount, setAmount] = useState("");
  const [showSuccess, setShowSuccess] = useState(false);

  const amountNum = parseFloat(amount) || 0;
  const estimatedShares = stock.currentPrice > 0 ? amountNum / stock.currentPrice : 0;

  const handleConfirm = () => {
    if (amountNum <= 0) return;
    const success = onExecute(stock.id, side, amountNum);
    if (success) {
      setShowSuccess(true);
      setTimeout(() => {
        setShowSuccess(false);
        onBack();
      }, 1500);
    }
  };

  if (showSuccess) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh] px-8">
        <div className="w-20 h-20 rounded-full bg-growth/10 flex items-center justify-center mb-6">
          <span className="text-4xl">✓</span>
        </div>
        <h2 className="text-2xl font-bold mb-2">Trade Confirmed!</h2>
        <p className="text-label-secondary text-center">
          You {side === "buy" ? "bought" : "sold"} {estimatedShares.toFixed(4)} shares of{" "}
          {stock.id} for {formatCurrency(amountNum)}.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-surface min-h-screen pb-8">
      {/* Nav */}
      <div className="sticky top-0 z-20 bg-warm-surface/80 backdrop-blur-md border-b border-black/5 px-4 py-2.5 flex items-center justify-between">
        <button onClick={onBack} className="flex items-center text-primary gap-0.5">
          <ChevronLeft size={24} />
          <span className="text-[17px]">Back</span>
        </button>
        <span className="text-[17px] font-bold absolute left-1/2 -translate-x-1/2">Trade</span>
        <button className="text-primary text-[17px]">Details</button>
      </div>

      <div className="max-w-md mx-auto px-4 pt-6 space-y-4">
        {/* Stock header */}
        <div className="flex justify-between items-start px-1">
          <div>
            <h2 className="text-3xl font-extrabold tracking-tight text-brand-maroon">{stock.id}</h2>
            <p className="text-sm font-medium text-label-secondary">{stock.name}</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold">{formatCurrency(stock.currentPrice)}</p>
            <span className={`text-xs font-bold ${changeColor(stock.dailyChange)}`}>
              {formatPercent(stock.dailyChange)} today
            </span>
          </div>
        </div>

        {/* Buy/Sell toggle */}
        <div className="flex p-0.5 bg-[#efeff0] rounded-lg">
          {["buy", "sell"].map((s) => (
            <button
              key={s}
              onClick={() => setSide(s)}
              className={`flex-1 py-1.5 text-sm font-semibold rounded-[7px] capitalize transition-all ${
                side === s ? "bg-white shadow-sm text-black" : "text-label-secondary"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Amount input card */}
        <div className="bg-white p-4 rounded-xl shadow-sm border border-black/5">
          <div className="flex justify-between items-center mb-6">
            <label className="text-[15px] font-semibold">Amount</label>
            <div className="flex items-center text-primary font-semibold text-[15px] gap-0.5">
              <span>USD</span>
              <ChevronsUpDown size={16} />
            </div>
          </div>

          <div className="flex items-baseline justify-center py-4">
            <span className="text-4xl font-bold text-brand-maroon">$</span>
            <input
              type="number"
              inputMode="decimal"
              placeholder="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-48 bg-transparent border-none p-0 text-6xl font-bold text-center text-brand-maroon placeholder:text-gray-200 focus:outline-none focus:ring-0 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
          </div>

          <div className="mt-6 pt-4 border-t border-black/5 space-y-2">
            <div className="flex justify-between text-[14px]">
              <span className="text-label-secondary">Est. Shares</span>
              <span className="font-semibold">{estimatedShares.toFixed(4)}</span>
            </div>
            <div className="flex justify-between text-[14px]">
              <span className="text-label-secondary">Market Price</span>
              <span className="font-semibold">{formatCurrency(stock.currentPrice)}</span>
            </div>
          </div>
        </div>

        {/* Order details */}
        <div className="bg-white rounded-xl overflow-hidden border border-black/5">
          <div className="px-4 py-3 flex items-center justify-between border-b border-black/5">
            <div className="flex items-center gap-3">
              <Wallet size={20} className="text-primary" />
              <span className="text-[15px] font-medium">Buying Power</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="text-[15px] font-semibold">{formatCurrency(cash)}</span>
              <ChevronRight size={18} className="text-gray-300" />
            </div>
          </div>
          <div className="px-4 py-3 flex items-center justify-between border-b border-black/5">
            <span className="text-[15px] font-medium">Order Type</span>
            <div className="flex items-center gap-1 text-primary">
              <span className="text-[15px] font-semibold">Market</span>
              <ChevronRight size={18} />
            </div>
          </div>
          <div className="px-4 py-3 flex items-center justify-between">
            <span className="text-[15px] font-medium">Expires</span>
            <div className="flex items-center gap-1 text-primary">
              <span className="text-[15px] font-semibold">End of Day</span>
              <ChevronRight size={18} />
            </div>
          </div>
        </div>

        {/* Confirm */}
        <div className="pt-4">
          <button
            onClick={handleConfirm}
            disabled={amountNum <= 0}
            className={`w-full bg-brand-maroon text-white font-bold text-[17px] py-4 rounded-xl shadow-sm transition-opacity ${
              amountNum > 0 ? "active:opacity-70" : "opacity-50 cursor-not-allowed"
            }`}
          >
            Confirm Trade
          </button>
          <p className="text-center text-[12px] text-label-secondary mt-4 px-6 leading-relaxed">
            By confirming, you agree to the Execution Policy and the risks associated with
            simulated trading.
          </p>
        </div>
      </div>
    </div>
  );
}
