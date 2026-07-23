import { useState, useEffect, type FormEvent } from "react";
import { useLogin } from "../api/queries";
import { useAuth } from "../hooks/useAuth";

const DEMO_CREDENTIALS = { username: "admin", password: "YouGotThis2026" };

// Once per page load: if auto-login fails we fall back to the form and must not
// re-attempt on any remount (belt-and-braces against redirect/remount loops).
let autoLoginAttempted = false;

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [demoMode, setDemoMode] = useState(false);
  // "checking": waiting on /api/health — render the bare card so demo visitors
  // never see a login form flash. "entering": demo auto-login in flight.
  // "form": normal login (self-host, or demo fallback if auto-login fails).
  const [phase, setPhase] = useState<"checking" | "entering" | "form">("checking");
  const loginMutation = useLogin();
  const { login } = useAuth();

  useEffect(() => {
    fetch("/api/health")
      .then(r => r.json())
      .then(async data => {
        if (!data.demo_mode) {
          setPhase("form");
          return;
        }
        // Public demo: the credentials are printed on the landing page anyway —
        // the login wall is pure friction, so walk straight in.
        setDemoMode(true);
        setUsername(DEMO_CREDENTIALS.username);
        setPassword(DEMO_CREDENTIALS.password);
        if (autoLoginAttempted) {
          setPhase("form");
          return;
        }
        autoLoginAttempted = true;
        setPhase("entering");
        try {
          const d = await loginMutation.mutateAsync(DEMO_CREDENTIALS);
          login(d.access_token);
        } catch {
          setPhase("form"); // e.g. rotated demo password — fall back to the prefilled form
        }
      })
      .catch(() => setPhase("form"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  if (phase !== "form") {
    return (
      <div className="flex flex-1 items-center justify-center min-h-screen bg-[var(--bg-primary)]">
        <div className="w-80 p-8 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg text-center">
          <h1 className="mb-2" style={{ fontFamily: "'Instrument Serif', Georgia, serif", fontSize: "24px", fontWeight: 400, letterSpacing: "-0.3px" }}>
            <span className="text-[var(--text-primary)]">FIRE</span><span className="text-[var(--green)]">Master</span>
          </h1>
          {phase === "entering" && (
            <p className="text-xs text-[var(--text-tertiary)]">Entering the demo&hellip;</p>
          )}
        </div>
      </div>
    );
  }

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
