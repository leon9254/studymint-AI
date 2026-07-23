import {
  ChevronLeft,
  ChevronRight,
  FileText,
  Layers,
  Plus,
  Search,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { DocumentCard } from "../components/ui/DocumentCard";
import { EmptyState } from "../components/ui/EmptyState";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { StatusBadge } from "../components/ui/StatusBadge";
import { deleteDocument, listDocuments } from "../services/documentsApi";
import type { DocumentStatus, DocumentType, StudyDocument } from "../types";

const DOCUMENTS_PER_PAGE = 6;

const statuses: Array<DocumentStatus | "ALL"> = [
  "ALL",
  "DRAFT",
  "GENERATING",
  "READY_FOR_REVIEW",
  "PDF_READY",
  "MARKETPLACE_READY",
  "ARCHIVED",
];

const types: Array<DocumentType | "ALL"> = [
  "ALL",
  "Study Notes",
  "Summary",
  "Exam Prep",
  "Q&A Guide",
  "Study Guide",
  "Flashcard Pack",
];

export function DocumentsPage() {
  const [documents, setDocuments] = useState<StudyDocument[]>([]);
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<DocumentStatus | "ALL">("ALL");
  const [type, setType] = useState<DocumentType | "ALL">("ALL");
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    void listDocuments().then(setDocuments);
  }, []);

  useEffect(() => {
    setQuery(searchParams.get("query") ?? "");
  }, [searchParams]);

  const filtered = useMemo(
    () =>
      documents.filter((document) => {
        const searchable =
          `${document.title} ${document.subject}`.toLowerCase();
        const matchesQuery = searchable.includes(query.toLowerCase());
        const matchesStatus = status === "ALL" || document.status === status;
        const matchesType = type === "ALL" || document.document_type === type;

        return matchesQuery && matchesStatus && matchesType;
      }),
    [documents, query, status, type],
  );

  const readyCount = documents.filter(
    (document) =>
      document.status === "PDF_READY" ||
      document.status === "MARKETPLACE_READY",
  ).length;

  const totalPages = Math.max(
    1,
    Math.ceil(filtered.length / DOCUMENTS_PER_PAGE),
  );

  const visibleDocuments = useMemo(() => {
    const start = (currentPage - 1) * DOCUMENTS_PER_PAGE;
    return filtered.slice(start, start + DOCUMENTS_PER_PAGE);
  }, [filtered, currentPage]);

  useEffect(() => {
    setCurrentPage(1);
  }, [query, status, type]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const documentStart =
    filtered.length === 0 ? 0 : (currentPage - 1) * DOCUMENTS_PER_PAGE + 1;

  const documentEnd = Math.min(
    currentPage * DOCUMENTS_PER_PAGE,
    filtered.length,
  );

  async function remove(id: string) {
    await deleteDocument(id);
    setDocuments((current) => current.filter((document) => document.id !== id));
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto lg:overflow-hidden">
      <div className="flex min-h-full flex-col gap-3 lg:h-full lg:min-h-0">
        <div className="relative shrink-0 overflow-hidden rounded-[1.1rem] border border-white/70 bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.15),transparent_30%),linear-gradient(135deg,#ffffff_0%,#f8fafc_50%,#eefdf8_100%)] px-3.5 py-3.5 shadow-[0_18px_60px_-42px_rgba(15,23,42,0.7)] ring-1 ring-ink-100/70 sm:rounded-[1.35rem] sm:px-4 sm:py-4">
          <div className="absolute -right-8 -top-10 h-32 w-32 rounded-full bg-mint-200/35 blur-3xl" />
          <div className="absolute bottom-0 right-36 h-24 w-24 rounded-full bg-iris-200/25 blur-3xl" />

          <div className="relative flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-mint-700">
                Production Library
              </p>
              <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink-950 sm:text-2xl">
                Documents
              </h1>
              <p className="mt-1 max-w-2xl text-sm leading-5 text-ink-500">
                Search, filter, open, and manage every generated study asset in
                one compact workspace.
              </p>
            </div>

            <Link to="/documents/new">
              <Button icon={<Plus size={16} />}>Create</Button>
            </Link>
          </div>
        </div>

        <section className="shrink-0 rounded-[1.1rem] border border-ink-100/80 bg-white/90 p-3 shadow-[0_18px_60px_-46px_rgba(15,23,42,0.55)] ring-1 ring-white/80 backdrop-blur sm:rounded-[1.35rem]">
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-[360px_minmax(0,1fr)] xl:items-stretch">
            <div className="grid grid-cols-3 gap-1.5 sm:gap-2 xl:grid-cols-3">
              <div className="min-w-0 rounded-2xl border border-ink-100 bg-gradient-to-br from-white to-ink-50/70 p-2.5 sm:p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.17em] text-ink-400">
                    Library
                  </p>
                  <Layers size={15} className="text-mint-700" />
                </div>
                <p className="mt-1.5 text-xl font-semibold tracking-tight text-ink-950">
                  {documents.length}
                </p>
                <p className="mt-0.5 text-xs text-ink-500">Total</p>
              </div>

              <div className="min-w-0 rounded-2xl border border-ink-100 bg-gradient-to-br from-white to-mint-50/70 p-2.5 sm:p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.17em] text-ink-400">
                    Shown
                  </p>
                  <SlidersHorizontal size={15} className="text-iris-600" />
                </div>
                <p className="mt-1.5 text-xl font-semibold tracking-tight text-ink-950">
                  {filtered.length}
                </p>
                <p className="mt-0.5 text-xs text-ink-500">Filtered</p>
              </div>

              <div className="min-w-0 rounded-2xl border border-ink-100 bg-gradient-to-br from-white to-saffron-50/70 p-2.5 sm:p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.17em] text-ink-400">
                    Ready
                  </p>
                  <FileText size={15} className="text-saffron-600" />
                </div>
                <p className="mt-1.5 text-xl font-semibold tracking-tight text-ink-950">
                  {readyCount}
                </p>
                <p className="mt-0.5 text-xs text-ink-500">PDF/market</p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-2 rounded-2xl border border-ink-100 bg-ink-50/60 p-2.5 lg:grid-cols-[minmax(0,1fr)_190px_190px]">
              <div className="relative">
                <Search
                  size={16}
                  className="pointer-events-none absolute left-3 top-3 text-ink-400"
                />
                <Input
                  className="h-10 pl-9 text-sm"
                  placeholder="Search by title or subject"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>

              <Select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as DocumentStatus | "ALL")
                }
                options={statuses.map((item) => ({
                  label: item.replace(/_/g, " "),
                  value: item,
                }))}
              />

              <Select
                value={type}
                onChange={(event) =>
                  setType(event.target.value as DocumentType | "ALL")
                }
                options={types.map((item) => ({
                  label: item,
                  value: item,
                }))}
              />
            </div>
          </div>
        </section>

        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.1rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-48px_rgba(15,23,42,0.58)] ring-1 ring-white/80 backdrop-blur sm:rounded-[1.35rem]">
          <div className="shrink-0 border-b border-ink-100 bg-gradient-to-r from-white via-ink-50/60 to-mint-50/60 px-4 py-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-mint-700">
                  Document workspace
                </p>
                <div className="mt-1 flex flex-wrap items-end gap-x-3 gap-y-1">
                  <h2 className="text-base font-semibold tracking-tight text-ink-950">
                    All documents
                  </h2>
                  <p className="text-xs font-medium text-ink-500">
                    Showing {documentStart}-{documentEnd} of {filtered.length}
                  </p>
                </div>
              </div>

              {filtered.length > 0 && (
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
            </div>
          </div>

          {filtered.length === 0 ? (
            <div className="flex min-h-0 flex-1 items-center justify-center p-4">
              <EmptyState
                icon={<FileText size={20} />}
                title="No documents found"
                description="Adjust your filters or create a new study document."
              />
            </div>
          ) : (
            <>
              <div className="grid gap-3 overflow-y-auto p-3 sm:grid-cols-2 sm:p-4 lg:hidden">
                {visibleDocuments.map((document) => (
                  <div
                    key={document.id}
                    className="space-y-2 rounded-2xl border border-ink-100 bg-white p-2 shadow-sm"
                  >
                    <DocumentCard document={document} />
                    <Button
                      variant="danger"
                      size="sm"
                      icon={<Trash2 size={15} />}
                      onClick={() => void remove(document.id)}
                    >
                      Delete
                    </Button>
                  </div>
                ))}
              </div>

              <div className="hidden min-h-0 flex-1 overflow-hidden lg:block">
                <table className="h-full w-full min-w-[860px] table-fixed text-left text-sm">
                  <thead className="bg-ink-950 text-[10px] uppercase tracking-[0.16em] text-white/70">
                    <tr>
                      <th className="w-[31%] px-4 py-3 font-semibold">Title</th>
                      <th className="w-[20%] px-4 py-3 font-semibold">
                        Subject
                      </th>
                      <th className="w-[17%] px-4 py-3 font-semibold">Type</th>
                      <th className="w-[17%] px-4 py-3 font-semibold">
                        Status
                      </th>
                      <th className="w-[15%] px-4 py-3 font-semibold">
                        Actions
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-ink-100 bg-white">
                    {visibleDocuments.map((document) => (
                      <tr
                        key={document.id}
                        className="h-[48px] transition hover:bg-mint-50/40"
                      >
                        <td className="px-4 py-2.5">
                          <div className="min-w-0">
                            <Link
                              className="line-clamp-1 font-semibold text-ink-950 transition hover:text-mint-700"
                              to={`/documents/${document.id}/studio`}
                            >
                              {document.title}
                            </Link>
                            {document.generation_time_seconds != null && (
                              <p className="mt-1 text-xs font-medium text-mint-700">
                                Ready in{" "}
                                {Math.floor(
                                  document.generation_time_seconds / 60,
                                )}
                                :
                                {String(
                                  document.generation_time_seconds % 60,
                                ).padStart(2, "0")}
                              </p>
                            )}
                          </div>
                        </td>

                        <td className="px-4 py-2.5 text-ink-600">
                          <span className="line-clamp-1">
                            {document.subject}
                          </span>
                        </td>

                        <td className="px-4 py-2.5 text-ink-600">
                          <span className="line-clamp-1">
                            {document.document_type}
                          </span>
                        </td>

                        <td className="px-4 py-2.5">
                          <StatusBadge status={document.status} />
                        </td>

                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-2">
                            <Link to={`/documents/${document.id}/studio`}>
                              <Button variant="secondary" size="sm">
                                Open
                              </Button>
                            </Link>

                            <Button
                              variant="danger"
                              size="sm"
                              icon={<Trash2 size={14} />}
                              onClick={() => void remove(document.id)}
                            >
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}

                    {Array.from({
                      length: Math.max(
                        0,
                        DOCUMENTS_PER_PAGE - visibleDocuments.length,
                      ),
                    }).map((_, index) => (
                      <tr key={`empty-${index}`} className="h-[48px]">
                        <td
                          colSpan={5}
                          className="border-t border-dashed border-ink-100 px-4 py-2.5"
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
