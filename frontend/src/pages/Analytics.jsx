import { useEffect, useState } from "react";
import api from "../api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function Analytics() {
  const [categories, setCategories] = useState({});
  const [topCategories, setTopCategories] = useState([]);

  useEffect(() => {
    api.get("/transactions/analytics/category").then((res) => setCategories(res.data.category_summary));
    api.get("/transactions/analytics/top-categories").then((res) => {
      setTopCategories(res.data.top_categories || []);
    });
  }, []);

  const chartData = Object.entries(categories).map(([category, total]) => ({ category, total }));

  return (
    <div className="page">
      <h1>Analytics</h1>

      <div className="dashboard-grid">
        <section className="ledger-section">
          <h2>Spending by category</h2>
          {chartData.length === 0 ? (
            <p className="empty-note">No expenses recorded yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="category" width={110} />
                <Tooltip formatter={(value) => `₹${value}`} />
                <Bar dataKey="total" fill="#A6472B" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="ledger-section">
          <h2>Top categories</h2>
          {topCategories.length === 0 ? (
            <p className="empty-note">No expenses recorded yet.</p>
          ) : (
            <ol className="top-list">
              {topCategories.map((c) => (
                <li key={c.category}>
                  <span>{c.category}</span>
                  <span className="mono">₹{c.total_amount.toFixed(2)}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}