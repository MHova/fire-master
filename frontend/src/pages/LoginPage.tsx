import { useState, useEffect, type FormEvent } from "react";
import { useLogin } from "../api/queries";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [demoMode, setDemoMode] = useState(false);
  const loginMutation = useLogin();
  const { login } = useAuth();

  useEffect(() => {
    fetch("/api/health").then(r => r.json()).then(data => {
      if (data.demo_mode) {
        setDemoMode(true);
        setUsername("admin");
        setPassword("YouGotThis2026");
      }
    }).catch(() => {});
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const data = await loginMutation.mutateAsync({ username, password });
      login(data.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  };

  return (
    <div className="flex flex-1 items-center justify-center min-h-screen bg-[var(--bg-primary)]">
      <form
        onSubmit={handleSubmit}
        className="w-80 p-8 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg"
      >
        <h1 className="mb-6 text-center" style={{ fontFamily: "'Instrument Serif', Georgia, serif", fontSize: "24px", fontWeight: 400, letterSpacing: "-0.3px" }}>
          <span className="text-[var(--text-primary)]">FIRE</span><span className="text-[var(--green)]">Master</span>
        </h1>
        {error && (
          <div className="mb-4 p-2 text-sm bg-[rgba(255,77,106,0.1)] text-[var(--red)] border border-[var(--red)] rounded">
            {error}
          </div>
        )}
        <div className="mb-4">
          <label className="block text-xs text-[var(--text-secondary)] mb-1.5">
            Username
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--bg-secondary)] border border-[var(--border)] rounded text-sm text-[var(--text-primary)] focus:border-[var(--blue)] focus:outline-none"
            autoFocus
          />
        </div>
        <div className="mb-6">
          <label className="block text-xs text-[var(--text-secondary)] mb-1.5">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--bg-secondary)] border border-[var(--border)] rounded text-sm text-[var(--text-primary)] focus:border-[var(--blue)] focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={loginMutation.isPending}
          className="w-full py-2.5 bg-[var(--green)] text-[var(--bg-primary)] font-medium rounded text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loginMutation.isPending ? "Signing in..." : "Sign In"}
        </button>
        {demoMode && (
          <p className="mt-4 text-center text-xs text-[var(--text-tertiary)]">
            Demo — just click Sign In
          </p>
        )}
      </form>
    </div>
  );
}
