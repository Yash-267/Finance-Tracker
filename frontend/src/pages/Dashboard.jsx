import { useEffect, useState } from "react";
import api from "../api";

const monthNames = ["January","February","March","April","May","June","July","August","September","October","November","December"];

export default function Dashboard() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    api.get(`/transactions/analytics/monthly?year=${year}&month=${month}`).then((res) => setSummary(res.data));
  }, [year, month]);

  return (
    <div className="page">
      <div className="page-header">
        <h1>Monthly-Dashboard</h1>
        <div className="month-picker">
          <select value={month} onChange={(e) => setMonth(Number(e.target.value))}>
            {monthNames.map((name, i) => (
              <option key={i} value={i + 1}>{name}</option>
            ))}
          </select>
          <input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
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
    </div>
  );
}