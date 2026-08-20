import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const STATUS_COLORS = {
  approved: "bg-green-100 text-green-800",
  pending: "bg-yellow-100 text-yellow-800",
  rejected: "bg-red-100 text-red-800",
};

/**
 * Decision History — the "business memory" replay view (Dev Step 11).
 * Shows every decision ever made, regardless of outcome, filterable
 * by approval status. This is what makes the system's behavior
 * auditable instead of a black box.
 */
function DecisionHistory() {
  const [decisions, setDecisions] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDecisions = async (status, actionType) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (status) params.set("status", status);
      if (actionType) params.set("action_type", actionType);
      const url = `${API_BASE}/decisions/${params.toString() ? `?${params}` : ""}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setDecisions(data);
    } catch (err) {
      setError("Could not reach the backend. Is uvicorn running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisions(statusFilter, typeFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, typeFilter]);

  return (
    <div className="mt-4 space-y-4">
      <div className="flex justify-end items-center">
        <div className="flex gap-2">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="">All types</option>
            <option value="reorder">Reorders</option>
            <option value="sale">Sales</option>
            <option value="stock_adjustment">Stock Adjustments</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="">All statuses</option>
            <option value="approved">Approved</option>
            <option value="pending">Pending</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
          {error}
        </div>
      )}
      {loading && <p className="text-gray-500">Loading...</p>}
      {!loading && decisions.length === 0 && (
        <p className="text-gray-500">No decisions match this filter.</p>
      )}

      <div className="space-y-2">
        {decisions.map((decision) => {
          const outcome = JSON.parse(decision.simulated_outcome);
          return (
            <div key={decision.decision_id} className="border rounded-lg p-3 bg-white text-sm">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-medium">
                    #{decision.decision_id} — {renderSummary(decision.action_type, outcome)}
                  </p>
                  <p className="text-gray-600">{renderDetail(decision.action_type, outcome)}</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <span className="text-xs font-medium bg-gray-100 text-gray-700 px-2 py-1 rounded">
                    {decision.rule_check_result}
                  </span>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded ${
                      STATUS_COLORS[decision.approval_status] || "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {decision.approval_status}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function renderSummary(actionType, outcome) {
  switch (actionType) {
    case "reorder":
      return `${outcome.product_name}: reorder ${outcome.quantity} units`;
    case "sale":
      return `${outcome.product_name}: sold ${outcome.quantity_sold} units`;
    case "stock_adjustment":
      return `${outcome.product_name}: stock adjusted`;
    default:
      return actionType;
  }
}

function renderDetail(actionType, outcome) {
  switch (actionType) {
    case "reorder":
      return `Cash: ${outcome.current_cash} → ${outcome.projected_cash} | Stock: ${outcome.current_stock} → ${outcome.projected_stock} | Risk: ${outcome.stockout_risk_before} → ${outcome.stockout_risk_after}`;
    case "sale":
      return `Revenue: ₹${outcome.revenue} at ₹${outcome.unit_price}/unit | New stock: ${outcome.new_stock} | New cash: ${outcome.new_cash_balance}`;
    case "stock_adjustment":
      return `Stock: ${outcome.old_stock} → ${outcome.new_stock}${outcome.reason ? ` | Reason: ${outcome.reason}` : ""}`;
    default:
      return "";
  }
}

export default DecisionHistory;
