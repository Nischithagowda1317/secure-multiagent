import { useEffect, useState } from "react";
import { demoAccounts, login } from "../api";
import type { DemoAccount, UserProfile } from "../types";
import { ErrorBox, Loading } from "../components/UI";

export default function LoginPage({ onLogin }: { onLogin: (token: string, user: UserProfile) => void }) {
  const [accounts, setAccounts] = useState<DemoAccount[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("Demo@123!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    demoAccounts().then((items) => {
      setAccounts(items);
      const preferred = items.find((item) => item.roles.includes("Admin")) ?? items[0];
      if (preferred) setEmail(preferred.email);
    }).catch((err: Error) => setError(err.message));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await login(email, password);
      onLogin(response.access_token, response.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-hero">
        <div className="hero-badge">Secure enterprise intelligence</div>
        <h1>Autonomous workflows.<br />Deterministic security.</h1>
        <p>
          A complete academic implementation of multi-agent coordination, secure RAG,
          role-based access, human approval, explainability, and reliability monitoring.
        </p>
        <div className="hero-grid">
          <div><strong>11</strong><span>Specialized agents</span></div>
          <div><strong>12</strong><span>Workflow definitions</span></div>
          <div><strong>50</strong><span>Linked data tables</span></div>
          <div><strong>14</strong><span>Knowledge documents</span></div>
        </div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <div className="brand login-brand"><div className="brand-mark">NC</div><div><strong>NexaCore</strong><span>Enterprise AI Assistant</span></div></div>
          <h2>Sign in to the demonstration</h2>
          <p>Use any synthetic role account. The temporary password is already filled.</p>
          {error && <ErrorBox message={error} />}
          <form onSubmit={submit}>
            <label>Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
            <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
            <button className="primary-button" disabled={loading}>{loading ? "Signing in..." : "Sign in"}</button>
          </form>
          <div className="account-picker">
            <span>Quick role selection</span>
            {!accounts.length && !error ? <Loading label="Loading accounts" /> : (
              <div className="account-list">
                {accounts.map((account) => (
                  <button key={account.user_id} type="button" className={email === account.email ? "selected" : ""} onClick={() => { setEmail(account.email); setPassword(account.temporary_password); }}>
                    <strong>{account.roles.filter((role) => role !== "Employee").join(" / ") || "Employee"}</strong>
                    <small>{account.email}</small>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
