import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

/**
 * Approval Queue — the visible proof of the safety-gated design
 * (Dev Step 8). Lets you propose a reorder (which runs the full
 * simulate -> rule check loop on the backend), then shows anything
 * that got flagged for human review, with approve/reject buttons.
 * Nothing flagged executes without a click here.
 */
function ApprovalQueue() {
  const [pending, setPending] = useState([]);
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [lastResult, setLastResult] = useState(null);

  const fetchPending = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/approvals/`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setPending(data);
    } catch (err) {
      setError("Could not reach the backend. Is uvicorn running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      const res = await fetch(`${API_BASE}/products/`);
      if (!res.ok) return;
      setProducts(await res.json());
    } catch {
      // Product list is a convenience for the dropdown; fail silently here.
    }
  };

  const fetchCustomers = async () => {
    try {
      const res = await fetch(`${API_BASE}/customers/`);
      if (!res.ok) return;
      setCustomers(await res.json());
    } catch {
      // Customer list is a convenience for the "From" dropdown; fail silently here.
    }
  };

  useEffect(() => {
    fetchPending();
    fetchProducts();
    fetchCustomers();
  }, []);

  const proposeReorder = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/reorder/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: Number(productId),
          quantity: Number(quantity),
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server returned ${res.status}`);
      }
      const data = await res.json();
      setLastResult(data);
      await fetchPending();
      await fetchProducts();
    } catch (err) {
      setError(err.message || "Could not submit the proposal. Check the backend is running.");
    }
  };

  const respond = async (decisionId, action) => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/approvals/${decisionId}/${action}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      await fetchPending();
      await fetchProducts();
    } catch (err) {
      setError("Could not update that decision. Check the backend is running.");
    }
  };

  const [orderText, setOrderText] = useState("");
  const [orderCustomerId, setOrderCustomerId] = useState("");
  const [parsedItems, setParsedItems] = useState(null);
  const [parseLoading, setParseLoading] = useState(false);
  const [parseError, setParseError] = useState(null);

  const parseOrder = async (e) => {
    e.preventDefault();
    setParsedItems(null);
    setParseError(null);
    setParseLoading(true);
    try {
      const res = await fetch(`${API_BASE}/drafts/parse-order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: orderText }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || `Server returned ${res.status}`);
      setParsedItems(body.items || []);
    } catch (err) {
      setParseError(err.message);
    } finally {
      setParseLoading(false);
    }
  };

  return (
    <div className="mt-4 space-y-6">
      {/* WhatsApp order parsing */}
      <div className="border rounded-lg p-4 bg-white">
        <h2 className="text-lg font-semibold mb-2">Parse a WhatsApp Order</h2>
        <p className="text-xs text-gray-500 mb-2">
          Paste an informal order message — this only extracts product names and quantities
          for you to review. It does not create a reorder automatically.
        </p>
        <form onSubmit={parseOrder} className="flex gap-2 items-end flex-wrap">
          <div>
            <label className="block text-xs text-gray-600">From (customer)</label>
            <select
              value={orderCustomerId}
              onChange={(e) => setOrderCustomerId(e.target.value)}
              className="border rounded px-2 py-1 w-48"
              required
            >
              <option value="" disabled>Select who sent this</option>
              {customers.map((c) => (
                <option key={c.customer_id} value={c.customer_id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[300px]">
            <label className="block text-xs text-gray-600">Message</label>
            <input
              type="text"
              value={orderText}
              onChange={(e) => setOrderText(e.target.value)}
              placeholder='e.g. "need 10 bags cement and 5 pvc pipes"'
              className="border rounded px-2 py-1 w-full"
              required
            />
          </div>
          <button
            type="submit"
            className="bg-clay text-white px-4 py-1.5 rounded hover:bg-clay-light"
          >
            Parse
          </button>
        </form>
        {parseLoading && <p className="text-sm text-gray-500 mt-2">Parsing...</p>}
        {parseError && (
          <p className="text-sm text-red-600 mt-2">
            {parseError}
            {parseError.includes("GEMINI_API_KEY") && (
              <> — add your key to <code>backend/.env</code> to enable this feature.</>
            )}
          </p>
        )}
        {parsedItems && (
          <div className="mt-2 text-sm bg-gray-50 border rounded p-3">
            <p className="font-medium mb-1">
              From: {customers.find((c) => String(c.customer_id) === String(orderCustomerId))?.name}
            </p>
            {parsedItems.length === 0 ? (
              <p className="text-gray-500">No items detected.</p>
            ) : (
              <ul className="list-disc list-inside">
                {parsedItems.map((item, i) => (
                  <li key={i}>
                    {item.product_name} — qty {item.quantity}
                  </li>
                ))}
              </ul>
            )}
            <p className="text-xs text-gray-500 mt-2">
              Match these to real products above and propose a reorder yourself — nothing here
              was added automatically.
            </p>
          </div>
        )}
      </div>

      {/* Propose a reorder */}
      <div className="border rounded-lg p-4 bg-white">
        <h2 className="text-lg font-semibold mb-2">Propose a Reorder</h2>
        <form onSubmit={proposeReorder} className="flex gap-2 items-end flex-wrap">
          <div>
            <label className="block text-sm text-gray-600">Product</label>
            <select
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              className="border rounded px-2 py-1 w-56"
              required
            >
              <option value="" disabled>Select a product</option>
              {products.map((p) => (
                <option key={p.product_id} value={p.product_id}>
                  {p.name} (stock: {p.current_stock})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600">Quantity</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="border rounded px-2 py-1 w-28"
              required
            />
          </div>
          <button
            type="submit"
            className="bg-clay text-white px-4 py-1.5 rounded hover:bg-clay-light"
          >
            Simulate
          </button>
        </form>

        {lastResult && (
          <div className="mt-3 text-sm bg-gray-50 border rounded p-3">
            <p>
              Decision #{lastResult.decision_id} —{" "}
              <span className="font-semibold">{lastResult.rule_check_result}</span> →{" "}
              {lastResult.approval_status}
            </p>
          </div>
        )}
      </div>

      {error && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
          {error}
        </div>
      )}

      {/* Pending approvals */}
      <div>
        <h2 className="text-lg font-semibold">Approval Queue</h2>
        {loading && <p className="text-gray-500">Loading...</p>}
        {!loading && pending.length === 0 && (
          <p className="text-gray-500">No pending decisions right now.</p>
        )}
        <div className="space-y-3 mt-2">
          {pending.map((decision) => {
            const outcome = JSON.parse(decision.simulated_outcome);
            return (
              <div key={decision.decision_id} className="border rounded-lg p-4 bg-white">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold">
                      {outcome.product_name} — reorder {outcome.quantity} units
                    </p>
                    <p className="text-sm text-gray-600">
                      Cash: {outcome.current_cash} → {outcome.projected_cash} | Stock:{" "}
                      {outcome.current_stock} → {outcome.projected_stock} | Risk:{" "}
                      {outcome.stockout_risk_before} → {outcome.stockout_risk_after}
                    </p>
                  </div>
                  <span className="text-xs font-medium bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                    {decision.rule_check_result}
                  </span>
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => respond(decision.decision_id, "approve")}
                    className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => respond(decision.decision_id, "reject")}
                    className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
                  >
                    Reject
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default ApprovalQueue;
