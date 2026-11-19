import { useEffect, useState } from "react";
import api from "../api";

export default function Recurring() {
  const [recurring, setRecurring] = useState([]);
  const [form, setForm] = useState({ amount: "", type: "expense", category: "", description: "", frequency: "monthly", start_date: "" });
  const [error, setError] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  function loadRecurring() {
    api.get("/transactions/recurring/all").then((res) => setRecurring(res.data));
  }

  useEffect(() => {
    loadRecurring();
  }, []);

  async function handleAdd(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/transactions/add/recurring", {
        amount: Number(form.amount),
        type: form.type,
        category: form.category.trim() || "uncategorized",
        description: form.description.trim() ? form.description : "undefined",
        frequency: form.frequency,
        start_date: new Date(form.start_date).toISOString(),
      });
      setForm({ amount: "", type: "expense", category: "", description: "", frequency: "monthly", start_date: "" });
      setShowAddForm(false);
      loadRecurring();
    } catch {
      setError("Couldn't add recurring transaction — check every field is filled in.");
    }
  }

  async function handlePause(id) {
    await api.patch(`/transactions/recurring/${id}/pause`);
    loadRecurring();
  }

  async function handleResume(id) {
    await api.patch(`/transactions/recurring/${id}/resume`);
    loadRecurring();
  }

  async function handleDelete(id) {
    await api.delete(`/transactions/recurring/${id}`);
    loadRecurring();
  }

  return (
    <div className="page recurring-page">
      <h1>Recurring</h1>

      <button className="transactions-add-toggle" type="button" aria-expanded={showAddForm} aria-controls="recurring-entry-form" onClick={() => setShowAddForm(!showAddForm)}>
        {showAddForm ? "Close form" : "+ Add recurring transaction"}
      </button>
      <form id="recurring-entry-form" className="inline-form inline-form-wrap" data-open={showAddForm} onSubmit={handleAdd}>
        <input aria-label="Category" placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
        <input aria-label="Description" placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input aria-label="Amount" type="number" step="0.01" placeholder="Amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
        <select aria-label="Transaction type" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
          <option value="expense">Expense</option>
          <option value="income">Income</option>
        </select>
        <select aria-label="Frequency" value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })}>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="yearly">Yearly</option>
        </select>
        <input aria-label="Start date" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} required />
        <button type="submit">Add recurring</button>
      </form>
      {error && <p className="form-error">{error}</p>}

      <div className="ledger-table recurring">
        <div className="ledger-row ledger-header">
          <span>Category</span>
          <span className="mono">Amount</span>
          <span>Frequency</span>
          <span>Description</span>
          <span>Next due</span>
          <span>Status</span>
          <span></span>
        </div>
        {recurring.length === 0 && <p className="empty-note">No recurring transactions set up yet.</p>}
        {recurring.map((r) => (
          <div className="ledger-row" key={r.id}>
            <span className="entry-category">{r.category}</span>
            <span className={`mono ${r.type === "income" ? "text-income" : "text-expense"}`}>₹{r.amount.toFixed(2)}</span>
            <span className="entry-type">{r.frequency}</span>
            <span className="entry-description">{r.description}</span>
            <span className="entry-date"><span className="recurring-due-label">Next due </span>{new Date(r.next_due).toLocaleDateString()}</span>
            <span className={r.active ? "status-active" : "status-paused"}>{r.active ? "Active" : "Paused"}</span>
            <span className="row-actions">
              {r.active ? (
                <button className="link-button" onClick={() => handlePause(r.id)}>Pause</button>
              ) : (
                <button className="link-button" onClick={() => handleResume(r.id)}>Resume</button>
              )}
              <button className="link-button link-danger" onClick={() => handleDelete(r.id)}>Delete</button>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
