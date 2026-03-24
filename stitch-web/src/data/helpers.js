export function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value) {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function formatGainLoss(value) {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${formatCurrency(value)}`;
}

export function changeColor(value) {
  return value >= 0 ? "text-growth" : "text-loss";
}

export function changeBg(value) {
  return value >= 0 ? "bg-growth" : "bg-loss";
}

const ICON_COLORS = {
  SPUS: { bg: "bg-brand-maroon/10", text: "text-brand-maroon" },
  NVDA: { bg: "bg-growth/10", text: "text-growth" },
  "SPDR GLD": { bg: "bg-orange-400/10", text: "text-orange-500" },
  CRWV: { bg: "bg-maroon-light/10", text: "text-maroon-light" },
};

export function stockIconColors(ticker) {
  return ICON_COLORS[ticker] || { bg: "bg-gray-100", text: "text-gray-500" };
}

export const ALLOC_COLORS = ["bg-brand-maroon", "bg-growth", "bg-orange-400", "bg-maroon-light", "bg-gray-400"];
export const ALLOC_DOT_COLORS = ["bg-brand-maroon", "bg-growth", "bg-orange-400", "bg-maroon-light", "bg-gray-400"];
