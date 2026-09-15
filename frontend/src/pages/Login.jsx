import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const EyeIcon = (props) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon = (props) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
    <path d="M17.94 17.94A10.94 10.94 0 0 1 12 19c-7 0-11-7-11-7a21.6 21.6 0 0 1 5.06-6.06" />
    <path d="M9.9 4.24A10.6 10.6 0 0 1 12 4c7 0 11 7 11 7a21.4 21.4 0 0 1-3.22 4.44" />
    <path d="M1 1l22 22" />
    <path d="M9.53 9.53a3 3 0 0 0 4.24 4.24" />
  </svg>
);

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Couldn't log in — check your email and password.");
    }
  }

  return (
    <div className="auth-page-split">
      <div className="auth-image-panel">
        <div className="auth-logo-mark">Ledger</div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-form-inner">
          <div className="auth-animate" style={{ animationDelay: "0.05s" }}>
            <h1 className="auth-heading">Welcome<br />back</h1>
            <p className="auth-subtitle-lg">Sign in to keep track of your money.</p>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="auth-field auth-animate" style={{ animationDelay: "0.15s" }}>
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="auth-field auth-animate" style={{ animationDelay: "0.22s" }}>
              <label htmlFor="password">Password</label>
              <div className="password-field-wrap">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>

            {error && (
              <p className="form-error auth-animate" style={{ animationDelay: "0.28s" }}>{error}</p>
            )}

            <button type="submit" className="auth-submit-btn auth-animate" style={{ animationDelay: "0.3s" }}>
              Sign in
            </button>
          </form>

          <p className="auth-footer-text auth-animate" style={{ animationDelay: "0.38s" }}>
            No account? <Link to="/register">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}