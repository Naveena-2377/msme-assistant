import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

/**
 * Suppliers — lists suppliers, which products each one supplies, and
 * lets the owner add/remove suppliers or draft a vendor email
 * (negotiation, delivery follow-up, etc.) via the LLM drafting layer.
 * Drafts are never sent automatically.
 */
function Suppliers() {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const [draftFor, setDraftFor] = useState(null);
  const [context, setContext] = useState("");
  const [draftText, setDraftText] = useState("");
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState(null);

  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDelivery, setNewDelivery] = useState("");
  const [newReliability, setNewReliability] = useState("");
  const [addError, setAddError] = useState(null);

  const [deleteError, setDeleteError] = useState(null);

  const fetchSuppliers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/suppliers/`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      setSuppliers(await res.json());
    } catch (err) {
      setError("Could not reach the backend. Is uvicorn running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSuppliers();
  }, []);

  const requestDraft = async (e) => {
    e.preventDefault();
    setDraftText("");
    setDraftError(null);
    setDraftLoading(true);
    try {
      const res = await fetch(`${API_BASE}/drafts/vendor-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ supplier_id: Number(draftFor), context }),
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

  const submitAdd = async (e) => {
    e.preventDefault();
    setAddError(null);
    try {
      const res = await fetch(`${API_BASE}/suppliers/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName,
          avg_delivery_days: Number(newDelivery),
          reliability_score: Number(newReliability),
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server returned ${res.status}`);
      }
      setShowAddForm(false);
      setNewName(""); setNewDelivery(""); setNewReliability("");
      setMessage("Supplier added.");
      await fetchSuppliers();
    } catch (err) {
      setAddError(err.message);
    }
  };

  const deleteSupplier = async (supplierId, name) => {
    setDeleteError(null);
    if (!window.confirm(`Delete "${name}"?`)) return;
    try {
      const res = await fetch(`${API_BASE}/suppliers/${supplierId}`, { method: "DELETE" });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server returned ${res.status}`);
      }
      await fetchSuppliers();
    } catch (err) {
      setDeleteError(err.message);
    }
  };

  return (
    <div className="mt-4 space-y-4">
      <div className="flex justify-between items-center">
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="bg-clay text-white px-3 py-1.5 rounded text-sm hover:bg-clay-light"
        >
          {showAddForm ? "Cancel" : "+ Add Supplier"}
        </button>
      </div>

      {showAddForm && (
        <form onSubmit={submitAdd} className="border rounded-lg p-4 bg-white space-y-2">
          <h3 className="font-semibold text-sm">Add Supplier</h3>
          <div className="flex gap-2 items-end flex-wrap">
            <div>
              <label className="block text-xs text-gray-600">Name</label>
              <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                className="border rounded px-2 py-1 w-56" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Avg Delivery (days)</label>
              <input type="number" step="0.1" value={newDelivery} onChange={(e) => setNewDelivery(e.target.value)}
                className="border rounded px-2 py-1 w-32" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Reliability (0-1)</label>
              <input type="number" step="0.01" min="0" max="1" value={newReliability}
                onChange={(e) => setNewReliability(e.target.value)}
                className="border rounded px-2 py-1 w-28" required />
            </div>
            <button type="submit" className="bg-clay text-white px-3 py-1.5 rounded text-sm hover:bg-clay-light">
              Save
            </button>
          </div>
          {addError && <p className="text-sm text-red-600">{addError}</p>}
        </form>
      )}

      {message && (
        <div className="text-green-800 text-sm bg-green-50 border border-green-200 rounded p-3">{message}</div>
      )}
      {error && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">{error}</div>
      )}
      {deleteError && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">{deleteError}</div>
      )}
      {loading && <p className="text-gray-500">Loading...</p>}

      {!loading && !error && (
        <div className="overflow-x-auto bg-white border rounded-lg">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-2">Supplier</th>
                <th className="text-left p-2">Products Supplied</th>
                <th className="text-right p-2">Avg Delivery (days)</th>
                <th className="text-right p-2">Reliability</th>
                <th className="text-right p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s.supplier_id} className="border-b last:border-0">
                  <td className="p-2 font-medium">{s.name}</td>
                  <td className="p-2 text-gray-600">
                    {s.products_supplied.length > 0 ? s.products_supplied.join(", ") : "—"}
                  </td>
                  <td className="p-2 text-right font-mono">{s.avg_delivery_days}</td>
                  <td className="p-2 text-right font-mono">{(s.reliability_score * 100).toFixed(0)}%</td>
                  <td className="p-2 text-right whitespace-nowrap">
                    <button
                      onClick={() => {
                        setDraftFor(s.supplier_id);
                        setDraftText("");
                        setDraftError(null);
                        setContext("");
                      }}
                      className="text-xs text-ink hover:underline mr-3"
                    >
                      Draft Email
                    </button>
                    <button
                      onClick={() => deleteSupplier(s.supplier_id, s.name)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {draftFor && (
        <div className="border rounded-lg p-4 bg-ink/5 border-ink/20">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-sm">
              Draft Email — {suppliers.find((s) => s.supplier_id === draftFor)?.name}
            </h3>
            <button onClick={() => setDraftFor(null)} className="text-xs text-gray-500 hover:underline">
              Close
            </button>
          </div>

          <form onSubmit={requestDraft} className="flex gap-2 items-end flex-wrap mb-3">
            <div className="flex-1 min-w-[300px]">
              <label className="block text-xs text-gray-600">
                What do you want to say? (e.g. "asking for 5% bulk discount on 500 units")
              </label>
              <input
                type="text"
                value={context}
                onChange={(e) => setContext(e.target.value)}
                className="border rounded px-2 py-1 w-full"
                required
              />
            </div>
            <button
              type="submit"
              className="bg-clay text-white px-3 py-1.5 rounded text-sm hover:bg-clay-light"
            >
              Generate Draft
            </button>
          </form>

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
    </div>
  );
}

export default Suppliers;
