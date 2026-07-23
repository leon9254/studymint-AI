import {
  Activity,
  ArrowRight,
  BarChart3,
  Building2,
  ChevronLeft,
  ChevronRight,
  Database,
  FileText,
  KeyRound,
  Layers3,
  MailWarning,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { StatCard } from "../components/ui/StatCard";
import { getAdminOverview, type AdminOverview } from "../services/adminApi";

const ADMIN_PANELS_PER_PAGE = 6;

const panels = [
  {
    title: "Manage users",
    description:
      "Review team access, user roles, and workspace-level permission controls.",
    icon: Users,
    accent: "bg-mint-50 text-mint-700 ring-mint-100",
  },
  {
    title: "Manage tenants/workspaces",
    description:
      "Oversee tenant accounts, workspace ownership, and organization setup.",
    icon: Building2,
    accent: "bg-iris-50 text-iris-700 ring-iris-100",
  },
  {
    title: "Manage templates",
    description:
      "Control active layouts, cover systems, and document generation styles.",
    icon: Layers3,
    accent: "bg-saffron-50 text-saffron-700 ring-saffron-100",
  },
  {
    title: "View generated documents",
    description:
      "Audit production output, review status, and marketplace readiness.",
    icon: FileText,
    accent: "bg-mint-50 text-mint-700 ring-mint-100",
  },
  {
    title: "View AI usage logs",
    description:
      "Track generation activity, AI events, credits, and usage trends.",
    icon: Activity,
    accent: "bg-ink-100 text-ink-800 ring-ink-200",
  },
  {
    title: "View audit logs",
    description:
      "Inspect admin changes, sensitive actions, and compliance-critical events.",
    icon: ScrollText,
    accent: "bg-iris-50 text-iris-700 ring-iris-100",
  },
  {
    title: "Manage system prompts",
    description:
      "Govern prompt behavior, quality rules, and AI safety guardrails.",
    icon: KeyRound,
    accent: "bg-saffron-50 text-saffron-700 ring-saffron-100",
  },
];

export function AdminPage() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    void getAdminOverview().then(setOverview);
  }, []);

  const totalEvents =
    (overview?.ai_usage_events ?? 0) + (overview?.audit_events ?? 0);

  const totalPages = Math.max(
    1,
    Math.ceil(panels.length / ADMIN_PANELS_PER_PAGE),
  );

  const visiblePanels = useMemo(() => {
    const start = (currentPage - 1) * ADMIN_PANELS_PER_PAGE;
    return panels.slice(start, start + ADMIN_PANELS_PER_PAGE);
  }, [currentPage]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const panelStart =
    panels.length === 0 ? 0 : (currentPage - 1) * ADMIN_PANELS_PER_PAGE + 1;

  const panelEnd = Math.min(currentPage * ADMIN_PANELS_PER_PAGE, panels.length);

  return (
    <div className="h-full min-h-0 overflow-y-auto xl:overflow-hidden">
      <div className="flex min-h-full flex-col gap-3 xl:h-full xl:min-h-0">
        <header className="relative shrink-0 overflow-hidden rounded-[1.05rem] border border-white/70 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.14),transparent_32%),linear-gradient(135deg,#ffffff_0%,#f8fafc_52%,#eef2ff_100%)] px-3.5 py-3 shadow-[0_18px_60px_-46px_rgba(15,23,42,0.65)] ring-1 ring-ink-100/70 sm:rounded-[1.15rem] sm:px-4">
          <div className="absolute -right-10 -top-10 h-24 w-24 rounded-full bg-mint-200/35 blur-3xl" />
          <div className="absolute bottom-0 right-40 h-16 w-16 rounded-full bg-iris-200/35 blur-3xl" />

          <div className="relative flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-mint-700">
                System command center
              </p>
              <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink-950 sm:text-2xl">
                Admin Panel
              </h1>
              <p className="mt-0.5 line-clamp-2 text-sm font-medium text-ink-500 sm:line-clamp-1">
                Role-gated control center for tenants, users, templates, AI
                usage, document visibility, and audit operations.
              </p>
            </div>

            <div className="header-kpi-grid">
              <div className="header-kpi">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Activity
                </p>
                <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                  {overview ? totalEvents : "-"}
                </p>
              </div>

              <div className="header-kpi">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Actions
                </p>
                <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                  {panelStart}-{panelEnd}
                </p>
              </div>

              <div className="header-kpi">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Pages
                </p>
                <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                  {currentPage}/{totalPages}
                </p>
              </div>
            </div>
          </div>
        </header>

        <div className="grid shrink-0 grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5">
          <StatCard
            label="Users"
            value={overview?.users ?? "-"}
            icon={<Users size={18} />}
            tone="mint"
          />
          <StatCard
            label="Tenants"
            value={overview?.tenants ?? "-"}
            icon={<Building2 size={18} />}
            tone="iris"
          />
          <StatCard
            label="Documents"
            value={overview?.generated_documents ?? "-"}
            icon={<FileText size={18} />}
            tone="saffron"
          />
          <StatCard
            label="AI usage logs"
            value={overview?.ai_usage_events ?? "-"}
            icon={<Activity size={18} />}
            tone="ink"
          />
          <StatCard
            label="Audit logs"
            value={overview?.audit_events ?? "-"}
            icon={<ScrollText size={18} />}
            tone="mint"
          />
        </div>

        <div className="grid shrink-0 grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
          <StatCard
            label="Active users"
            value={overview?.active_users ?? "-"}
            icon={<Users size={18} />}
            tone="mint"
          />
          <StatCard
            label="Unverified users"
            value={overview?.unverified_users ?? "-"}
            icon={<MailWarning size={18} />}
            tone="saffron"
          />
          <StatCard
            label="Admin users"
            value={overview?.admin_users ?? "-"}
            icon={<ShieldCheck size={18} />}
            tone="iris"
          />
          <StatCard
            label="Super admins"
            value={overview?.super_admins ?? "-"}
            icon={<KeyRound size={18} />}
            tone="ink"
          />
        </div>

        <section className="grid min-h-0 flex-1 grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_320px] 2xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="flex min-h-0 flex-col overflow-hidden rounded-[1.15rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80 backdrop-blur">
            <div className="shrink-0 border-b border-ink-100 bg-gradient-to-r from-white via-ink-50/70 to-mint-50/60 px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-mint-700">
                    Admin workflows
                  </p>
                  <h2 className="mt-1 text-base font-semibold tracking-tight text-ink-950">
                    Operational controls
                  </h2>
                </div>

                {panels.length > ADMIN_PANELS_PER_PAGE && (
                  <div className="flex items-center rounded-full border border-ink-100 bg-white p-1 shadow-sm">
                    <button
                      type="button"
                      disabled={currentPage === 1}
                      onClick={() =>
                        setCurrentPage((page) => Math.max(1, page - 1))
                      }
                      className="inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-35"
                      aria-label="Previous admin controls"
                    >
                      <ChevronLeft size={16} />
                    </button>

                    <span className="min-w-14 px-2 text-center text-xs font-semibold text-ink-600">
                      {currentPage}/{totalPages}
                    </span>

                    <button
                      type="button"
                      disabled={currentPage === totalPages}
                      onClick={() =>
                        setCurrentPage((page) => Math.min(totalPages, page + 1))
                      }
                      className="inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-35"
                      aria-label="Next admin controls"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-3 xl:overflow-hidden">
              <div className="grid min-h-0 grid-cols-1 gap-3 md:grid-cols-2 xl:h-full xl:grid-cols-3 xl:grid-rows-2">
                {visiblePanels.map((panel) => {
                  const Icon = panel.icon;

                  return (
                    <article
                      key={panel.title}
                      className="group flex min-h-0 flex-col overflow-hidden rounded-[1.05rem] border border-ink-100/80 bg-white p-3 shadow-[0_18px_60px_-52px_rgba(15,23,42,0.6)] ring-1 ring-white/80 transition hover:border-mint-200"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div
                          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ring-1 ${panel.accent}`}
                        >
                          <Icon size={16} />
                        </div>

                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-ink-100 bg-white text-ink-400 shadow-sm transition group-hover:border-mint-200 group-hover:text-mint-700">
                          <ArrowRight size={14} />
                        </div>
                      </div>

                      <h3 className="mt-3 line-clamp-1 text-sm font-semibold tracking-tight text-ink-950">
                        {panel.title}
                      </h3>

                      <p className="mt-1 line-clamp-3 text-xs leading-5 text-ink-600">
                        {panel.description}
                      </p>

                      <div className="mt-auto pt-3">
                        <div className="h-1.5 overflow-hidden rounded-full bg-ink-100">
                          <div className="h-full w-2/3 rounded-full bg-gradient-to-r from-mint-500 via-iris-500 to-saffron-400 opacity-80" />
                        </div>
                      </div>
                    </article>
                  );
                })}

                {Array.from({
                  length: Math.max(
                    0,
                    ADMIN_PANELS_PER_PAGE - visiblePanels.length,
                  ),
                }).map((_, index) => (
                  <div
                    key={`empty-admin-panel-${index}`}
                    className="hidden min-h-0 rounded-[1.05rem] border border-dashed border-ink-100 bg-ink-50/40 xl:block"
                  />
                ))}
              </div>
            </div>
          </div>

          <aside className="flex min-h-0 flex-col gap-3 overflow-hidden">
            <section className="shrink-0 overflow-hidden rounded-[1.15rem] border border-ink-100/80 bg-white/90 shadow-[0_18px_60px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80">
              <div className="bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.26),transparent_42%),linear-gradient(135deg,#111827,#172033)] px-3.5 py-3 text-white">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20">
                    <ShieldCheck size={17} />
                  </div>

                  <div>
                    <h2 className="text-sm font-semibold">
                      Admin security posture
                    </h2>
                    <p className="text-[11px] text-white/55">
                      Role-based operational controls
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2 p-2.5">
                {[
                  "RBAC-protected workflows",
                  "Audit-sensitive operations",
                  "Tenant-aware administration",
                ].map((item) => (
                  <div
                    key={item}
                    className="flex items-center gap-2 rounded-xl bg-ink-50/70 px-3 py-2 text-xs font-medium text-ink-700"
                  >
                    <ShieldCheck size={14} className="text-mint-700" />
                    <span className="line-clamp-1">{item}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.15rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80">
              <div className="shrink-0 border-b border-ink-100 bg-gradient-to-r from-white via-ink-50/70 to-iris-50/60 px-3.5 py-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-iris-50 text-iris-700 ring-1 ring-iris-100">
                    <BarChart3 size={17} />
                  </div>

                  <div>
                    <h2 className="text-sm font-semibold text-ink-950">
                      Operational snapshot
                    </h2>
                    <p className="text-[11px] text-ink-500">
                      Admin overview status
                    </p>
                  </div>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto p-2.5">
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-xl bg-ink-50/70 px-3 py-2 ring-1 ring-ink-100">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                      Tenants
                    </p>
                    <p className="mt-1 text-lg font-semibold text-ink-950">
                      {overview?.tenants ?? "-"}
                    </p>
                  </div>

                  <div className="rounded-xl bg-ink-50/70 px-3 py-2 ring-1 ring-ink-100">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                      Documents
                    </p>
                    <p className="mt-1 text-lg font-semibold text-ink-950">
                      {overview?.generated_documents ?? "-"}
                    </p>
                  </div>

                  <div className="rounded-xl bg-ink-50/70 px-3 py-2 ring-1 ring-ink-100">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                      AI events
                    </p>
                    <p className="mt-1 text-lg font-semibold text-ink-950">
                      {overview?.ai_usage_events ?? "-"}
                    </p>
                  </div>

                  <div className="rounded-xl bg-ink-50/70 px-3 py-2 ring-1 ring-ink-100">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                      Audit
                    </p>
                    <p className="mt-1 text-lg font-semibold text-ink-950">
                      {overview?.audit_events ?? "-"}
                    </p>
                  </div>
                </div>

                <div className="mt-2 rounded-2xl border border-mint-100 bg-mint-50 px-3 py-2 text-xs font-medium leading-5 text-mint-700">
                  <div className="flex items-center gap-2">
                    <Database size={14} />
                    Connected to admin overview API
                  </div>
                </div>

                <div className="mt-2 rounded-2xl border border-ink-100 bg-white px-3 py-2">
                  <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-ink-900">
                    <Users size={14} className="text-mint-700" />
                    Recent users
                  </div>
                  <div className="space-y-2">
                    {(overview?.recent_users ?? []).slice(0, 4).map((recentUser) => (
                      <div
                        key={recentUser.id}
                        className="rounded-xl border border-ink-100 bg-ink-50/70 px-3 py-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="truncate text-xs font-semibold text-ink-900">
                            {recentUser.full_name}
                          </p>
                          <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-[10px] font-bold uppercase text-ink-500 ring-1 ring-ink-100">
                            {recentUser.role.replace(/_/g, " ")}
                          </span>
                        </div>
                        <p className="mt-1 truncate text-[11px] text-ink-500">
                          {recentUser.email}
                        </p>
                      </div>
                    ))}
                    {overview?.recent_users?.length === 0 && (
                      <p className="text-xs text-ink-500">No users yet.</p>
                    )}
                  </div>
                </div>

                <div className="mt-2 rounded-2xl border border-ink-100 bg-white px-3 py-2 text-xs leading-5 text-ink-600">
                  <div className="mb-1 flex items-center gap-2 font-semibold text-ink-900">
                    <Sparkles size={14} className="text-iris-600" />
                    Admin note
                  </div>
                  Keep all high-risk actions protected with tenant checks, audit
                  trails, and least-privilege permissions.
                </div>
              </div>
            </section>
          </aside>
        </section>
      </div>
    </div>
  );
}
