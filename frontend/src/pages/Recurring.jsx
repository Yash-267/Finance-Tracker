import { useEffect, useState } from "react";
import api from "../api";

export default function Recurring() {
  const [recurring, setRecurring] = useState([]);
  const [form, setForm] = useState({ amount: "", type: "expense", category: "", description: "", frequency: "monthly", start_date: "" });
  const [error, setError] = useState("");

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
        category: form.category,
        description: form.description,
        frequency: form.frequency,
        start_date: new Date(form.start_date).toISOString(),
      });
      setForm({ amount: "", type: "expense", category: "", description: "", frequency: "monthly", start_date: "" });
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
    <div className="page">
      <h1>Recurring</h1>

      <form className="inline-form inline-form-wrap" onSubmit={handleAdd}>
        <input placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required />
        <input placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
        <input type="number" step="0.01" placeholder="Amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
        <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
          <option value="expense">Expense</option>
          <option value="income">Income</option>
        </select>
        <select value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })}>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="yearly">Yearly</option>
        </select>
        <input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} required />
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
            <span>{r.category}</span>
            <span className={`mono ${r.type === "income" ? "text-income" : "text-expense"}`}>₹{r.amount.toFixed(2)}</span>
            <span>{r.frequency}</span>
            <span>{r.description}</span>
            <span>{new Date(r.next_due).toLocaleDateString()}</span>
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