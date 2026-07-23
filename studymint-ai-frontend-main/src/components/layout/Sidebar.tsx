import {
  BarChart3,
  Bot,
  FileText,
  Layers3,
  Link2,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

const items = [
  { label: "Dashboard", to: "/dashboard", icon: BarChart3 },
  { label: "Agent", to: "/agent", icon: Bot },
  { label: "Documents", to: "/documents", icon: FileText },
  { label: "Templates", to: "/templates", icon: Layers3 },
  { label: "Integrations", to: "/integrations", icon: Link2 },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onClose?: () => void;
}

function Brand({ onClose }: { onClose?: () => void }) {
  return (
    <div className="flex h-[76px] shrink-0 items-center justify-between border-b border-ink-200 px-4">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-mint-700 text-white shadow-lg shadow-mint-900/15 ring-1 ring-mint-800">
          <Sparkles size={19} />
        </div>
        <div className="min-w-0">
          <p className="truncate text-[15px] font-extrabold tracking-tight text-ink-950">
            StudyMint AI
          </p>
          <p className="mt-0.5 truncate text-[11px] font-semibold uppercase tracking-[0.18em] text-mint-700">
            Document Suite
          </p>
        </div>
      </div>

      {onClose && (
        <button
          aria-label="Close navigation"
          onClick={onClose}
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-ink-300 bg-white text-ink-700 shadow-sm transition hover:-translate-y-0.5 hover:bg-ink-50 hover:text-ink-950 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-mint-100 lg:hidden"
        >
          <X size={18} />
        </button>
      )}
    </div>
  );
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "SUPER_ADMIN";

  return (
    <>
      <div className="px-4 pb-3 pt-4">
        <div className="rounded-2xl border border-ink-200 bg-white p-3 shadow-sm shadow-ink-900/5">
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-ink-500">
            Workspace health
          </p>
          <div className="mt-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-bold text-ink-900">Ready to export</p>
              <p className="mt-0.5 text-xs leading-5 text-ink-600">
                Citations and originality checks enabled.
              </p>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-mint-50 text-mint-800 ring-1 ring-mint-200">
              <ShieldCheck size={18} />
            </div>
          </div>
        </div>
      </div>

      <nav className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-3 py-2">
        <p className="px-3 pb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-ink-500">
          Main menu
        </p>
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `group relative flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition-all duration-200 ${
                isActive
                  ? "bg-mint-50 text-mint-900 shadow-sm ring-1 ring-mint-200"
                  : "text-ink-700 hover:-translate-y-0.5 hover:bg-ink-50 hover:text-ink-950 hover:shadow-sm"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`absolute left-0 top-1/2 h-8 w-1 -translate-y-1/2 rounded-r-full transition ${
                    isActive
                      ? "bg-mint-600 opacity-100"
                      : "bg-transparent opacity-0"
                  }`}
                />
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition ${
                    isActive
                      ? "bg-white text-mint-800 ring-1 ring-mint-200"
                      : "bg-white text-ink-600 ring-1 ring-ink-200 group-hover:bg-mint-50 group-hover:text-mint-800 group-hover:ring-mint-200"
                  }`}
                >
                  <item.icon size={18} />
                </span>
                <span className="truncate">{item.label}</span>
              </>
            )}
          </NavLink>
        ))}

        {isAdmin && (
          <div className="pt-3">
            <p className="px-3 pb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-ink-500">
              Admin
            </p>
            <NavLink
              to="/admin"
              onClick={onNavigate}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition-all duration-200 ${
                  isActive
                    ? "bg-mint-50 text-mint-900 shadow-sm ring-1 ring-mint-200"
                    : "text-ink-700 hover:-translate-y-0.5 hover:bg-ink-50 hover:text-ink-950 hover:shadow-sm"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={`absolute left-0 top-1/2 h-8 w-1 -translate-y-1/2 rounded-r-full transition ${
                      isActive
                        ? "bg-mint-600 opacity-100"
                        : "bg-transparent opacity-0"
                    }`}
                  />
                  <span
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition ${
                      isActive
                        ? "bg-white text-mint-800 ring-1 ring-mint-200"
                        : "bg-white text-ink-600 ring-1 ring-ink-200 group-hover:bg-mint-50 group-hover:text-mint-800 group-hover:ring-mint-200"
                    }`}
                  >
                    <ShieldCheck size={18} />
                  </span>
                  <span className="truncate">Admin</span>
                </>
              )}
            </NavLink>
          </div>
        )}
      </nav>

      <div className="shrink-0 border-t border-ink-200 p-4">
        <div className="rounded-3xl border border-mint-200 bg-mint-50 p-4 shadow-sm shadow-ink-900/5">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-mint-800">
            Review policy
          </p>
          <p className="mt-2 text-sm leading-5 text-ink-800">
            Confirm originality, citations, and brand alignment before every
            export.
          </p>
        </div>
      </div>
    </>
  );
}

export function Sidebar({ mobileOpen = false, onClose }: SidebarProps) {
  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            aria-label="Close navigation overlay"
            className="absolute inset-0 bg-ink-950/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <aside className="relative flex h-full w-[min(22rem,92vw)] flex-col border-r border-ink-200 bg-white shadow-2xl shadow-ink-950/20">
            <Brand onClose={onClose} />
            <SidebarBody onNavigate={onClose} />
          </aside>
        </div>
      )}

      <aside className="hidden h-full w-[18.5rem] shrink-0 flex-col border-r border-ink-200 bg-white shadow-[18px_0_40px_rgba(21,29,24,0.045)] lg:flex">
        <Brand />
        <SidebarBody />
      </aside>
    </>
  );
}
