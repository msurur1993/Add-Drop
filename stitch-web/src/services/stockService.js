// Yahoo Finance ticker mapping
const TICKER_MAP = {
  SPUS: "SPUS",
  "SPDR GLD": "GLD",
  NVDA: "NVDA",
  CRWV: "CRWV",
};

// Period -> Yahoo Finance params
const PERIOD_CONFIG = {
  "1D": { range: "1d", interval: "5m" },
  "1W": { range: "5d", interval: "15m" },
  "1M": { range: "1mo", interval: "1d" },
  "3M": { range: "3mo", interval: "1d" },
  "1Y": { range: "1y", interval: "1wk" },
  All: { range: "max", interval: "1mo" },
  ALL: { range: "max", interval: "1mo" },
};

export function getYahooTicker(appTicker) {
  return TICKER_MAP[appTicker] || appTicker;
}

// Simple in-memory cache to avoid duplicate requests
const cache = new Map();
const CACHE_TTL = 120_000; // 2 minutes

function getCached(key) {
  const entry = cache.get(key);
  if (entry && Date.now() - entry.ts < CACHE_TTL) return entry.data;
  return null;
}

function setCache(key, data) {
  cache.set(key, { data, ts: Date.now() });
}

// Sequential fetch with delay to avoid rate limiting
async function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// Retry wrapper
async function fetchWithRetry(url, retries = 2) {
  for (let i = 0; i <= retries; i++) {
    try {
      const res = await fetch(url);
      if (res.status === 429) {
        if (i < retries) {
          await delay(2000 * (i + 1)); // backoff: 2s, 4s
          continue;
        }
        throw new Error("Rate limited");
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      if (i === retries) throw err;
      await delay(500);
    }
  }
}

/**
 * Fetch chart data for a stock + period from Yahoo Finance
 */
export async function fetchChartData(appTicker, period = "1D") {
  const ticker = getYahooTicker(appTicker);
  const config = PERIOD_CONFIG[period] || PERIOD_CONFIG["1D"];
  const cacheKey = `chart_${ticker}_${period}`;

  const cached = getCached(cacheKey);
  if (cached) return cached;

  try {
    const data = await fetchWithRetry(
      `/yf/v8/finance/chart/${encodeURIComponent(ticker)}?range=${config.range}&interval=${config.interval}`
    );

    const result = data.chart?.result?.[0];
    if (!result) return null;

    const timestamps = result.timestamp || [];
    const closes = result.indicators?.quote?.[0]?.close || [];

    const points = [];
    for (let i = 0; i < timestamps.length; i++) {
      if (closes[i] != null) {
        points.push({ time: timestamps[i] * 1000, value: closes[i] });
      }
    }

    setCache(cacheKey, points);
    return points;
  } catch (err) {
    console.warn(`Chart fetch failed for ${ticker} (${period}):`, err.message);
    return null;
  }
}

/**
 * Fetch real-time quote for a stock
 */
export async function fetchQuote(appTicker) {
  const ticker = getYahooTicker(appTicker);
  const cacheKey = `quote_${ticker}`;

  const cached = getCached(cacheKey);
  if (cached) return cached;

  try {
    const data = await fetchWithRetry(
      `/yf/v8/finance/chart/${encodeURIComponent(ticker)}?range=1d&interval=1d`
    );

    const result = data.chart?.result?.[0];
    if (!result) return null;

    const meta = result.meta;
    const currentPrice = meta.regularMarketPrice;
    const previousClose = meta.chartPreviousClose || meta.previousClose;
    const dailyChange = previousClose
      ? ((currentPrice - previousClose) / previousClose) * 100
      : 0;

    const quote = { currentPrice, previousClose, dailyChange };
    setCache(cacheKey, quote);
    return quote;
  } catch (err) {
    console.warn(`Quote fetch failed for ${ticker}:`, err.message);
    return null;
  }
}

/**
 * Fetch quotes for all stocks - sequentially to avoid rate limiting
 */
export async function fetchAllQuotes(appTickers) {
  const quotes = {};
  for (const ticker of appTickers) {
    const quote = await fetchQuote(ticker);
    if (quote) quotes[ticker] = quote;
    await delay(200); // 200ms between requests
  }
  return quotes;
}

/**
 * Fetch sparkline (5-day) for a stock
 */
export async function fetchSparkline(appTicker) {
  const points = await fetchChartData(appTicker, "1W");
  if (!points || points.length === 0) return null;

  // Downsample to ~20 points for sparkline
  const step = Math.max(1, Math.floor(points.length / 20));
  return points.filter((_, i) => i % step === 0).map((p) => p.value);
}

/**
 * Fetch all sparklines sequentially
 */
export async function fetchAllSparklines(appTickers) {
  const results = [];
  for (const ticker of appTickers) {
    const sparkline = await fetchSparkline(ticker);
    results.push(sparkline);
    await delay(200);
  }
  return results;
}
