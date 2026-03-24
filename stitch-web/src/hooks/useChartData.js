import { useState, useEffect, useRef } from "react";
import { fetchChartData } from "../services/stockService";

/**
 * Hook to fetch chart data for a single ticker with period switching.
 */
export function useChartData(ticker, initialPeriod = "1D") {
  const [period, setPeriod] = useState(initialPeriod);
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const cacheRef = useRef({});

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;

    const cacheKey = `${ticker}_${period}`;
    const cached = cacheRef.current[cacheKey];
    if (cached) {
      setChartData(cached);
      setLoading(false);
      return;
    }

    setLoading(true);

    fetchChartData(ticker, period).then((points) => {
      if (cancelled) return;
      setLoading(false);
      if (points && points.length > 0) {
        const values = points.map((p) => p.value);
        cacheRef.current[cacheKey] = values;
        setChartData(values);
      }
    });

    return () => { cancelled = true; };
  }, [ticker, period]);

  return { chartData, period, setPeriod, loading };
}

/**
 * Hook to fetch a combined portfolio chart (sequential to avoid rate limiting).
 */
export function usePortfolioChart(holdings, initialPeriod = "1M") {
  const [period, setPeriod] = useState(initialPeriod);
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const cacheRef = useRef({});

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!holdings || holdings.length === 0) return;

      const cacheKey = `portfolio_${period}`;
      const cached = cacheRef.current[cacheKey];
      if (cached) {
        setChartData(cached);
        setLoading(false);
        return;
      }

      setLoading(true);

      // Fetch charts sequentially to avoid rate limiting
      const charts = [];
      for (const h of holdings) {
        const data = await fetchChartData(h.id, period);
        charts.push(data);
        if (cancelled) return;
        // Small delay between requests
        await new Promise((r) => setTimeout(r, 150));
      }

      if (cancelled) return;

      const validCharts = charts
        .map((c, i) => ({ data: c || [], holding: holdings[i] }))
        .filter((c) => c.data.length > 0);

      if (validCharts.length === 0) {
        setLoading(false);
        return;
      }

      const maxLen = Math.max(...validCharts.map((c) => c.data.length));

      const combined = [];
      for (let i = 0; i < maxLen; i++) {
        let totalValue = 0;
        for (const { data, holding } of validCharts) {
          const idx = Math.min(Math.floor((i / maxLen) * data.length), data.length - 1);
          totalValue += data[idx].value * holding.shares;
        }
        combined.push(totalValue);
      }

      cacheRef.current[cacheKey] = combined;
      setChartData(combined);
      setLoading(false);
    }

    load();
    return () => { cancelled = true; };
  }, [holdings, period]);

  return { chartData, period, setPeriod, loading };
}
