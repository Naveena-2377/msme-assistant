import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

function StatCard({ label, value, tone = "default" }) {
  const toneClasses = {
    default: "bg-white border-gray-200 text-gray-900",
    warning: "bg-amber-50 border-amber-200 text-amber-900",
    danger: "bg-red-50 border-red-200 text-red-900",
    good: "bg-green-50 border-green-200 text-green-900",
  };
  return (
    <div className={`border rounded-lg p-4 ${toneClasses[tone]}`}>
      <p className="text-xs uppercase tracking-wide opacity-70">{label}</p>
      <p className="text-2xl font-semibold font-mono mt-1">{value}</p>
    </div>
  );
}

/**
 * Dashboard — a single-glance summary of business health. Usually
 * the first screen a real owner would want, pulling together numbers
 * from Products, Invoices, and the Approval Queue instead of making
 * them check each page separately.
 */
function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/dashboard/`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError("Could not reach the backend. Is uvicorn running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  return (
    <div className="mt-4 space-y-4">
      <div className="flex justify-end items-center">
        <button onClick={fetchDashboard} className="text-sm text-ink hover:underline">
          Refresh
        </button>
      </div>

      {error && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
          {error}
        </div>
      )}
      {loading && <p className="text-gray-500">Loading...</p>}

      {!loading && !error && data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Cash Balance" value={`₹${data.current_cash.toLocaleString()}`} />
          <StatCard
            label="Products Below Threshold"
            value={data.products_below_threshold}
            tone={data.products_below_threshold > 0 ? "warning" : "good"}
          />
          <StatCard
            label="Products at High Risk"
            value={data.products_high_risk}
            tone={data.products_high_risk > 0 ? "danger" : "good"}
          />
          <StatCard
            label="Pending Approvals"
            value={data.pending_approvals}
            tone={data.pending_approvals > 0 ? "warning" : "good"}
          />
          <StatCard
            label="Unpaid Invoices"
            value={data.unpaid_invoices_count}
          />
          <StatCard
            label="Overdue Invoices"
            value={data.overdue_invoices_count}
            tone={data.overdue_invoices_count > 0 ? "danger" : "good"}
          />
          <StatCard
            label="Unpaid Total"
            value={`₹${data.unpaid_invoices_total.toLocaleString()}`}
          />
          <StatCard label="Total Products" value={data.total_products} />
        </div>
      )}
    </div>
  );
}

export default Dashboard;
