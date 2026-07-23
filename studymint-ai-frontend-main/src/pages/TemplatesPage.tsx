import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Eye,
  Layers3,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { listTemplates } from "../services/templatesApi";
import type { Template } from "../types";

const TEMPLATES_PER_PAGE = 4;

export function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    void listTemplates().then(setTemplates);
  }, []);

  const totalPages = Math.max(
    1,
    Math.ceil(templates.length / TEMPLATES_PER_PAGE),
  );

  const visibleTemplates = useMemo(() => {
    const start = (currentPage - 1) * TEMPLATES_PER_PAGE;
    return templates.slice(start, start + TEMPLATES_PER_PAGE);
  }, [templates, currentPage]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const templateStart =
    templates.length === 0 ? 0 : (currentPage - 1) * TEMPLATES_PER_PAGE + 1;

  const templateEnd = Math.min(
    currentPage * TEMPLATES_PER_PAGE,
    templates.length,
  );

  return (
    <div className="h-full min-h-0 overflow-y-auto xl:overflow-hidden">
      <div className="flex min-h-full flex-col gap-3 xl:h-full xl:min-h-0">
        <header className="relative shrink-0 overflow-hidden rounded-[1.05rem] border border-white/70 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.14),transparent_32%),linear-gradient(135deg,#ffffff_0%,#f8fafc_52%,#eef2ff_100%)] px-3.5 py-3 shadow-[0_18px_60px_-46px_rgba(15,23,42,0.65)] ring-1 ring-ink-100/70 sm:rounded-[1.15rem] sm:px-4">
          <div className="absolute -right-10 -top-10 h-24 w-24 rounded-full bg-mint-200/35 blur-3xl" />
          <div className="absolute bottom-0 right-40 h-16 w-16 rounded-full bg-iris-200/35 blur-3xl" />

          <div className="relative flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-mint-700">
                Layout system
              </p>
              <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink-950 sm:text-2xl">
                Templates
              </h1>
              <p className="mt-0.5 line-clamp-2 text-sm font-medium text-ink-500 sm:line-clamp-1">
                Manage PDF layouts, cover treatments, typography rules, and
                structured section systems.
              </p>
            </div>

            <div className="header-kpi-grid">
              <div className="header-kpi">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Layouts
                </p>
                <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                  {templates.length}
                </p>
              </div>

              <div className="header-kpi">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Showing
                </p>
                <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                  {templateStart}-{templateEnd}
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

        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.15rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80 backdrop-blur">
          <div className="shrink-0 border-b border-ink-100 bg-gradient-to-r from-white via-ink-50/70 to-mint-50/60 px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-mint-700">
                  Template library
                </p>
                <h2 className="mt-1 text-base font-semibold tracking-tight text-ink-950">
                  Active document layouts
                </h2>
              </div>

              {templates.length > TEMPLATES_PER_PAGE && (
                <div className="flex items-center rounded-full border border-ink-100 bg-white p-1 shadow-sm">
                  <button
                    type="button"
                    disabled={currentPage === 1}
                    onClick={() =>
                      setCurrentPage((page) => Math.max(1, page - 1))
                    }
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-35"
                    aria-label="Previous templates"
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
                    aria-label="Next templates"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              )}
            </div>
          </div>

          {templates.length === 0 ? (
            <div className="flex min-h-0 flex-1 items-center justify-center p-4">
              <EmptyState
                icon={<Layers3 size={20} />}
                title="No templates available"
                description="Template definitions will appear here after the backend returns active layouts."
              />
            </div>
          ) : (
            <div className="min-h-0 flex-1 overflow-y-auto p-3 xl:overflow-hidden">
              <div className="grid min-h-0 grid-cols-1 gap-3 md:grid-cols-2 xl:h-full xl:grid-cols-4">
                {visibleTemplates.map((template, index) => {
                  const templateNumber =
                    (currentPage - 1) * TEMPLATES_PER_PAGE + index + 1;

                  return (
                    <article
                      key={template.id}
                      className="group flex min-h-0 flex-col overflow-hidden rounded-[1.05rem] border border-ink-100/80 bg-white shadow-[0_18px_60px_-52px_rgba(15,23,42,0.6)] ring-1 ring-white/80 transition hover:border-mint-200"
                    >
                      <div className="relative shrink-0 overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.2),transparent_42%),linear-gradient(135deg,#0f172a,#172033)] px-3 py-3 text-white">
                        <div className="absolute -right-8 -top-8 h-20 w-20 rounded-full bg-white/10 blur-2xl" />

                        <div className="relative flex items-start justify-between gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/10 text-mint-100 ring-1 ring-white/20">
                            <Layers3 size={15} />
                          </div>

                          <span className="rounded-full border border-white/15 bg-white/10 px-2 py-0.5 text-[10px] font-semibold text-white/75 backdrop-blur">
                            {template.page_size}
                          </span>
                        </div>

                        <div className="relative mt-3">
                          <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-mint-100/80">
                            Template {String(templateNumber).padStart(2, "0")}
                          </p>

                          <h2 className="mt-1 line-clamp-1 text-sm font-semibold tracking-tight text-white">
                            {template.name}
                          </h2>

                          <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-white/65">
                            {template.description}
                          </p>
                        </div>
                      </div>

                      <div className="flex min-h-0 flex-1 flex-col gap-2 p-2.5">
                        <div className="rounded-xl border border-ink-100 bg-ink-50/70 px-2.5 py-2">
                          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-ink-900">
                            <BookOpenCheck
                              size={13}
                              className="text-mint-700"
                            />
                            Cover system
                          </div>
                          <p className="mt-1 line-clamp-3 text-[11px] leading-4 text-ink-600">
                            {template.cover_style}
                          </p>
                        </div>

                        <div className="rounded-xl border border-ink-100 bg-ink-50/70 px-2.5 py-2">
                          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-ink-900">
                            <CheckCircle2 size={13} className="text-iris-600" />
                            Section structure
                          </div>
                          <p className="mt-1 line-clamp-3 text-[11px] leading-4 text-ink-600">
                            {template.section_style}
                          </p>
                        </div>

                        <div className="mt-auto flex shrink-0 items-center gap-2 pt-1">
                          <Button
                            className="h-8 flex-1 text-xs"
                            variant="secondary"
                            size="sm"
                            icon={<Eye size={14} />}
                          >
                            Preview
                          </Button>

                          <button
                            className="flex h-8 w-8 items-center justify-center rounded-xl border border-ink-100 bg-white text-ink-500 shadow-sm transition hover:border-mint-200 hover:text-mint-700"
                            type="button"
                            aria-label={`Open ${template.name}`}
                          >
                            <ArrowRight size={14} />
                          </button>
                        </div>
                      </div>
                    </article>
                  );
                })}

                {Array.from({
                  length: Math.max(
                    0,
                    TEMPLATES_PER_PAGE - visibleTemplates.length,
                  ),
                }).map((_, index) => (
                  <div
                    key={`empty-template-${index}`}
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
