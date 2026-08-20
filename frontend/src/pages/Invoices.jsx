import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const RISK_COLORS = {
  high: "bg-red-100 text-red-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

const STATUS_COLORS = {
  overdue: "bg-red-50 text-red-700",
  pending: "bg-gray-50 text-gray-600",
};

/**
 * Invoices / Collections — ranks unpaid invoices by risk (Dev Step 9),
 * using each customer's historical average payment delay. Tells the
 * owner who to chase first instead of working through invoices in
 * issue-date order.
 */
function Invoices() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [draftFor, setDraftFor] = useState(null);
  const [draftText, setDraftText] = useState("");
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState(null);
  const [customerSearch, setCustomerSearch] = useState("");
  const [markPaidLoading, setMarkPaidLoading] = useState(null);
  const [markPaidError, setMarkPaidError] = useState(null);

  const fetchInvoices = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/invoices/`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      setInvoices(data);
    } catch (err) {
      setError("Could not reach the backend. Is uvicorn running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  const markAsPaid = async (invoiceId) => {
    setMarkPaidLoading(invoiceId);
    setMarkPaidError(null);
    try {
      const res = await fetch(`${API_BASE}/invoices/${invoiceId}/mark-paid`, {
        method: "POST",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server returned ${res.status}`);
      }
      await fetchInvoices();
    } catch (err) {
      setMarkPaidError(err.message);
    } finally {
      setMarkPaidLoading(null);
    }
  };

  const requestDraft = async (invoiceId) => {
    setDraftFor(invoiceId);
    setDraftText("");
    setDraftError(null);
    setDraftLoading(true);
    try {
      const res = await fetch(`${API_BASE}/drafts/collections-reminder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invoice_id: invoiceId }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || `Server returned ${res.status}`);
      setDraftText(body.draft_text);
    } catch (err) {
      setDraftError(err.message);
    } finally {
      setDraftLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const highRiskCount = invoices.filter((i) => i.risk === "high").length;
  const filteredInvoices = invoices.filter((inv) =>
    inv.customer_name.toLowerCase().includes(customerSearch.toLowerCase())
  );

  return (
    <div className="mt-4 space-y-4">
      <div className="flex justify-between items-center">
        <input
          type="text"
          value={customerSearch}
          onChange={(e) => setCustomerSearch(e.target.value)}
          placeholder="Filter by customer name..."
          className="border rounded px-2 py-1 text-sm w-64"
        />
        <button onClick={fetchInvoices} className="text-sm text-ink hover:underline">
          Refresh
        </button>
      </div>

      {error && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
          {error}
        </div>
      )}

      {!loading && !error && highRiskCount > 0 && (
        <div className="text-red-800 text-sm bg-red-50 border border-red-200 rounded p-3">
          ⚠ {highRiskCount} unpaid invoice{highRiskCount > 1 ? "s are" : " is"} from customers
          with a history of long delays — chase these first.
        </div>
      )}

      {draftFor && (
        <div className="border rounded-lg p-4 bg-ink/5 border-ink/20">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-sm">Draft Collections Reminder</h3>
            <button
              onClick={() => setDraftFor(null)}
              className="text-xs text-gray-500 hover:underline"
            >
              Close
            </button>
          </div>
          {draftLoading && <p className="text-sm text-gray-500">Generating draft...</p>}
          {draftError && (
            <p className="text-sm text-red-600">
              {draftError}
              {draftError.includes("GEMINI_API_KEY") && (
                <> — add your key to <code>backend/.env</code> to enable this feature.</>
              )}
            </p>
          )}
          {draftText && (
            <>
              <p className="text-sm whitespace-pre-wrap bg-white border rounded p-3">{draftText}</p>
              <p className="text-xs text-gray-500 mt-2">
                This is a draft only — copy, edit, and send it yourself. Nothing has been sent automatically.
              </p>
            </>
          )}
        </div>
      )}

      {markPaidError && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">
          {markPaidError}
        </div>
      )}

      {loading && <p className="text-gray-500">Loading...</p>}
      {!loading && !error && invoices.length === 0 && (
        <p className="text-gray-500">No unpaid invoices — everything's settled.</p>
      )}
      {!loading && !error && invoices.length > 0 && filteredInvoices.length === 0 && (
        <p className="text-gray-500">No invoices match "{customerSearch}".</p>
      )}

      {!loading && !error && filteredInvoices.length > 0 && (
        <div className="overflow-x-auto bg-white border rounded-lg">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-2">Customer</th>
                <th className="text-right p-2">Amount</th>
                <th className="text-left p-2">Due Date</th>
                <th className="text-left p-2">Status</th>
                <th className="text-right p-2">Days Overdue</th>
                <th className="text-right p-2">Customer Avg Delay</th>
                <th className="text-right p-2">Risk</th>
                <th className="text-right p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredInvoices.map((inv) => (
                <tr key={inv.invoice_id} className="border-b last:border-0">
                  <td className="p-2 font-medium">{inv.customer_name}</td>
                  <td className="p-2 text-right font-mono">₹{inv.amount.toLocaleString()}</td>
                  <td className="p-2">{inv.due_date}</td>
                  <td className="p-2">
                    <span
                      className={`text-xs font-medium px-2 py-1 rounded ${STATUS_COLORS[inv.status] || ""}`}
                    >
                      {inv.status}
                    </span>
                  </td>
                  <td className="p-2 text-right font-mono">{inv.days_overdue}</td>
                  <td className="p-2 text-right font-mono">{inv.customer_avg_past_delay_days}d</td>
                  <td className="p-2 text-right">
                    <span className={`text-xs font-medium px-2 py-1 rounded ${RISK_COLORS[inv.risk]}`}>
                      {inv.risk}
                    </span>
                  </td>
                  <td className="p-2 text-right whitespace-nowrap">
                    <button
                      onClick={() => requestDraft(inv.invoice_id)}
                      className="text-xs text-ink hover:underline mr-3"
                    >
                      Draft Reminder
                    </button>
                    <button
                      onClick={() => markAsPaid(inv.invoice_id)}
                      disabled={markPaidLoading === inv.invoice_id}
                      className="text-xs text-green-700 hover:underline disabled:opacity-50"
                    >
                      {markPaidLoading === inv.invoice_id ? "Marking..." : "Mark as Paid"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Invoices;
