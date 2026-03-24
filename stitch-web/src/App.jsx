import { useState } from "react";
import { LayoutGrid, BarChart3, PieChart, Settings } from "lucide-react";
import { usePortfolio } from "./hooks/usePortfolio";
import Dashboard from "./views/Dashboard";
import StockDetail from "./views/StockDetail";
import Trade from "./views/Trade";
import Portfolio from "./views/Portfolio";

const TABS = [
  { id: "summary", label: "Summary", Icon: LayoutGrid },
  { id: "markets", label: "Markets", Icon: BarChart3 },
  { id: "portfolio", label: "Portfolio", Icon: PieChart },
  { id: "settings", label: "Settings", Icon: Settings },
];

export default function App() {
  const portfolio = usePortfolio();
  const [tab, setTab] = useState("summary");
  const [screen, setScreen] = useState({ type: "tab" }); // { type: "tab" } | { type: "detail", stock } | { type: "trade", stock }

  const handleSelectStock = (stock) => setScreen({ type: "detail", stock });
  const handleTrade = (stock) => setScreen({ type: "trade", stock });
  const handleBack = () => setScreen({ type: "tab" });

  const renderContent = () => {
    if (screen.type === "detail") {
      return (
        <StockDetail
          stock={screen.stock}
          onBack={handleBack}
          onTrade={handleTrade}
        />
      );
    }
    if (screen.type === "trade") {
      return (
        <Trade
          stock={screen.stock}
          cash={portfolio.cash}
          onExecute={portfolio.executeTrade}
          onBack={handleBack}
        />
      );
    }

    switch (tab) {
      case "summary":
        return <Dashboard portfolio={portfolio} onSelectStock={handleSelectStock} />;
      case "portfolio":
        return <Portfolio portfolio={portfolio} onSelectStock={handleSelectStock} />;
      case "markets":
        return (
          <div className="px-4 pt-4">
            <h1 className="text-2xl font-bold mb-4">Markets</h1>
            <div className="bg-white border border-gray-100 rounded-xl overflow-hidden divide-y divide-gray-100">
              {portfolio.watchlist.map((stock) => (
                <button
                  key={stock.id}
                  onClick={() => handleSelectStock(stock)}
                  className="w-full flex items-center justify-between px-4 py-4 active:bg-gray-50 transition-colors text-left"
                >
                  <div>
                    <p className="font-bold text-[16px]">{stock.id}</p>
                    <p className="text-[13px] text-label-secondary">{stock.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold">{new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(stock.currentPrice)}</p>
                    <p className={`text-[13px] font-bold ${stock.dailyChange >= 0 ? "text-growth" : "text-loss"}`}>
                      {stock.dailyChange >= 0 ? "+" : ""}{stock.dailyChange.toFixed(2)}%
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        );
      case "settings":
        return (
          <div className="px-4 pt-4 space-y-6">
            <h1 className="text-2xl font-bold">Settings</h1>
            <div className="bg-white rounded-xl overflow-hidden divide-y divide-gray-100">
              <div className="px-4 py-4 flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-primary flex items-center justify-center text-white text-lg">👤</div>
                <div>
                  <p className="font-bold">Paper Trader</p>
                  <p className="text-[13px] text-label-secondary">Virtual Account</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl overflow-hidden divide-y divide-gray-100">
              {["Notifications", "Appearance", "Currency"].map((item) => (
                <div key={item} className="px-4 py-3 text-[15px]">{item}</div>
              ))}
            </div>
            <div className="text-center text-[13px] text-label-secondary pt-4">
              The Precision Ledger v1.0
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="app-frame">
      {/* Content */}
      <div className={screen.type === "tab" ? "pb-20" : ""}>
        {renderContent()}
      </div>

      {/* Tab Bar - only show on tab screens */}
      {screen.type === "tab" && (
        <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[430px] bg-white/85 backdrop-blur-xl border-t border-gray-200 z-50 px-2 pt-1.5 pb-5">
          <div className="flex justify-around items-center h-12">
            {TABS.map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => { setTab(id); setScreen({ type: "tab" }); }}
                className={`flex flex-col items-center justify-center gap-0.5 ${
                  tab === id ? "text-primary" : "text-gray-400"
                }`}
              >
                <Icon size={24} strokeWidth={tab === id ? 2.5 : 1.5} />
                <span className="text-[10px] font-medium">{label}</span>
              </button>
            ))}
          </div>
        </nav>
      )}
    </div>
  );
}
