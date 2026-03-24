import { stockIconColors } from "../data/helpers";

export default function StockIcon({ ticker, size = 40 }) {
  const { bg, text } = stockIconColors(ticker);
  const abbr = ticker.length <= 2 ? ticker : ticker.slice(0, 2).toUpperCase();

  return (
    <div
      className={`${bg} ${text} rounded-[10px] flex items-center justify-center font-bold text-sm shrink-0`}
      style={{ width: size, height: size }}
    >
      {abbr}
    </div>
  );
}
