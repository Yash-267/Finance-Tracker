import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function AdminRoute({ children }) {
  const { token, user } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  if (user === null) return null; // still fetching /auth/me
  if (user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}