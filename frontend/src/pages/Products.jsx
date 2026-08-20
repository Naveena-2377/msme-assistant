import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const RISK_COLORS = {
  high: "bg-red-100 text-red-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
  unknown: "bg-gray-100 text-gray-700",
};

/**
 * Products / Inventory — the page an MSME owner would check daily:
 * stock levels, reorder threshold, current stockout risk, and which
 * supplier each product is sourced from.
 */
function Products({ onSelectProduct }) {
  const [products, setProducts] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");
  const [editThreshold, setEditThreshold] = useState("");
  const [editCost, setEditCost] = useState("");
  const [editSupplierId, setEditSupplierId] = useState("");
  const [editError, setEditError] = useState(null);

  const [saleProductId, setSaleProductId] = useState("");
  const [saleQuantity, setSaleQuantity] = useState("");

  const [adjustProductId, setAdjustProductId] = useState("");
  const [adjustNewStock, setAdjustNewStock] = useState("");
  const [adjustReason, setAdjustReason] = useState("");

  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newStock, setNewStock] = useState("");
  const [newThreshold, setNewThreshold] = useState("");
  const [newCost, setNewCost] = useState("");
  const [newPrice, setNewPrice] = useState("");
  const [newSupplierId, setNewSupplierId] = useState("");
  const [addError, setAddError] = useState(null);

  const [deleteError, setDeleteError] = useState(null);

  const fetchProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/products/`);
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      const riskOrder = { high: 0, medium: 1, low: 2, unknown: 3 };
      data.sort((a, b) => riskOrder[a.stockout_risk] - riskOrder[b.stockout_risk]);
      setProducts(data);
    } catch (err) {
      setError("Could not reach the backend. Is uvicorn running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  const fetchSuppliers = async () => {
    try {
      const res = await fetch(`${API_BASE}/suppliers/`);
      if (!res.ok) return;
      setSuppliers(await res.json());
    } catch {
      // Convenience list for dropdowns; fail silently.
    }
  };

  useEffect(() => {
    fetchProducts();
    fetchSuppliers();
  }, []);

  const belowThresholdCount = products.filter((p) => p.below_threshold).length;

  const submitSale = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/inventory/sales`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: Number(saleProductId), quantity: Number(saleQuantity) }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server returned ${res.status}`);
      }
      setMessage("Sale recorded.");
      setSaleProductId("");
      setSaleQuantity("");
      await fetchProducts();
    } catch (err) {
      setError(err.message);
    }
  };

  const submitAdjustment = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE}/inventory/stock-adjustments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: Number(adjustProductId),
          new_stock: Number(adjustNewStock),
          reason: adjustReason,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server returned ${res.status}`);
      }
      setMessage("Stock adjusted.");
      setAdjustProductId("");
      setAdjustNewStock("");
      setAdjustReason("");
      await fetchProducts();
    } catch (err) {
      setError(err.message);
    }
  };

  const startEdit = (p) => {
    setEditingId(p.product_id);
    setEditName(p.name);
    setEditThreshold(p.reorder_threshold);
    setEditCost(p.unit_cost);
    setEditSupplierId(p.supplier_id || "");
    setEditError(null);
  };

  const saveEdit = async (e) => {
    e.preventDefault();
    setEditError(null);
    try {
      const res = await fetch(`${API_BASE}/products/${editingId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editName,
          reorder_threshold: Number(editThreshold),
          unit_cost: Number(editCost),
          supplier_id: editSupplierId ? Number(editSupplierId) : null,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server returned ${res.status}`);
      }
      setEditingId(null);
      await fetchProducts();
    } catch (err) {
      setEditError(err.message);
    }
  };

  const submitAdd = async (e) => {
    e.preventDefault();
    setAddError(null);
    try {
      const res = await fetch(`${API_BASE}/products/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName,
          current_stock: Number(newStock) || 0,
          reorder_threshold: Number(newThreshold),
          unit_cost: Number(newCost),
          unit_price: Number(newPrice),
          supplier_id: newSupplierId ? Number(newSupplierId) : null,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server returned ${res.status}`);
      }
      setShowAddForm(false);
      setNewName(""); setNewStock(""); setNewThreshold(""); setNewCost(""); setNewPrice(""); setNewSupplierId("");
      setMessage("Product added.");
      await fetchProducts();
    } catch (err) {
      setAddError(err.message);
    }
  };

  const deleteProduct = async (productId, name) => {
    setDeleteError(null);
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
      const res = await fetch(`${API_BASE}/products/${productId}`, { method: "DELETE" });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `Server returned ${res.status}`);
      }
      await fetchProducts();
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
          {showAddForm ? "Cancel" : "+ Add Product"}
        </button>
        <button onClick={fetchProducts} className="text-sm text-ink hover:underline">
          Refresh
        </button>
      </div>
      <p className="text-xs text-gray-500 -mt-2">Click a product row to see its full history.</p>

      {showAddForm && (
        <form onSubmit={submitAdd} className="border rounded-lg p-4 bg-white space-y-2">
          <h3 className="font-semibold text-sm">Add Product</h3>
          <div className="flex gap-2 items-end flex-wrap">
            <div>
              <label className="block text-xs text-gray-600">Name</label>
              <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                className="border rounded px-2 py-1 w-48" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Initial Stock</label>
              <input type="number" value={newStock} onChange={(e) => setNewStock(e.target.value)}
                className="border rounded px-2 py-1 w-24" />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Reorder Threshold</label>
              <input type="number" value={newThreshold} onChange={(e) => setNewThreshold(e.target.value)}
                className="border rounded px-2 py-1 w-28" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Unit Cost</label>
              <input type="number" step="0.01" value={newCost} onChange={(e) => setNewCost(e.target.value)}
                className="border rounded px-2 py-1 w-24" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Unit Price</label>
              <input type="number" step="0.01" value={newPrice} onChange={(e) => setNewPrice(e.target.value)}
                className="border rounded px-2 py-1 w-24" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Supplier</label>
              <select value={newSupplierId} onChange={(e) => setNewSupplierId(e.target.value)}
                className="border rounded px-2 py-1 w-44">
                <option value="">Unassigned</option>
                {suppliers.map((s) => (
                  <option key={s.supplier_id} value={s.supplier_id}>{s.name}</option>
                ))}
              </select>
            </div>
            <button type="submit" className="bg-clay text-white px-3 py-1.5 rounded text-sm hover:bg-clay-light">
              Save
            </button>
          </div>
          {addError && <p className="text-sm text-red-600">{addError}</p>}
        </form>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <form onSubmit={submitSale} className="border rounded-lg p-4 bg-white">
          <h3 className="font-semibold mb-2 text-sm">Record a Sale</h3>
          <div className="flex gap-2 items-end flex-wrap">
            <div>
              <label className="block text-xs text-gray-600">Product</label>
              <select value={saleProductId} onChange={(e) => setSaleProductId(e.target.value)}
                className="border rounded px-2 py-1 w-48" required>
                <option value="" disabled>Select a product</option>
                {products.map((p) => (
                  <option key={p.product_id} value={p.product_id}>{p.name} (stock: {p.current_stock})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600">Quantity Sold</label>
              <input type="number" value={saleQuantity} onChange={(e) => setSaleQuantity(e.target.value)}
                className="border rounded px-2 py-1 w-24" required />
            </div>
            <button type="submit" className="bg-green-600 text-white px-3 py-1.5 rounded text-sm hover:bg-green-700">
              Record Sale
            </button>
          </div>
        </form>

        <form onSubmit={submitAdjustment} className="border rounded-lg p-4 bg-white">
          <h3 className="font-semibold mb-2 text-sm">Adjust Stock (correction)</h3>
          <div className="flex gap-2 items-end flex-wrap">
            <div>
              <label className="block text-xs text-gray-600">Product</label>
              <select value={adjustProductId} onChange={(e) => setAdjustProductId(e.target.value)}
                className="border rounded px-2 py-1 w-48" required>
                <option value="" disabled>Select a product</option>
                {products.map((p) => (
                  <option key={p.product_id} value={p.product_id}>{p.name} (stock: {p.current_stock})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600">New Stock</label>
              <input type="number" value={adjustNewStock} onChange={(e) => setAdjustNewStock(e.target.value)}
                className="border rounded px-2 py-1 w-24" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Reason</label>
              <input type="text" value={adjustReason} onChange={(e) => setAdjustReason(e.target.value)}
                className="border rounded px-2 py-1 w-40" placeholder="e.g. damaged goods" required />
            </div>
            <button type="submit" className="bg-clay text-white px-3 py-1.5 rounded text-sm hover:bg-clay-light">
              Adjust
            </button>
          </div>
        </form>
      </div>

      {message && (
        <div className="text-green-800 text-sm bg-green-50 border border-green-200 rounded p-3">{message}</div>
      )}
      {error && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">{error}</div>
      )}
      {deleteError && (
        <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">{deleteError}</div>
      )}

      {!loading && !error && belowThresholdCount > 0 && (
        <div className="text-amber-800 text-sm bg-amber-50 border border-amber-200 rounded p-3">
          ⚠ {belowThresholdCount} product{belowThresholdCount > 1 ? "s are" : " is"} below its
          reorder threshold and may need restocking soon.
        </div>
      )}

      {loading && <p className="text-gray-500">Loading...</p>}

      {!loading && !error && (
        <div className="overflow-x-auto bg-white border rounded-lg">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-2">Product</th>
                <th className="text-left p-2">Supplier</th>
                <th className="text-right p-2">Stock</th>
                <th className="text-right p-2">Reorder Threshold</th>
                <th className="text-right p-2">Avg Daily Demand</th>
                <th className="text-right p-2">Days of Stock</th>
                <th className="text-right p-2">Risk</th>
                <th className="text-right p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr
                  key={p.product_id}
                  onClick={() => onSelectProduct && onSelectProduct(p.product_id)}
                  className={`border-b last:border-0 cursor-pointer hover:bg-ink/5 ${p.below_threshold ? "bg-amber-50" : ""}`}
                >
                  <td className="p-2 font-medium">
                    {p.below_threshold && <span className="text-amber-600 mr-1">⚠</span>}
                    {p.name}
                  </td>
                  <td className="p-2 text-gray-600">{p.supplier_name}</td>
                  <td className="p-2 text-right font-mono">{p.current_stock}</td>
                  <td className="p-2 text-right font-mono">{p.reorder_threshold}</td>
                  <td className="p-2 text-right font-mono">{p.avg_daily_demand}</td>
                  <td className="p-2 text-right">{p.days_of_stock !== null ? p.days_of_stock : "—"}</td>
                  <td className="p-2 text-right">
                    <span className={`text-xs font-medium px-2 py-1 rounded ${RISK_COLORS[p.stockout_risk]}`}>
                      {p.stockout_risk}
                    </span>
                  </td>
                  <td className="p-2 text-right whitespace-nowrap">
                    <button
                      onClick={(e) => { e.stopPropagation(); startEdit(p); }}
                      className="text-xs text-ink hover:underline mr-3"
                    >
                      Edit
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteProduct(p.product_id, p.name); }}
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

      {editingId && (
        <div className="border rounded-lg p-4 bg-ink/5 border-ink/20">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-sm">Edit Product</h3>
            <button onClick={() => setEditingId(null)} className="text-xs text-gray-500 hover:underline">
              Close
            </button>
          </div>
          <form onSubmit={saveEdit} className="flex gap-2 items-end flex-wrap">
            <div>
              <label className="block text-xs text-gray-600">Name</label>
              <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)}
                className="border rounded px-2 py-1 w-56" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Reorder Threshold</label>
              <input type="number" value={editThreshold} onChange={(e) => setEditThreshold(e.target.value)}
                className="border rounded px-2 py-1 w-32" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Unit Cost</label>
              <input type="number" step="0.01" value={editCost} onChange={(e) => setEditCost(e.target.value)}
                className="border rounded px-2 py-1 w-32" required />
            </div>
            <div>
              <label className="block text-xs text-gray-600">Supplier</label>
              <select value={editSupplierId} onChange={(e) => setEditSupplierId(e.target.value)}
                className="border rounded px-2 py-1 w-44">
                <option value="">Unassigned</option>
                {suppliers.map((s) => (
                  <option key={s.supplier_id} value={s.supplier_id}>{s.name}</option>
                ))}
              </select>
            </div>
            <button type="submit" className="bg-clay text-white px-3 py-1.5 rounded text-sm hover:bg-clay-light">
              Save
            </button>
          </form>
          {editError && <p className="text-sm text-red-600 mt-2">{editError}</p>}
        </div>
      )}
    </div>
  );
}

export default Products;
