import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

export default function PasswordRecovery({ reset = false }) {
  const { hash } = useLocation();
  const token = new URLSearchParams(hash.slice(1)).get("token");
  const invalidLink = reset && !/^[A-Za-z0-9_-]{43}$/.test(token ?? "");
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const password = fields.get("password");
    if (reset && password !== fields.get("confirmation")) {
      setError("The passwords must match.");
      return;
    }
    setPending(true);
    setError("");
    try {
      if (reset) {
        await api.post("/auth/reset-password", { token, password });
        logout();
        navigate("/login", { replace: true, state: { passwordReset: true } });
      } else {
        await api.post("/auth/forgot-password", { email: fields.get("email") });
        setSent(true);
      }
    } catch (requestError) {
      setError(reset && requestError.response?.status === 400
        ? "This reset link is invalid or has expired. Request a new link."
        : "Couldn't complete the request. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="auth-page-split">
      <div className="auth-form-panel">
        <div className="auth-form-inner">
          <h1 className="auth-heading">{reset ? "Reset password" : "Forgot password?"}</h1>
          {invalidLink && <p role="alert">This reset link is invalid. Request a new link.</p>}
          {sent && <p role="status">If an account matches that email, a reset link will be sent.</p>}
          {!invalidLink && !sent && (
            <form onSubmit={handleSubmit}>
              {reset ? (
                <>
                  <div className="auth-field">
                    <label htmlFor="recovery-password">New password (at least 8 characters)</label>
                    <input id="recovery-password" name="password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required />
                  </div>
                  <div className="auth-field">
                    <label htmlFor="recovery-confirmation">Confirm new password</label>
                    <input id="recovery-confirmation" name="confirmation" type="password" autoComplete="new-password" maxLength={128} required />
                  </div>
                </>
              ) : (
                <div className="auth-field">
                  <label htmlFor="recovery-email">Account email</label>
                  <input id="recovery-email" name="email" type="email" autoComplete="email" maxLength={225} required />
                </div>
              )}
              {error && <p className="form-error" role="alert">{error}</p>}
              <button className="auth-submit-btn" disabled={pending}>
                {pending ? "Please wait…" : reset ? "Set new password" : "Send reset link"}
              </button>
            </form>
          )}
          <p className="auth-footer-text">
            {reset ? <Link to="/forgot-password">Request a new link</Link> : <Link to="/login">Back to sign in</Link>}
          </p>
        </div>
      </div>
    </main>
  );
}
