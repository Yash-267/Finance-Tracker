import { useEffect, useState } from "react";
import api from "../api";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [recurring, setRecurring] = useState([]);
  const [error, setError] = useState("");

  function loadAll() {
    api.get("/admin/dashboard").then((res) => setStats(res.data));
    api.get("/admin/users").then((res) => setUsers(res.data));
    api.get("/admin/recurring").then((res) => setRecurring(res.data));
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleRoleChange(userId, newRole) {
    setError("");
    try {
      await api.patch(`/admin/users/${userId}/role`, { role: newRole });
      loadAll();
    } catch {
      setError("Couldn't update that user's role.");
    }
  }

  const overdue = recurring.filter((r) => r.overdue);

  return (
    <div className="page">
      <h1>Admin</h1>

      {stats && (
        <>
          <div className="stat-row">
            <div className="stat-block">
              <span className="stat-label">Users</span>
              <span className="stat-value">{stats.total_users}</span>
            </div>
            <div className="stat-block">
              <span className="stat-label">Transactions</span>
              <span className="stat-value">{stats.total_transactions}</span>
            </div>
            <div className="stat-block">
              <span className="stat-label">Total volume</span>
              <span className="stat-value">₹{stats.total_transaction_volume.toFixed(2)}</span>
            </div>
          </div>

          <div className="stat-row">
            <div className="stat-block stat-income">
              <span className="stat-label">Active recurring</span>
              <span className="stat-value">{stats.active_recurring}</span>
            </div>
            <div className="stat-block">
              <span className="stat-label">Paused recurring</span>
              <span className="stat-value">{stats.paused_recurring}</span>
            </div>
            <div className="stat-block stat-expense">
              <span className="stat-label">Overdue recurring</span>
              <span className="stat-value">{stats.overdue_recurring}</span>
            </div>
          </div>
        </>
      )}

      {error && <p className="form-error">{error}</p>}

      <div className="dashboard-grid">
        <section className="ledger-section">
          <h2>Top categories (platform-wide)</h2>
          {!stats || stats.top_categories_platform_wide.length === 0 ? (
            <p className="empty-note">No expenses recorded yet.</p>
          ) : (
            <ol className="top-list">
              {stats.top_categories_platform_wide.map((c) => (
                <li key={c.category}>
                  <span>{c.category}</span>
                  <span className="mono">₹{c.total_amount.toFixed(2)}</span>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="ledger-section">
          <h2>Overdue recurring transactions</h2>
          {overdue.length === 0 ? (
            <p className="empty-note">Nothing overdue — the scheduler is keeping up.</p>
          ) : (
            <ol className="top-list">
              {overdue.map((r) => (
                <li key={r.id}>
                  <span>User #{r.user_id} — {r.category}</span>
                  <span className="mono">₹{r.amount.toFixed(2)}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>

      <h2 style={{ marginTop: "2rem" }}>Users</h2>
      <div className="ledger-table admin-users">
        <div className="ledger-row ledger-header">
          <span>Username</span>
          <span>Email</span>
          <span>Role</span>
          <span></span>
        </div>
        {users.map((u) => (
          <div className="ledger-row" key={u.id}>
            <span>{u.username}</span>
            <span>{u.email}</span>
            <span>{u.role}</span>
            <span className="row-actions">
              {u.role === "admin" ? (
                <button className="link-button" onClick={() => handleRoleChange(u.id, "user")}>Demote</button>
              ) : (
                <button className="link-button" onClick={() => handleRoleChange(u.id, "admin")}>Promote</button>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}