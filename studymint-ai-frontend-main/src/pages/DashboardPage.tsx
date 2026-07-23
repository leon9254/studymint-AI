import {
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  FileCheck2,
  FileText,
  Gauge,
  Plus,
  Sparkles,
  WalletCards,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { DocumentCard } from "../components/ui/DocumentCard";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { StatCard } from "../components/ui/StatCard";
import { StatusBadge } from "../components/ui/StatusBadge";
import { getDashboardStats, listDocuments } from "../services/documentsApi";
import type { DashboardStats, StudyDocument } from "../types";

const DOCUMENTS_PER_PAGE = 5;

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [documents, setDocuments] = useState<StudyDocument[]>([]);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    void getDashboardStats().then(setStats);
    void listDocuments().then(setDocuments);
  }, []);

  const readinessRate = stats?.total_documents
    ? Math.round(((stats.marketplace_ready ?? 0) / stats.total_documents) * 100)
    : 0;

  const totalPages = Math.max(
    1,
    Math.ceil(documents.length / DOCUMENTS_PER_PAGE),
  );

  const visibleDocuments = useMemo(() => {
    const start = (currentPage - 1) * DOCUMENTS_PER_PAGE;
    return documents.slice(start, start + DOCUMENTS_PER_PAGE);
  }, [documents, currentPage]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const documentStart =
    documents.length === 0 ? 0 : (currentPage - 1) * DOCUMENTS_PER_PAGE + 1;

  const documentEnd = Math.min(
    currentPage * DOCUMENTS_PER_PAGE,
    documents.length,
  );

  return (
    <div className="h-full min-h-0 overflow-y-auto lg:overflow-hidden">
      <div className="flex min-h-full flex-col gap-3 sm:gap-4 lg:h-full lg:min-h-0">
        <div className="relative shrink-0 overflow-hidden rounded-[1.1rem] border border-white/70 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.16),transparent_30%),linear-gradient(135deg,#ffffff_0%,#f8fafc_48%,#eef6ff_100%)] px-3.5 py-3.5 shadow-[0_18px_60px_-42px_rgba(15,23,42,0.7)] ring-1 ring-ink-100/70 sm:rounded-[1.4rem] sm:px-5 sm:py-4">
          <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-mint-200/35 blur-3xl" />
          <div className="absolute bottom-0 right-32 h-24 w-24 rounded-full bg-iris-200/30 blur-3xl" />

          <div className="relative grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_300px] xl:items-center">
            <PageHeader
              title="Dashboard"
              description="A compact command center for production, PDF readiness, AI usage, and review progress."
              actions={
                <Link to="/documents/new">
                  <Button icon={<Plus size={16} />}>Create</Button>
                </Link>
              }
            />

            <div className="rounded-2xl border border-white/80 bg-white/75 p-3.5 shadow-sm backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-400">
                    Workspace readiness
                  </p>
                  <div className="mt-1.5 flex items-end gap-2">
                    <p className="text-2xl font-semibold tracking-tight text-ink-950">
                      {readinessRate}%
                    </p>
                    <p className="pb-1 text-xs font-medium text-ink-500">
                      ready
                    </p>
                  </div>
                </div>

                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-ink-950 text-white shadow-lg shadow-ink-900/20">
                  <Sparkles size={18} />
                </div>
              </div>

              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink-100">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-mint-500 via-iris-500 to-saffron-400"
                  style={{ width: `${readinessRate}%` }}
                />
              </div>

              <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-ink-600">
                <CheckCircle2 size={14} className="text-mint-600" />
                Marketplace-ready / total documents
              </div>
            </div>
          </div>
        </div>

        <div className="grid shrink-0 grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5">
          <StatCard
            label="Total documents"
            value={stats?.total_documents ?? "-"}
            icon={<FileText size={18} />}
            tone="mint"
          />
          <StatCard
            label="Drafts"
            value={stats?.drafts ?? "-"}
            icon={<Gauge size={18} />}
            tone="ink"
          />
          <StatCard
            label="PDFs exported"
            value={stats?.pdfs_exported ?? "-"}
            icon={<FileCheck2 size={18} />}
            tone="iris"
          />
          <StatCard
            label="Marketplace-ready"
            value={stats?.marketplace_ready ?? "-"}
            icon={<ClipboardCheck size={18} />}
            tone="saffron"
          />
          <StatCard
            label="AI credits used"
            value={stats?.ai_credits_used ?? "-"}
            icon={<WalletCards size={18} />}
            tone="mint"
          />
        </div>

        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.1rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-48px_rgba(15,23,42,0.58)] ring-1 ring-white/80 backdrop-blur sm:rounded-[1.4rem]">
          <div className="shrink-0 border-b border-ink-100 bg-gradient-to-r from-white via-ink-50/60 to-mint-50/60 px-4 py-3.5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-mint-700">
                  Latest production activity
                </p>
                <div className="mt-1 flex flex-wrap items-end gap-x-3 gap-y-1">
                  <h2 className="text-base font-semibold tracking-tight text-ink-950">
                    Recent documents
                  </h2>
                  <p className="text-xs font-medium text-ink-500">
                    Showing {documentStart}-{documentEnd} of {documents.length}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {documents.length > DOCUMENTS_PER_PAGE && (
                  <div className="flex items-center rounded-full border border-ink-100 bg-white p-1 shadow-sm">
                    <button
                      type="button"
                      disabled={currentPage === 1}
                      onClick={() =>
                        setCurrentPage((page) => Math.max(1, page - 1))
                      }
                      className="inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-35"
                      aria-label="Previous documents"
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
                      aria-label="Next documents"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                )}

                <Link
                  className="inline-flex h-9 items-center gap-1.5 rounded-full border border-ink-100 bg-white px-3 text-xs font-semibold text-ink-700 shadow-sm transition hover:border-mint-200 hover:text-mint-700"
                  to="/documents"
                >
                  Library
                  <ArrowRight size={15} />
                </Link>
              </div>
            </div>
          </div>

          {documents.length === 0 ? (
            <div className="flex min-h-0 flex-1 items-center justify-center p-4">
              <EmptyState
                icon={<FileText size={20} />}
                title="No documents yet"
                description="Create your first study document to populate the production dashboard."
              />
            </div>
          ) : (
            <>
              <div className="grid gap-3 overflow-y-auto p-3 sm:grid-cols-2 sm:p-4 lg:hidden">
                {visibleDocuments.map((document) => (
                  <DocumentCard key={document.id} document={document} />
                ))}
              </div>

              <div className="hidden min-h-0 flex-1 overflow-hidden lg:block">
                <table className="h-full w-full min-w-[760px] table-fixed text-left text-sm">
                  <thead className="bg-ink-950 text-[10px] uppercase tracking-[0.16em] text-white/70">
                    <tr>
                      <th className="w-[34%] px-4 py-3 font-semibold">Title</th>
                      <th className="w-[16%] px-4 py-3 font-semibold">Type</th>
                      <th className="w-[18%] px-4 py-3 font-semibold">
                        Platform
                      </th>
                      <th className="w-[17%] px-4 py-3 font-semibold">
                        Status
                      </th>
                      <th className="w-[15%] px-4 py-3 font-semibold">
                        Updated
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-ink-100 bg-white">
                    {visibleDocuments.map((document) => (
                      <tr
                        key={document.id}
                        className="h-[54px] transition hover:bg-mint-50/40"
                      >
                        <td className="px-4 py-3">
                          <Link
                            className="line-clamp-1 font-semibold text-ink-950 transition hover:text-mint-700"
                            to={`/documents/${document.id}/studio`}
                          >
                            {document.title}
                          </Link>
                        </td>

                        <td className="px-4 py-3 text-ink-600">
                          <span className="line-clamp-1">
                            {document.document_type}
                          </span>
                        </td>

                        <td className="px-4 py-3 text-ink-600">
                          <span className="line-clamp-1">
                            {document.target_platform}
                          </span>
                        </td>

                        <td className="px-4 py-3">
                          <StatusBadge status={document.status} />
                        </td>

                        <td className="px-4 py-3 text-ink-500">
                          {new Date(document.updated_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}

                    {Array.from({
                      length: Math.max(
                        0,
                        DOCUMENTS_PER_PAGE - visibleDocuments.length,
                      ),
                    }).map((_, index) => (
                      <tr key={`empty-${index}`} className="h-[54px]">
                        <td
                          colSpan={5}
                          className="border-t border-dashed border-ink-100 px-4 py-3"
                        >
                          <div className="h-2 w-full rounded-full bg-ink-50" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
