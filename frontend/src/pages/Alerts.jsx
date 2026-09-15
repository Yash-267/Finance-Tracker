import { useNotifications } from "../context/NotificationContext";

export default function Alerts() {
  const { alerts, markAsRead } = useNotifications();

  return (
    <div className="page">
      <h1>Alerts</h1>

      {alerts.length === 0 && <p className="empty-note">No budget alerts yet.</p>}

      <div className="alert-list">
        {alerts.map((a) => (
          <div className={`alert-item ${a.read ? "" : "unread"}`} key={a.id}>
            <span>
              {!a.read && <span className="alert-dot" />}
              {a.message}
            </span>
            {!a.read && (
              <button className="link-button" onClick={() => markAsRead(a.id)}>Mark as read</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}