import { useEffect, useState } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";

const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];

export default function Dashboard() {
  const { logout } = useAuth();
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [summary, setSummary] = useState(null);
  const [profile, setProfile] = useState(null);
  const [password, setPassword] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  async function handleDeleteAccount(event) {
    event.preventDefault();
    setDeleteError("");
    setDeleting(true);
    try {
      await api.delete("/auth/me", { data: { password } });
      logout();
    } catch (error) {
      const status = error.response?.status;
      if (status === 400 && error.response.data?.detail === "Incorrect password") {
        setDeleteError("Incorrect password.");
      } else if (status === 404 || status === 405) {
        setDeleteError("Account deletion is unavailable on the connected server.");
      } else if (!status) {
        setDeleteError("Couldn't reach the server. Check your connection and try again.");
      } else {
        setDeleteError(`Couldn't delete your account (HTTP ${status}). Please try again.`);
      }
    } finally {
      setDeleting(false);
    }
  }

  useEffect(() => {
    api.get("/auth/me").then((res) => setProfile(res.data));
  }, []);

  useEffect(() => {
    api.get(`/transactions/analytics/monthly?year=${year}&month=${month}`).then((res) => setSummary(res.data));
  }, [year, month]);

  return (
    <div className="page monthly-dashboard">
      <div className="page-header">
        <div>
          <h1>Monthly-Dashboard</h1>

          {profile && (
            <div className="user-info">
              <span>{profile.username}</span>
              <span>{profile.email}</span>
            </div>
          )}
        </div>

        <div className="month-picker">
          <select aria-label="Month" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {monthNames.map((name, i) => (
              <option key={i} value={i + 1}>{name}</option>
            ))}
          </select>

          <input
            aria-label="Year"
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          />
        </div>
      </div>

      {summary && (
        <div className="stat-row">
          <div className="stat-block stat-income">
            <span className="stat-label">Income</span>
            <span className="stat-value">₹{summary.total_income.toFixed(2)}</span>
          </div>

          <div className="stat-block stat-expense">
            <span className="stat-label">Expense</span>
            <span className="stat-value">₹{summary.total_expense.toFixed(2)}</span>
          </div>

          <div className="stat-block stat-balance">
            <span className="stat-label">Balance</span>
            <span className="stat-value">₹{summary.monthly_balance.toFixed(2)}</span>
          </div>
        </div>
      )}

      <details className="account-deletion" onToggle={(event) => {
        if (!event.currentTarget.open) {
          setPassword("");
          setDeleteError("");
        }
      }}>
        <summary>Delete account</summary>
        <p>Enter your password to permanently delete your account, transactions, budgets, and group activity. Groups you own pass to another member if one remains.</p>
        <form className="inline-form" onSubmit={handleDeleteAccount}>
          <input
            type="password"
            aria-label="Current password"
            placeholder="Current password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <button type="submit" disabled={deleting}>{deleting ? "Deleting account…" : "Permanently delete account"}</button>
        </form>
        {deleteError && <p className="form-error" role="alert">{deleteError}</p>}
      </details>
    </div>
  );
}
