import { useState, useCallback, useMemo, useEffect } from "react";
import { stocks as defaultStocks, initialHoldings, initialCash } from "../data/stocks";
import { fetchAllQuotes, fetchAllSparklines } from "../services/stockService";

export function usePortfolio() {
  const [cash, setCash] = useState(initialCash);
  const [holdings, setHoldings] = useState(initialHoldings);
  const [watchlist, setWatchlist] = useState(defaultStocks);
  const [loading, setLoading] = useState(true);

  // Fetch real prices on mount and every 60s
  useEffect(() => {
    let cancelled = false;

    async function loadRealData() {
      const tickers = defaultStocks.map((s) => s.id);
      const quotes = await fetchAllQuotes(tickers);
      const sparklines = await fetchAllSparklines(tickers);

      if (cancelled) return;

      setWatchlist((prev) =>
        prev.map((stock, i) => {
          const quote = quotes[stock.id];
          const sparkline = sparklines[i];
          return {
            ...stock,
            currentPrice: quote?.currentPrice ?? stock.currentPrice,
            dailyChange: quote?.dailyChange ?? stock.dailyChange,
            sparkline: sparkline ?? stock.sparkline,
          };
        })
      );
      setLoading(false);
    }

    loadRealData();
    const interval = setInterval(loadRealData, 60000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const getStock = useCallback((id) => watchlist.find((s) => s.id === id), [watchlist]);

  const holdingsWithData = useMemo(
    () =>
      holdings.map((h) => {
        const stock = getStock(h.id) || defaultStocks.find((s) => s.id === h.id);
        const currentValue = h.shares * stock.currentPrice;
        const totalCost = h.shares * h.averageCost;
        const gainLoss = currentValue - totalCost;
        const gainLossPercent = totalCost > 0 ? (gainLoss / totalCost) * 100 : 0;
        return { ...h, stock, currentValue, totalCost, gainLoss, gainLossPercent };
      }),
    [holdings, getStock]
  );

  const totalInvested = holdingsWithData.reduce((sum, h) => sum + h.currentValue, 0);
  const totalAccountValue = cash + totalInvested;
  const totalGainLoss = holdingsWithData.reduce((sum, h) => sum + h.gainLoss, 0);
  const totalCost = holdingsWithData.reduce((sum, h) => sum + h.totalCost, 0);
  const totalGainLossPercent = totalCost > 0 ? (totalGainLoss / totalCost) * 100 : 0;

  const allocations = holdingsWithData
    .map((h) => ({
      ticker: h.id,
      percent: totalInvested > 0 ? (h.currentValue / totalInvested) * 100 : 0,
    }))
    .sort((a, b) => b.percent - a.percent);

  const topPerformer = holdingsWithData.reduce(
    (best, h) => (h.gainLossPercent > (best?.gainLossPercent ?? -Infinity) ? h : best),
    null
  );

  // Daily gain based on daily change of each holding
  const dailyGain = holdingsWithData.reduce((sum, h) => {
    const prevPrice = h.stock.currentPrice / (1 + h.stock.dailyChange / 100);
    return sum + (h.stock.currentPrice - prevPrice) * h.shares;
  }, 0);
  const dailyGainPercent =
    totalAccountValue > 0 ? (dailyGain / (totalAccountValue - dailyGain)) * 100 : 0;

  const executeTrade = useCallback(
    (stockId, side, amount) => {
      const stock = watchlist.find((s) => s.id === stockId);
      if (!stock || amount <= 0) return false;
      const shares = amount / stock.currentPrice;

      if (side === "buy") {
        if (cash < amount) return false;
        setCash((c) => c - amount);
        setHoldings((prev) => {
          const idx = prev.findIndex((h) => h.id === stockId);
          if (idx >= 0) {
            const existing = prev[idx];
            const totalShares = existing.shares + shares;
            const totalCostVal = existing.shares * existing.averageCost + amount;
            return prev.map((h, i) =>
              i === idx
                ? { ...h, shares: totalShares, averageCost: totalCostVal / totalShares }
                : h
            );
          }
          return [...prev, { id: stockId, shares, averageCost: stock.currentPrice }];
        });
      } else {
        const holding = holdings.find((h) => h.id === stockId);
        if (!holding || holding.shares < shares) return false;
        setCash((c) => c + amount);
        setHoldings((prev) => {
          const remaining = holding.shares - shares;
          if (remaining < 0.0001) return prev.filter((h) => h.id !== stockId);
          return prev.map((h) => (h.id === stockId ? { ...h, shares: remaining } : h));
        });
      }
      return true;
    },
    [cash, holdings, watchlist]
  );

  return {
    cash,
    holdings: holdingsWithData,
    totalAccountValue,
    totalGainLoss,
    totalGainLossPercent,
    dailyGain,
    dailyGainPercent,
    allocations,
    topPerformer,
    executeTrade,
    watchlist,
    loading,
  };
}
