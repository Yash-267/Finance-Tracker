import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "../api";
import { useAuth } from "./AuthContext";

const NotificationContext = createContext(null);
const POLL_INTERVAL_MS = 30000;

export function NotificationProvider({ children }) {
  const { token } = useAuth();
  const [alerts, setAlerts] = useState([]);

  const refresh = useCallback(() => {
    if (!token) return;
    api.get("/budgets/alerts").then((res) => setAlerts(res.data)).catch(() => {});
  }, [token]);

  useEffect(() => {
    if (!token) {
      setAlerts([]);
      return;
    }
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [token, refresh]);

  async function markAsRead(id) {
    await api.patch(`/budgets/alerts/${id}/read`);
    refresh();
  }

  const unreadCount = alerts.filter((a) => !a.read).length;

  return (
    <NotificationContext.Provider value={{ alerts, unreadCount, refresh, markAsRead }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  return useContext(NotificationContext);
}