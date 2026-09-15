import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useNotifications } from "../context/NotificationContext";

export default function Sidebar() {
  const { logout, user } = useAuth();
  const { unreadCount } = useNotifications();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">Ledger</div>
      <nav className="sidebar-nav">
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/transactions">Transactions</NavLink>
        <NavLink to="/recurring">Recurring</NavLink>
        <NavLink to="/groups">Groups</NavLink>
        <NavLink to="/budgets">Budgets</NavLink>
        <NavLink to="/analytics">Analytics</NavLink>
        <NavLink to="/alerts">
          Alerts{unreadCount > 0 && <span className="nav-badge">{unreadCount}</span>}
        </NavLink>
        {user?.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
      </nav>
      <button className="sidebar-logout" onClick={logout}>Log out</button>
    </aside>
  );
}