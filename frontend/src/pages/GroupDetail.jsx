import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate} from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

export default function GroupDetail() {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [group, setGroup] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [balances, setBalances] = useState([]);

  const [memberEmail, setMemberEmail] = useState("");
  const [memberError, setMemberError] = useState("");

  const [expenseForm, setExpenseForm] = useState({ description: "", amount: "", splitType: "equal", paidBy: "" });
  const [participants, setParticipants] = useState({});
  const [customShares, setCustomShares] = useState({});
  const [expenseError, setExpenseError] = useState("");

  const [settleTo, setSettleTo] = useState(null);
  const [settleAmount, setSettleAmount] = useState("");
  const [settleError, setSettleError] = useState("");

  function loadGroup() {
    api.get(`/groups/${groupId}`).then((res) => {
      setGroup(res.data);
      setParticipants((prev) => {
        if (Object.keys(prev).length) return prev;
        const initial = {};
        res.data.members.forEach((m) => { initial[m.id] = true; });
        return initial;
      });
    });
  }

  function loadExpenses() {
    api.get(`/groups/${groupId}/expenses`).then((res) => setExpenses(res.data));
  }

  function loadBalances() {
    api.get(`/groups/${groupId}/balances`).then((res) => setBalances(res.data.balances));
  }

  useEffect(() => {
    loadGroup();
    loadExpenses();
    loadBalances();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId]);

  async function handleAddMember(e) {
    e.preventDefault();
    setMemberError("");
    try {
      await api.post(`/groups/${groupId}/members`, { email: memberEmail });
      setMemberEmail("");
      loadGroup();
    } catch (err) {
      setMemberError(err.response?.data?.detail || "Couldn't add member.");
    }
  }

  function toggleParticipant(userId) {
    setParticipants((prev) => ({ ...prev, [userId]: !prev[userId] }));
  }

  async function handleAddExpense(e) {
    e.preventDefault();
    setExpenseError("");

    const amount = Number(expenseForm.amount);
    const paidBy = Number(expenseForm.paidBy || user?.id);

    try {
      if (expenseForm.splitType === "equal") {
        const participantIds = Object.entries(participants)
          .filter(([, checked]) => checked)
          .map(([id]) => Number(id));

        if (participantIds.length === 0) {
          setExpenseError("Select at least one participant.");
          return;
        }

        await api.post(`/groups/${groupId}/expenses`, {
          amount,
          description: expenseForm.description,
          split_type: "equal",
          participant_ids: participantIds,
          paid_by: paidBy,
        });
      } else {
        const customSharesPayload = Object.entries(customShares)
          .filter(([, value]) => value !== "" && Number(value) > 0)
          .map(([userId, value]) => ({ user_id: Number(userId), amount: Number(value) }));

        const total = customSharesPayload.reduce((sum, s) => sum + s.amount, 0);
        if (Math.abs(total - amount) > 0.01) {
          setExpenseError(`Shares add up to ₹${total.toFixed(2)}, but the total is ₹${amount.toFixed(2)}.`);
          return;
        }

        await api.post(`/groups/${groupId}/expenses`, {
          amount,
          description: expenseForm.description,
          split_type: "custom",
          custom_shares: customSharesPayload,
          paid_by: paidBy,
        });
      }

      setExpenseForm({ description: "", amount: "", splitType: expenseForm.splitType, paidBy: expenseForm.paidBy });
      setCustomShares({});
      loadExpenses();
      loadBalances();
    } catch (err) {
      setExpenseError(err.response?.data?.detail || "Couldn't add expense.");
    }
  }

  async function handleDeleteExpense(expenseId) {
    await api.delete(`/groups/${groupId}/expenses/${expenseId}`);
    loadExpenses();
    loadBalances();
  }

  async function handleDeleteGroup() {
  if (!window.confirm(`Delete "${group.name}"? This removes all expenses and settlements in this group for everyone.`)) {
    return;
  }
  await api.delete(`/groups/${groupId}`);
  navigate("/groups");
  }

  function openSettle(otherUserId, amount) {
    setSettleTo(otherUserId);
    setSettleAmount(String(amount));
    setSettleError("");
  }

  async function handleSettle(e) {
    e.preventDefault();
    setSettleError("");
    try {
      await api.post(`/groups/${groupId}/settle`, {
        paid_to: settleTo,
        amount: Number(settleAmount),
      });
      setSettleTo(null);
      setSettleAmount("");
      loadBalances();
    } catch {
      setSettleError("Couldn't record settlement.");
    }
  }

  const memberMap = useMemo(() => {
    const map = {};
    (group?.members || []).forEach((m) => { map[m.id] = m; });
    return map;
  }, [group]);

  if (!group) return <div className="page"><h1>Group</h1><p className="empty-note">Loading…</p></div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>{group.name}</h1>
        <button className="link-button link-danger" onClick={handleDeleteGroup}>Delete group</button>
      </div>

      <section className="ledger-section">
        <h2>Members</h2>
        <ul className="member-list">
          {group.members.map((m) => (
            <li key={m.id}>{m.username}{m.id === user?.id && " (you)"}</li>
          ))}
        </ul>
        <form className="inline-form" onSubmit={handleAddMember}>
          <input
            type="email"
            placeholder="Add member by email"
            value={memberEmail}
            onChange={(e) => setMemberEmail(e.target.value)}
            required
          />
          <button type="submit">Add member</button>
        </form>
        {memberError && <p className="form-error">{memberError}</p>}
      </section>

      <section className="ledger-section">
        <h2>Balances</h2>
        {balances.length === 0 ? (
          <p className="empty-note">All settled up.</p>
        ) : (
          <ul className="balance-list">
            {balances.map((b, i) => {
              const youOwe = b.owed_by_id === user?.id;
              return (
                <li className="balance-item" key={i}>
                  <span>
                    {youOwe ? (
                      <>You owe <strong>{b.owed_to_username}</strong></>
                    ) : b.owed_to_id === user?.id ? (
                      <><strong>{b.owed_by_username}</strong> owes you</>
                    ) : (
                      <><strong>{b.owed_by_username}</strong> owes <strong>{b.owed_to_username}</strong></>
                    )}
                  </span>
                  <span className={`mono ${youOwe ? "text-expense" : "text-income"}`}>₹{b.amount.toFixed(2)}</span>
                  {youOwe && (
                    <button className="link-button" onClick={() => openSettle(b.owed_to_id, b.amount)}>Settle up</button>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {settleTo !== null && (
          <form className="inline-form" onSubmit={handleSettle}>
            <span>Settling with {memberMap[settleTo]?.username}</span>
            <input
              type="number"
              step="0.01"
              value={settleAmount}
              onChange={(e) => setSettleAmount(e.target.value)}
              required
            />
            <button type="submit">Confirm payment</button>
            <button type="button" className="link-button" onClick={() => setSettleTo(null)}>Cancel</button>
          </form>
        )}
        {settleError && <p className="form-error">{settleError}</p>}
      </section>

      <section className="ledger-section">
        <h2>Add expense</h2>
        <form className="expense-form" onSubmit={handleAddExpense}>
          <div className="inline-form">
            <input
              placeholder="Description"
              value={expenseForm.description}
              onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Total amount"
              value={expenseForm.amount}
              onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
              required
            />
            <select
              value={expenseForm.splitType}
              onChange={(e) => setExpenseForm({ ...expenseForm, splitType: e.target.value })}
            >
              <option value="equal">Split equally</option>
              <option value="custom">Custom split</option>
            </select>
            <select
              value={expenseForm.paidBy || user?.id || ""}
              onChange={(e) => setExpenseForm({ ...expenseForm, paidBy: e.target.value })}
            >
              {group.members.map((m) => (
                <option key={m.id} value={m.id}>
                  Paid by {m.id === user?.id ? "you" : m.username}
                </option>
              ))}
            </select>
          </div>

          {expenseForm.splitType === "equal" ? (
            <div className="participant-list">
              {group.members.map((m) => (
                <label className="participant-item" key={m.id}>
                  <input
                    type="checkbox"
                    checked={!!participants[m.id]}
                    onChange={() => toggleParticipant(m.id)}
                  />
                  {m.username}
                </label>
              ))}
            </div>
          ) : (
            <div className="custom-share-list">
              {group.members.map((m) => (
                <div className="custom-share-row" key={m.id}>
                  <span>{m.username}</span>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={customShares[m.id] || ""}
                    onChange={(e) => setCustomShares({ ...customShares, [m.id]: e.target.value })}
                  />
                </div>
              ))}
            </div>
          )}

          <button type="submit">Add expense</button>
        </form>
        {expenseError && <p className="form-error">{expenseError}</p>}
      </section>

      <section className="ledger-section">
        <h2>Expense history</h2>
        {expenses.length === 0 ? (
          <p className="empty-note">No expenses logged yet.</p>
        ) : (
          <div className="ledger-table group-expenses">
            <div className="ledger-row ledger-header">
              <span>Description</span>
              <span>Paid by</span>
              <span className="mono">Amount</span>
              <span>Date</span>
              <span></span>
            </div>
            {expenses.map((e) => (
              <div className="ledger-row" key={e.id}>
                <span>{e.description}</span>
                <span>{memberMap[e.paid_by]?.username || `User #${e.paid_by}`}</span>
                <span className="mono">₹{e.amount.toFixed(2)}</span>
                <span>{new Date(e.created_at).toLocaleDateString()}</span>
                <button className="link-button link-danger" onClick={() => handleDeleteExpense(e.id)}>Delete</button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}