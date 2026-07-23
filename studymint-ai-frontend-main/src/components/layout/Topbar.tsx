import { LogOut, Menu, Search } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { useTenant } from "../../contexts/TenantContext";

export function Topbar({ onOpenSidebar }: { onOpenSidebar: () => void }) {
  const { user, logout } = useAuth();
  const { tenant } = useTenant();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const initials = (user?.full_name ?? "StudyMint User")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  function onSearch(event: FormEvent) {
    event.preventDefault();
    const query = searchQuery.trim();
    navigate(
      query ? `/documents?query=${encodeURIComponent(query)}` : "/documents",
    );
  }

  return (
    <header className="z-30 shrink-0 border-b border-ink-200 bg-white/95 shadow-sm shadow-ink-900/[0.03] backdrop-blur">
      <div className="flex h-16 items-center justify-between gap-2 px-3 sm:h-[76px] sm:gap-3 sm:px-5 lg:px-8">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <button
            aria-label="Open navigation"
            onClick={onOpenSidebar}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-ink-300 bg-white text-ink-800 shadow-sm transition hover:-translate-y-0.5 hover:border-ink-400 hover:bg-ink-50 hover:text-ink-950 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-mint-100 lg:hidden"
          >
            <Menu size={19} />
          </button>

          <div className="min-w-0 md:hidden">
            <p className="truncate text-sm font-extrabold tracking-tight text-ink-950">
              StudyMint AI
            </p>
            <p className="truncate text-[10px] font-semibold uppercase tracking-[0.14em] text-mint-700">
              Workspace
            </p>
          </div>

          <form
            onSubmit={onSearch}
            className="hidden h-11 min-w-0 flex-1 items-center gap-3 rounded-2xl border border-ink-300 bg-ink-50 px-3.5 text-ink-600 shadow-sm shadow-ink-900/[0.02] transition focus-within:border-mint-600 focus-within:bg-white focus-within:ring-4 focus-within:ring-mint-100 md:flex lg:max-w-2xl"
          >
            <Search size={17} className="shrink-0 text-ink-500" />
            <input
              aria-label="Search documents"
              className="min-w-0 flex-1 bg-transparent text-sm font-medium text-ink-950 outline-none placeholder:text-ink-500"
              placeholder="Search documents, templates, citations..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </form>
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-3">
          <div className="hidden min-w-0 items-center gap-2 rounded-2xl border border-ink-200 bg-white px-3 py-2 shadow-sm shadow-ink-900/[0.02] sm:flex">
            <span className="h-2 w-2 rounded-full bg-mint-500 shadow-[0_0_0_4px_rgba(16,185,129,0.12)]" />
            <div className="min-w-0">
              <p className="truncate text-[11px] font-bold uppercase tracking-[0.16em] text-ink-500">
                Workspace
              </p>
              <p className="truncate text-xs font-bold text-ink-900">
                {tenant?.name ?? "StudyMint"}
              </p>
            </div>
          </div>

          <div className="flex min-w-0 items-center gap-2 rounded-2xl border border-ink-200 bg-white px-1.5 py-1.5 shadow-sm shadow-ink-900/[0.02] sm:gap-3 sm:px-2.5 sm:py-2">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-ink-950 text-sm font-extrabold text-white shadow-lg shadow-ink-900/12 ring-1 ring-ink-800">
              {initials || "SU"}
            </div>
            <div className="hidden min-w-0 pr-1 text-right sm:block">
              <p className="max-w-[12rem] truncate text-sm font-bold leading-5 text-ink-950">
                {user?.full_name ?? "StudyMint User"}
              </p>
              <p className="truncate text-xs font-medium text-ink-500">
                {user?.role?.replace(/_/g, " ").toLowerCase() ??
                  "workspace member"}
              </p>
            </div>
          </div>

          <button
            aria-label="Log out"
            title="Log out"
            onClick={logout}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-ink-300 bg-white text-ink-700 shadow-sm shadow-ink-900/[0.02] transition hover:-translate-y-0.5 hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-rose-100"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>

      <div className="border-t border-ink-100 px-3 pb-3 pt-2 md:hidden">
        <form
          onSubmit={onSearch}
          className="flex h-11 min-w-0 items-center gap-3 rounded-2xl border border-ink-300 bg-ink-50 px-3.5 text-ink-600 shadow-sm shadow-ink-900/[0.02] transition focus-within:border-mint-600 focus-within:bg-white focus-within:ring-4 focus-within:ring-mint-100"
        >
          <Search size={17} className="shrink-0 text-ink-500" />
          <input
            aria-label="Search documents"
            className="min-w-0 flex-1 bg-transparent text-sm font-medium text-ink-950 outline-none placeholder:text-ink-500"
            placeholder="Search documents"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </form>
      </div>
    </header>
  );
}
