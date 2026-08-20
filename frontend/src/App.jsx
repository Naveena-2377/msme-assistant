import { useState } from "react";
import ApprovalQueue from "./components/ApprovalQueue";
import DecisionHistory from "./components/DecisionHistory";
import Products from "./pages/Products";
import Invoices from "./pages/Invoices";
import Dashboard from "./pages/Dashboard";
import Suppliers from "./pages/Suppliers";
import ProductHistory from "./pages/ProductHistory";

const TABS = {
  dashboard: { label: "Dashboard", component: Dashboard },
  products: { label: "Products", component: Products },
  invoices: { label: "Invoices", component: Invoices },
  suppliers: { label: "Suppliers", component: Suppliers },
  approvals: { label: "Approval Queue", component: ApprovalQueue },
  history: { label: "Decision History", component: DecisionHistory },
};

/** Simple interlocking-loop mark — the "twin" in MSME Assistant. */
function Logomark() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="11" cy="14" r="8" stroke="#FAF9F6" strokeWidth="2" />
      <circle cx="17" cy="14" r="8" stroke="#C97A2B" strokeWidth="2" />
    </svg>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [selectedProductId, setSelectedProductId] = useState(null);
  const ActiveComponent = TABS[activeTab].component;

  const selectTab = (key) => {
    setActiveTab(key);
    setSelectedProductId(null);
  };

  return (
    <div className="min-h-screen flex bg-paper text-[#2B2A28]">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-ink text-paper flex flex-col">
        <div className="flex items-center gap-2 px-5 py-6">
          <Logomark />
          <span className="font-display text-xl font-semibold tracking-tight">MSME Assistant</span>
        </div>
        <nav className="flex-1 px-2 space-y-1">
          {Object.entries(TABS).map(([key, tab]) => {
            const isActive = activeTab === key && !selectedProductId;
            return (
              <button
                key={key}
                onClick={() => selectTab(key)}
                className={`w-full flex items-center gap-2.5 text-left px-3 py-2 rounded text-sm transition-colors ${
                  isActive
                    ? "bg-ink-light text-white font-medium"
                    : "text-paper/70 hover:bg-ink-light/60 hover:text-white"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    isActive ? "bg-clay" : "bg-transparent"
                  }`}
                />
                {tab.label}
              </button>
            );
          })}
        </nav>
        <div className="px-5 py-4 text-xs text-paper/40 border-t border-ink-light">
          MSME digital twin — predict, simulate, validate, approve
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0">
        <header className="px-8 py-5 border-b border-black/5 bg-white/60">
          <h1 className="font-display text-2xl font-semibold text-ink-dark">
            {selectedProductId ? "Product History" : TABS[activeTab].label}
          </h1>
        </header>
        <div className="px-8 pb-10">
          {selectedProductId ? (
            <ProductHistory
              productId={selectedProductId}
              onBack={() => setSelectedProductId(null)}
            />
          ) : activeTab === "products" ? (
            <Products onSelectProduct={setSelectedProductId} />
          ) : (
            <ActiveComponent />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
