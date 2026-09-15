import { useEffect, useState } from "react";
import api from "../api";
import { useNotifications } from "../context/NotificationContext";

export default function Budgets() {
  const [budgets, setBudgets] = useState([]);
  const [form, setForm] = useState({ category: "", monthly_limit: "" });
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [error, setError] = useState("");
  const { refresh: refreshAlerts } = useNotifications();

  function loadBudgets() {
    api.get("/budgets/all").then((res) => setBudgets(res.data));
  }

  useEffect(() => {
    loadBudgets();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/budgets/create", {
        category: form.category,
        monthly_limit: Number(form.monthly_limit),
      });
      setForm({ category: "", monthly_limit: "" });
      loadBudgets();
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't create budget.");
    }
  }

  function startEdit(budget) {
    setEditingId(budget.id);
    setEditValue(String(budget.monthly_limit));
  }

  async function saveEdit(id) {
    await api.patch(`/budgets/${id}`, { monthly_limit: Number(editValue) });
    setEditingId(null);
    loadBudgets();
  }

  async function handleDelete(id) {
    await api.delete(`/budgets/${id}`);
    loadBudgets();
    refreshAlerts();
  }

  function statusClass(percent) {
    if (percent >= 100) return "exceeded";
    if (percent >= 80) return "approaching";
    return "ok";
  }

  return (
    <div className="page">
      <h1>Budgets</h1>

      <form className="inline-form" onSubmit={handleCreate}>
        <input
          placeholder="Category"
          value={form.category}
          onChange={(e) => setForm({ ...form, category: e.target.value })}
          required
        />
        <input
          type="number"
          step="0.01"
          placeholder="Monthly limit"
          value={form.monthly_limit}
          onChange={(e) => setForm({ ...form, monthly_limit: e.target.value })}
          required
        />
        <button type="submit">Set budget</button>
      </form>
      {error && <p className="form-error">{error}</p>}

      {budgets.length === 0 && <p className="empty-note">No budgets set yet — add one above.</p>}

      <div className="budget-list">
        {budgets.map((b) => (
          <div className="budget-row" key={b.id}>
            <div className="budget-row-header">
              <span>{b.category}</span>
              {editingId === b.id ? (
                <span className="budget-edit">
                  <input
                    type="number"
                    step="0.01"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                  />
                  <button className="link-button" onClick={() => saveEdit(b.id)}>Save</button>
                  <button className="link-button" onClick={() => setEditingId(null)}>Cancel</button>
                </span>
              ) : (
                <span className="mono">
                  ₹{b.spent_this_month.toFixed(2)} / ₹{b.monthly_limit.toFixed(2)}
                </span>
              )}
            </div>
            <div className="budget-bar-track">
              <div
                className={`budget-bar-fill ${statusClass(b.percent_used)}`}
                style={{ width: `${Math.min(b.percent_used, 100)}%` }}
              />
            </div>
            <div className="budget-row-footer">
              <span className={`budget-percent ${statusClass(b.percent_used)}`}>{b.percent_used}% used</span>
              <span className="row-actions">
                {editingId !== b.id && (
                  <button className="link-button" onClick={() => startEdit(b)}>Edit</button>
                )}
                <button className="link-button link-danger" onClick={() => handleDelete(b.id)}>Delete</button>
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}