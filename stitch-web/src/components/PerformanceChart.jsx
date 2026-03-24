const PERIODS = ["1D", "1W", "1M", "1Y", "All"];

export default function PerformanceChart({
  data,
  color = "#800000",
  period = "1M",
  onPeriodChange,
  loading = false,
  periods = PERIODS,
}) {
  const hasData = data && data.length >= 2;

  const renderChart = () => {
    if (!hasData) return null;

    const min = Math.min(...data) * 0.998;
    const max = Math.max(...data) * 1.002;
    const range = max - min || 1;
    const w = 1000;
    const h = 300;
    const stepX = w / (data.length - 1);

    const linePoints = data
      .map((v, i) => `${i * stepX},${h - ((v - min) / range) * h}`)
      .join(" ");

    const lastX = (data.length - 1) * stepX;
    const lastY = h - ((data[data.length - 1] - min) / range) * h;
    const areaPoints = `${linePoints} ${w},${h} 0,${h}`;

    return (
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-[180px]">
        <defs>
          <linearGradient id="chartGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.2" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={areaPoints} fill="url(#chartGrad)" />
        <polyline
          points={linePoints}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx={lastX} cy={lastY} r="5" fill={color} />
      </svg>
    );
  };

  return (
    <div className="bg-surface rounded-2xl overflow-hidden">
      <div className="px-2 pt-4 pb-1 min-h-[180px] flex items-center justify-center">
        {loading && !hasData ? (
          <div className="text-label-secondary text-sm animate-pulse">Loading chart...</div>
        ) : hasData ? (
          renderChart()
        ) : (
          <div className="text-label-secondary text-sm">No chart data available</div>
        )}
      </div>

      <div className="flex mx-4 mb-3 p-0.5 bg-gray-200/50 rounded-lg">
        {periods.map((p) => (
          <button
            key={p}
            onClick={() => onPeriodChange?.(p)}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
              period === p
                ? "bg-white shadow-sm font-bold text-black"
                : "text-gray-500"
            }`}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
