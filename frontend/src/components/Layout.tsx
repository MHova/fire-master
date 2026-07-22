import { useState, type ReactNode } from "react";
import { useAuth } from "../hooks/useAuth";
import { useSyncStatus } from "../api/queries";

const NAV_ITEMS = [
  { label: "Dashboard", path: "/", active: true },
  { label: "Runway", path: "/runway", active: true },
  { label: "Assets", path: "/assets", active: true },
  { label: "Spending", path: "/spending", active: true },
  { label: "Tracker", path: "/tracker", active: true },
  { label: "Transactions", path: "/transactions", active: true },
  { label: "Properties", path: "/properties", active: true },
  { label: "Retirement", path: "/retirement", active: true },
  { label: "Tax Planning", path: "/tax", active: true },
];

function Wordmark() {
  return (
    <h1 className="flex items-center gap-2" style={{ fontFamily: "'Instrument Serif', Georgia, serif", fontSize: "20px", fontWeight: 400, letterSpacing: "-0.3px" }}>
      <img src="/favicon.svg" alt="" className="w-6 h-6 rounded" />
      <span><span className="text-[var(--bg-primary)]">FIRE</span><span className="text-[var(--green)]">Master</span></span>
    </h1>
  );
}

function SidebarNav({ currentPath, onLogout }: { currentPath: string; onLogout: () => void }) {
  return (
    <ul className="flex-1 py-2 overflow-y-auto">
      {NAV_ITEMS.map((item) => {
        const isCurrent = item.path === "/" ? currentPath === "/" : currentPath.startsWith(item.path);
        return (
          <li key={item.path}>
            <a
              href={item.active ? item.path : undefined}
              className={`block px-5 py-2.5 text-sm ${
                !item.active
                  ? "text-[var(--text-secondary)] cursor-not-allowed opacity-50"
                  : isCurrent
                    ? "text-[var(--green)] bg-[rgba(0,212,170,0.08)]"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.03)] transition-colors"
              }`}
            >
              {item.label}
            </a>
          </li>
        );
      })}
      <li className="mt-2 pt-2 border-t border-[var(--sidebar-border)]">
        <a
          href="/settings"
          className={`flex items-center gap-2 px-5 py-2.5 text-sm transition-colors ${
            currentPath.startsWith("/settings") || currentPath.startsWith("/fire/config")
              ? "text-[var(--green)] bg-[rgba(0,212,170,0.08)]"
              : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.03)]"
          }`}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          Settings
        </a>
      </li>
      <li>
        <button
          onClick={onLogout}
          className="block w-full text-left px-5 py-2.5 text-sm text-[var(--text-secondary)] hover:text-[var(--red)] transition-colors"
        >
          Sign Out
        </button>
      </li>
    </ul>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { logout } = useAuth();
  const { data: syncStatus } = useSyncStatus();
  const [menuOpen, setMenuOpen] = useState(false);
  const currentPath = window.location.pathname;

  return (
    <div className="flex min-h-screen w-full">
      {/* Sidebar — static on desktop */}
      <nav className="hidden md:flex w-56 shrink-0 border-r border-[var(--sidebar-border)] bg-[var(--sidebar-bg)] flex-col">
        <div className="px-5 py-5 border-b border-[var(--sidebar-border)]">
          <Wordmark />
        </div>
        <SidebarNav currentPath={currentPath} onLogout={logout} />
      </nav>

      {/* Mobile nav drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMenuOpen(false)}
            aria-hidden="true"
          />
          <nav className="absolute inset-y-0 left-0 w-44 bg-[var(--sidebar-bg)] border-r border-[var(--sidebar-border)] flex flex-col">
            <div className="pl-4 pr-2 py-5 border-b border-[var(--sidebar-border)] flex items-center justify-between">
              <Wordmark />
              <button
                onClick={() => setMenuOpen(false)}
                aria-label="Close menu"
                className="p-1 shrink-0 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <SidebarNav currentPath={currentPath} onLogout={logout} />
          </nav>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 border-b border-[var(--border)] bg-[var(--bg-secondary)] flex items-center px-4 md:px-6 gap-4">
          <button
            onClick={() => setMenuOpen(true)}
            aria-label="Open menu"
            className="md:hidden p-1 -ml-1 text-[var(--text-primary)]"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
          </button>
          <span className="md:hidden text-sm font-semibold tracking-tight">
            <span className="text-[var(--text-primary)]">FIRE</span><span className="text-[var(--green)]">Master</span>
          </span>
          <div className="flex-1" />
          {syncStatus?.demo_mode ? (
            <span className="text-xs px-2 py-0.5 rounded border border-[var(--border)] bg-[var(--bg-secondary)] text-[var(--yellow)]">
              Demo mode
            </span>
          ) : syncStatus ? (
            <span className="text-xs text-[var(--text-secondary)]">
              Sync: {syncStatus.status}
              {syncStatus.last_sync_at &&
                ` · ${new Date(syncStatus.last_sync_at).toLocaleString()}`}
            </span>
          ) : null}
        </header>
        <main className="flex-1 p-4 md:p-6 overflow-auto">{children}</main>
      </div>

      {/* AI Advisor — disabled, Claude Code is the preferred analysis tool */}
      {/* <AdvisorPanel /> */}
    </div>
  );
}
