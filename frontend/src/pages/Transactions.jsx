import { useEffect, useMemo, useState } from "react";
import api from "../api";

const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];

export default function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [form, setForm] = useState({ amount: "", type: "expense", category: "", description: "", date: "" });
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [viewDate, setViewDate] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [error, setError] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  function loadTransactions() {
    api.get("/transactions/all").then((res) => setTransactions(res.data));
  }

  useEffect(() => {
    loadTransactions();
  }, []);

  async function handleAdd(e) {
    e.preventDefault();
    setError("");
    try {
      const payload = {
        amount: Number(form.amount),
        type: form.type,
        category: form.category.trim() || "uncategorized",
        description: form.description.trim() ? form.description : "undefined",
      };
      if (form.date) {
        payload.created_at = new Date(form.date).toISOString();
      }
      await api.post("/transactions/add", payload);
      setForm({ amount: "", type: "expense", category: "", description: "", date: "" });
      setShowAddForm(false);
      loadTransactions();
    } catch {
      setError("Couldn't add transaction — check the amount and category.");
    }
  }

  async function handleDelete(id) {
    await api.delete(`/transactions/delete/${id}`);
    loadTransactions();
  }

  const categories = useMemo(
    () => [...new Set(transactions.map((t) => t.category))].sort(),
    [transactions]
  );

  const isCurrentMonth = useMemo(() => {
    const now = new Date();
    return viewDate.getFullYear() === now.getFullYear() && viewDate.getMonth() === now.getMonth();
  }, [viewDate]);

  function shiftMonth(delta) {
    setViewDate((prev) => new Date(prev.getFullYear(), prev.getMonth() + delta, 1));
  }

  const monthTransactions = transactions.filter((t) => {
    const created = new Date(t.created_at);
    return created.getFullYear() === viewDate.getFullYear() && created.getMonth() === viewDate.getMonth();
  });

  const filteredTransactions =
    selectedCategory === "all"
      ? monthTransactions
      : monthTransactions.filter((t) => t.category === selectedCategory);

  return (
    <div className="page transactions-page">
      <div className="page-header">
        <h1>Transactions</h1>
        <div className="month-switcher">
          <button className="month-nav-button" onClick={() => shiftMonth(-1)} aria-label="Previous month">‹</button>
          <span className="month-label">
            <span className="transactions-month-full">{monthNames[viewDate.getMonth()]} {viewDate.getFullYear()}</span>
            <abbr className="transactions-month-short" title={`${monthNames[viewDate.getMonth()]} ${viewDate.getFullYear()}`}>
              {monthNames[viewDate.getMonth()].slice(0, 3)} {viewDate.getFullYear()}
            </abbr>
          </span>
          <button
            className="month-nav-button"
            onClick={() => shiftMonth(1)}
            aria-label="Next month"
            disabled={isCurrentMonth}
          >
            ›
          </button>
        </div>
      </div>

      <button
        className="transactions-add-toggle"
        type="button"
        aria-expanded={showAddForm}
        aria-controls="transaction-entry-form"
        onClick={() => setShowAddForm((open) => !open)}
      >
        {showAddForm ? "Close form" : "+ Add transaction"}
      </button>
      <form id="transaction-entry-form" className="inline-form" data-open={showAddForm} onSubmit={handleAdd}>
        <input className="entry-category" aria-label="Category" placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
        <input className="entry-description" aria-label="Description" placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <input className="entry-amount" aria-label="Amount" type="number" step="0.01" placeholder="Amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
        <select className="entry-type" aria-label="Transaction type" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
          <option value="expense">Expense</option>
          <option value="income">Income</option>
        </select>
        <input
          className="entry-date"
          aria-label="Date (optional)"
          type="date"
          value={form.date}
          onChange={(e) => setForm({ ...form, date: e.target.value })}
          title="Leave blank to use today's date"
        />
        <button type="submit">Add entry</button>
      </form>
      {error && <p className="form-error">{error}</p>}

      <div className="filter-bar">
        <select
          aria-label="Filter by category"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          <option value="all">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="ledger-table transactions">
        <div className="ledger-row ledger-header">
          <span>Category</span>
          <span>Description</span>
          <span>Type</span>
          <span className="mono">Amount</span>
          <span>Created At</span>
          <span></span>
        </div>
        {filteredTransactions.length === 0 && (
          <p className="empty-note">
            {monthTransactions.length === 0
              ? "No transactions in this month."
              : "No transactions in this category for this month."}
          </p>
        )}
        {filteredTransactions.map((t) => (
          <div className="ledger-row" key={t.id}>
            <span className="entry-category">{t.category}</span>
            <span className="entry-description">{t.description || "—"}</span>
            <span className="entry-type">{t.type}</span>
            <span className={`mono ${t.type === "income" ? "text-income" : "text-expense"}`}>
              {t.type === "income" ? "+" : "-"}₹{t.amount.toFixed(2)}
            </span>
            <span className="entry-date">{new Date(t.created_at).toLocaleDateString("en-IN")}</span>
            <button className="link-button" onClick={() => handleDelete(t.id)}>Delete</button>
          </div>
        ))}
      </div>
    </div>
  );
}
