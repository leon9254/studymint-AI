import {
  Bot,
  Cable,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Lock,
  PlugZap,
  Save,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { Input } from "../components/ui/Input";
import {
  getStuviaIntegration,
  listIntegrations,
  updateStuviaIntegration,
} from "../services/integrationsApi";
import type {
  IntegrationCard,
  StuviaIntegrationConfig,
  StuviaIntegrationConfigUpdate,
} from "../types";

const INTEGRATIONS_PER_PAGE = 6;

export function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<IntegrationCard[]>([]);
  const [stuviaConfig, setStuviaConfig] =
    useState<StuviaIntegrationConfig | null>(null);
  const [stuviaForm, setStuviaForm] = useState<StuviaIntegrationConfigUpdate>({
    stuvia_email: "",
    stuvia_password: null,
    auto_publish_enabled: false,
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [isSavingStuvia, setIsSavingStuvia] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [connectionMessage, setConnectionMessage] = useState("");

  useEffect(() => {
    void refreshIntegrations().catch((err) =>
      setConnectionError(
        err instanceof Error ? err.message : "Unable to load integrations",
      ),
    );
  }, []);

  async function refreshIntegrations() {
    const [integrationItems, stuvia] = await Promise.all([
      listIntegrations(),
      getStuviaIntegration(),
    ]);

    setIntegrations(integrationItems);
    setStuviaConfig(stuvia);
    setStuviaForm({
      stuvia_email: stuvia.stuvia_email,
      stuvia_password: null,
      auto_publish_enabled: stuvia.auto_publish_enabled,
    });
  }

  async function saveStuviaConnection() {
    setConnectionError("");
    setConnectionMessage("");
    setIsSavingStuvia(true);

    try {
      const updated = await updateStuviaIntegration(stuviaForm);
      setStuviaConfig(updated);
      setStuviaForm({
        stuvia_email: updated.stuvia_email,
        stuvia_password: null,
        auto_publish_enabled: updated.auto_publish_enabled,
      });
      setConnectionMessage("Stuvia account connection saved.");
      void listIntegrations().then(setIntegrations);
    } catch (err) {
      setConnectionError(
        err instanceof Error ? err.message : "Unable to save Stuvia connection",
      );
    } finally {
      setIsSavingStuvia(false);
    }
  }

  const totalPages = Math.max(
    1,
    Math.ceil(integrations.length / INTEGRATIONS_PER_PAGE),
  );

  const visibleIntegrations = useMemo(() => {
    const start = (currentPage - 1) * INTEGRATIONS_PER_PAGE;
    return integrations.slice(start, start + INTEGRATIONS_PER_PAGE);
  }, [integrations, currentPage]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const integrationStart =
    integrations.length === 0
      ? 0
      : (currentPage - 1) * INTEGRATIONS_PER_PAGE + 1;

  const integrationEnd = Math.min(
    currentPage * INTEGRATIONS_PER_PAGE,
    integrations.length,
  );

  const requiredFieldsCount = integrations.reduce(
    (total, integration) => total + integration.required_fields.length,
    0,
  );

  function statusClass(status: string) {
    const value = status.toLowerCase();

    if (value.includes("active") || value.includes("connected")) {
      return "border-mint-100 bg-mint-50 text-mint-700";
    }

    if (value.includes("soon") || value.includes("pending")) {
      return "border-saffron-100 bg-saffron-50 text-saffron-700";
    }

    return "border-ink-100 bg-ink-50 text-ink-600";
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto xl:overflow-hidden">
      <div className="flex min-h-full flex-col gap-3 xl:h-full xl:min-h-0">
        <header className="relative shrink-0 overflow-hidden rounded-[1.05rem] border border-white/70 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.14),transparent_32%),linear-gradient(135deg,#ffffff_0%,#f8fafc_52%,#eef2ff_100%)] px-3.5 py-3 shadow-[0_18px_60px_-46px_rgba(15,23,42,0.65)] ring-1 ring-ink-100/70 sm:rounded-[1.15rem] sm:px-4">
          <div className="absolute -right-10 -top-10 h-24 w-24 rounded-full bg-iris-200/35 blur-3xl" />
          <div className="absolute bottom-0 right-40 h-16 w-16 rounded-full bg-mint-200/35 blur-3xl" />

          <div className="relative flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-mint-700">
                Workflow connections
              </p>
              <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink-950 sm:text-2xl">
                Integration Center
              </h1>
              <p className="mt-0.5 line-clamp-2 text-sm font-medium text-ink-500 sm:line-clamp-1">
                Connect publishing, export, listing, storage, and marketplace
                workflows from one document production workspace.
              </p>
            </div>

            <div className="header-kpi-grid">
              <div className="header-kpi">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Connectors
                </p>
                <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                  {integrations.length}
                </p>
              </div>

              <div className="header-kpi">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Showing
                </p>
                <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                  {integrationStart}-{integrationEnd}
                </p>
              </div>

              <div className="header-kpi">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Fields
                </p>
                <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                  {requiredFieldsCount}
                </p>
              </div>
            </div>
          </div>
        </header>

        <section className="shrink-0 overflow-hidden rounded-[1.15rem] border border-ink-100/80 bg-white/95 shadow-[0_18px_60px_-48px_rgba(15,23,42,0.55)] ring-1 ring-white/80">
          <div className="grid gap-0 lg:grid-cols-[280px_minmax(0,1fr)]">
            <div className="relative overflow-hidden bg-[linear-gradient(135deg,#0f172a,#172033_58%,#202942)] p-4 text-white">
              <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-mint-300/10 blur-2xl" />
              <div className="relative flex items-start justify-between gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10 text-mint-100 ring-1 ring-white/15">
                  <Cable size={18} />
                </span>
                <span
                  className={`rounded-full border px-2.5 py-1 text-[10px] font-bold ${
                    stuviaConfig?.connected
                      ? "border-mint-300/25 bg-mint-300/15 text-mint-100"
                      : "border-saffron-300/25 bg-saffron-300/15 text-saffron-100"
                  }`}
                >
                  {stuviaConfig?.status ?? "Loading"}
                </span>
              </div>

              <div className="relative mt-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-white/45">
                  Stuvia publishing
                </p>
                <h2 className="mt-1 text-base font-bold tracking-tight">
                  Connect Stuvia
                </h2>
                <p className="mt-2 text-xs leading-5 text-white/60">
                  Add the seller account used for Stuvia publishing. The
                  background automation layer stays hidden from tenant users.
                </p>
              </div>

              <div className="relative mt-4 grid gap-2">
                <Link
                  to="/agent"
                  className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md border border-mint-300/20 bg-mint-300/15 px-3 text-xs font-bold text-mint-100 transition hover:bg-mint-300/20"
                >
                  <Bot size={14} />
                  Open agent
                </Link>
              </div>
            </div>

            <div className="grid gap-3 p-3 sm:grid-cols-2 xl:grid-cols-12">
              <div className="sm:col-span-2 xl:col-span-5">
                <Input
                  label="Stuvia email"
                  type="email"
                  value={stuviaForm.stuvia_email}
                  onChange={(event) =>
                    setStuviaForm({
                      ...stuviaForm,
                      stuvia_email: event.target.value,
                    })
                  }
                  placeholder="seller@example.com"
                />
              </div>

              <div className="sm:col-span-2 xl:col-span-4">
                <Input
                  label="Stuvia password"
                  type="password"
                  value={stuviaForm.stuvia_password ?? ""}
                  onChange={(event) =>
                    setStuviaForm({
                      ...stuviaForm,
                      stuvia_password: event.target.value,
                    })
                  }
                  placeholder={
                    stuviaConfig?.stuvia_password_configured
                      ? "Saved - leave blank to keep"
                      : "Password"
                  }
                />
              </div>

              <div className="flex items-end gap-2 sm:col-span-2 xl:col-span-3">
                <label className="flex h-11 flex-1 cursor-pointer items-center justify-between rounded-md border border-ink-300 bg-white px-3 text-sm font-semibold text-ink-800 shadow-sm">
                  <span>Auto-publish</span>
                  <span className="relative inline-flex items-center">
                    <input
                      type="checkbox"
                      checked={stuviaForm.auto_publish_enabled}
                      onChange={(event) =>
                        setStuviaForm({
                          ...stuviaForm,
                          auto_publish_enabled: event.target.checked,
                        })
                      }
                      className="peer sr-only"
                    />
                    <span className="h-5 w-9 rounded-full bg-ink-200 transition peer-checked:bg-mint-600 peer-focus-visible:ring-4 peer-focus-visible:ring-mint-100" />
                    <span className="absolute left-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition peer-checked:translate-x-4" />
                  </span>
                </label>

                <Button
                  type="button"
                  icon={<Save size={15} />}
                  disabled={isSavingStuvia}
                  onClick={saveStuviaConnection}
                >
                  Save
                </Button>
              </div>

              <div className="sm:col-span-2 xl:col-span-12 grid gap-2 sm:grid-cols-3">
                <div className="rounded-xl border border-ink-100 bg-ink-50/70 px-3 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-400">
                    Account
                  </p>
                  <p className="mt-1 text-xs font-bold text-ink-800">
                    {stuviaConfig?.stuvia_email || "Not connected"}
                  </p>
                </div>
                <div className="rounded-xl border border-ink-100 bg-ink-50/70 px-3 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-400">
                    Automation
                  </p>
                  <p className="mt-1 text-xs font-bold text-ink-800">
                    {stuviaConfig?.automation_ready ? "Ready" : "Background setup needed"}
                  </p>
                </div>
                <div className="rounded-xl border border-ink-100 bg-ink-50/70 px-3 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-400">
                    Publishing
                  </p>
                  <p className="mt-1 text-xs font-bold text-ink-800">
                    {stuviaForm.auto_publish_enabled ? "Auto-publish on" : "Review mode"}
                  </p>
                </div>
              </div>

              {(connectionError || connectionMessage) && (
                <div
                  className={`sm:col-span-2 xl:col-span-12 rounded-xl border px-3 py-2 text-xs font-semibold ${
                    connectionError
                      ? "border-red-200 bg-red-50 text-red-700"
                      : "border-mint-200 bg-mint-50 text-mint-700"
                  }`}
                >
                  {connectionError || connectionMessage}
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.15rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80 backdrop-blur">
          <div className="shrink-0 border-b border-ink-100 bg-gradient-to-r from-white via-ink-50/70 to-mint-50/60 px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-mint-700">
                  Connector library
                </p>
                <h2 className="mt-1 text-base font-semibold tracking-tight text-ink-950">
                  Available workflow integrations
                </h2>
              </div>

              {integrations.length > INTEGRATIONS_PER_PAGE && (
                <div className="flex items-center rounded-full border border-ink-100 bg-white p-1 shadow-sm">
                  <button
                    type="button"
                    disabled={currentPage === 1}
                    onClick={() =>
                      setCurrentPage((page) => Math.max(1, page - 1))
                    }
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-35"
                    aria-label="Previous integrations"
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
                    aria-label="Next integrations"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>

          {integrations.length === 0 ? (
            <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_340px]">
              <div className="flex min-h-0 items-center justify-center p-4">
                <EmptyState
                  icon={<Cable size={20} />}
                  title="No integrations available"
                  description="Available channels will appear here after the backend returns integration definitions."
                />
              </div>

              <div className="hidden border-l border-ink-100 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.2),transparent_45%),linear-gradient(135deg,#111827,#172033)] p-5 text-white lg:flex lg:flex-col lg:justify-between">
                <div>
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/20">
                    <PlugZap size={20} />
                  </div>

                  <h2 className="mt-5 text-lg font-semibold tracking-tight">
                    Connector layer ready
                  </h2>

                  <p className="mt-2 text-sm leading-6 text-white/65">
                    This page is prepared for marketplace publishing, cloud
                    storage, listing workflows, export automation, and payment
                    connectors.
                  </p>
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/10 p-3 text-xs leading-5 text-white/70">
                  Secure integrations should use scoped permissions, encrypted
                  tokens, and manual review before publishing.
                </div>
              </div>
            </div>
          ) : (
            <div className="min-h-0 flex-1 overflow-y-auto p-3 xl:overflow-hidden">
              <div className="grid min-h-0 grid-cols-1 gap-3 md:grid-cols-2 xl:h-full xl:grid-cols-3 xl:grid-rows-2">
                {visibleIntegrations.map((integration) => (
                  <article
                    key={integration.id}
                    className="group flex min-h-0 flex-col overflow-hidden rounded-[1.05rem] border border-ink-100/80 bg-white shadow-[0_18px_60px_-52px_rgba(15,23,42,0.6)] ring-1 ring-white/80 transition hover:border-mint-200"
                  >
                    <div className="relative shrink-0 overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.22),transparent_42%),linear-gradient(135deg,#0f172a,#172033)] px-3 py-3 text-white">
                      <div className="absolute -right-8 -top-8 h-20 w-20 rounded-full bg-white/10 blur-2xl" />

                      <div className="relative flex items-start justify-between gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/10 text-mint-100 ring-1 ring-white/20">
                          <Cable size={15} />
                        </div>

                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${statusClass(
                            integration.status,
                          )}`}
                        >
                          {integration.status}
                        </span>
                      </div>

                      <div className="relative mt-3">
                        <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-mint-100/80">
                          Integration
                        </p>

                        <h2 className="mt-1 line-clamp-1 text-sm font-semibold tracking-tight text-white">
                          {integration.name}
                        </h2>

                        <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-white/65">
                          {integration.description}
                        </p>
                      </div>
                    </div>

                    <div className="flex min-h-0 flex-1 flex-col gap-2 p-2.5">
                      <div className="rounded-xl border border-ink-100 bg-ink-50/70 px-2.5 py-2">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-ink-900">
                          <ShieldCheck size={13} className="text-mint-700" />
                          Required fields
                        </div>

                        <div className="mt-2 grid gap-1.5">
                          {integration.required_fields
                            .slice(0, 4)
                            .map((field) => (
                              <div
                                key={field}
                                className="flex items-center gap-2 rounded-lg bg-white px-2 py-1.5 text-[11px] font-medium text-ink-600 ring-1 ring-ink-100"
                              >
                                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-mint-500" />
                                <span className="line-clamp-1">{field}</span>
                              </div>
                            ))}

                          {integration.required_fields.length > 4 && (
                            <div className="rounded-lg bg-mint-50 px-2 py-1.5 text-[11px] font-semibold text-mint-700 ring-1 ring-mint-100">
                              +{integration.required_fields.length - 4} more
                              required fields
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="mt-auto grid grid-cols-2 gap-2 pt-1">
                        <div className="rounded-xl border border-ink-100 bg-white px-2.5 py-2">
                          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-ink-900">
                            <CheckCircle2 size={13} className="text-iris-600" />
                            Secure handoff
                          </div>
                          <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-ink-500">
                            Prepared for scoped workflow access.
                          </p>
                        </div>

                        <Button
                          className="h-full min-h-16 rounded-xl text-xs"
                          variant="secondary"
                          size="sm"
                          icon={<Lock size={14} />}
                          disabled
                        >
                          Coming soon
                        </Button>
                      </div>
                    </div>
                  </article>
                ))}

                {Array.from({
                  length: Math.max(
                    0,
                    INTEGRATIONS_PER_PAGE - visibleIntegrations.length,
                  ),
                }).map((_, index) => (
                  <div
                    key={`empty-integration-${index}`}
                    className="hidden min-h-0 rounded-[1.05rem] border border-dashed border-ink-100 bg-ink-50/40 xl:block"
                  />
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
