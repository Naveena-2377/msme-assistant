import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const STATUS_COLORS = {
  approved: "bg-green-100 text-green-800",
  pending: "bg-yellow-100 text-yellow-800",
  rejected: "bg-red-100 text-red-800",
};

function renderSummary(actionType, outcome) {
  switch (actionType) {
    case "reorder":
      return `Reordered ${outcome.quantity} units`;
    case "sale":
      return `Sold ${outcome.quantity_sold} units`;
    case "stock_adjustment":
      return `Stock adjusted (${outcome.reason || "no reason given"})`;
    default:
      return actionType;
  }
}

function renderDetail(actionType, outcome) {
  switch (actionType) {
    case "reorder":
      return `Stock: ${outcome.current_stock} → ${outcome.projected_stock} | Cash: ${outcome.current_cash} → ${outcome.projected_cash}`;
    case "sale":
      return `Revenue: ₹${outcome.revenue} at ₹${outcome.unit_price}/unit | Stock after: ${outcome.new_stock}`;
    case "stock_adjustment":
      return `Stock: ${outcome.old_stock} → ${outcome.new_stock}`;
    default:
      return "";
  }
}

/**
 * Product History — click-through from the Products page showing one
 * product's full timeline: every sale, reorder, and adjustment that's
 * ever touched it, newest first. Reuses the same decisions data as
 * Decision History, filtered to a single product.
 */
function ProductHistory({ productId, onBack }) {
  const [product, setProduct] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [productsRes, decisionsRes] = await Promise.all([
          fetch(`${API_BASE}/products/`),
          fetch(`${API_BASE}/decisions/?product_id=${productId}`),
        ]);
        if (!productsRes.ok || !decisionsRes.ok) throw new Error("Server error");
        const allProducts = await productsRes.json();
        const found = allProducts.find((p) => p.product_id === productId);
        setProduct(found || null);
        setEvents(await decisionsRes.json());
      } catch (err) {
        setError("Could not reach the backend. Is uvicorn running on port 8000?");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [productId]);

  return (
    <div className="mt-4 space-y-4">
      <button onClick={onBack} className="text-sm text-ink hover:underline">
        ← Back to Products
      </button>

      {error && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
          {error}
        </div>
      )}
      {loading && <p className="text-gray-500">Loading...</p>}

      {!loading && !error && product && (
        <div className="bg-white border rounded-lg p-4">
          <h2 className="text-lg font-semibold">{product.name}</h2>
          <p className="text-sm text-gray-600 mt-1">
            Current stock: {product.current_stock} | Reorder threshold:{" "}
            {product.reorder_threshold} | Risk: {product.stockout_risk}
          </p>
        </div>
      )}

      {!loading && !error && (
        <div>
          <h3 className="font-semibold text-sm mb-2">History ({events.length} events)</h3>
          {events.length === 0 && (
            <p className="text-gray-500 text-sm">No sales, reorders, or adjustments yet.</p>
          )}
          <div className="space-y-2">
            {events.map((decision) => {
              const outcome = JSON.parse(decision.simulated_outcome);
              return (
                <div key={decision.decision_id} className="border rounded-lg p-3 bg-white text-sm">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">
                        #{decision.decision_id} — {renderSummary(decision.action_type, outcome)}
                      </p>
                      <p className="text-gray-600">
                        {renderDetail(decision.action_type, outcome)}
                      </p>
                    </div>
                    <span
                      className={`text-xs font-medium px-2 py-1 rounded shrink-0 ${
                        STATUS_COLORS[decision.approval_status] || "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {decision.approval_status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default ProductHistory;
