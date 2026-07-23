import {
  CheckCircle2,
  Download,
  FileCheck2,
  RefreshCcw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { createPdfExport, getDocument } from "../services/documentsApi";
import type { PdfExport, StudyDocument } from "../types";

const checklist = [
  "Original work confirmation",
  "Copyright warning",
  "Citation/source reminder",
  "No copied textbook/manual content",
  "No personal data",
  "No false claims",
  "User must review before publishing",
];

export function PdfPreviewPage() {
  const { id } = useParams();
  const [document, setDocument] = useState<StudyDocument | null>(null);
  const [pdfExport, setPdfExport] = useState<PdfExport | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [checkedItems, setCheckedItems] = useState<string[]>([]);

  const apiBase =
    import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1";

  const backendOrigin = apiBase.replace(/\/api\/v1\/?$/, "");

  const pdfHref = pdfExport?.pdf_url
    ? pdfExport.pdf_url.startsWith("http")
      ? pdfExport.pdf_url
      : `${backendOrigin}${pdfExport.pdf_url}`
    : "";

  const reviewProgress = Math.round(
    (checkedItems.length / checklist.length) * 100,
  );

  const exportStatus = pdfExport?.status ?? "Not generated";

  const statusTone = useMemo(() => {
    if (!pdfExport) return "idle";
    if (pdfExport.status === "FAILED") return "failed";
    if (pdfExport.status === "COMPLETED" || pdfHref) return "ready";
    return "working";
  }, [pdfExport, pdfHref]);

  useEffect(() => {
    if (!id) return;
    void getDocument(id).then(setDocument);
  }, [id]);

  async function generatePdf() {
    if (!id) return;

    setError("");
    setIsGenerating(true);

    try {
      const result = await createPdfExport(id);
      setPdfExport(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate PDF");
    } finally {
      setIsGenerating(false);
    }
  }

  function toggleChecklistItem(item: string) {
    setCheckedItems((current) =>
      current.includes(item)
        ? current.filter((existing) => existing !== item)
        : [...current, item],
    );
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto xl:overflow-hidden">
      <div className="flex min-h-full flex-col gap-3 xl:h-full xl:min-h-0">
        <header className="relative shrink-0 overflow-hidden rounded-[1.05rem] border border-white/70 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.14),transparent_32%),linear-gradient(135deg,#ffffff_0%,#f8fafc_52%,#eef2ff_100%)] px-3.5 py-3 shadow-[0_18px_60px_-46px_rgba(15,23,42,0.65)] ring-1 ring-ink-100/70 sm:rounded-[1.25rem] sm:px-4">
          <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-iris-200/35 blur-3xl" />
          <div className="absolute bottom-0 right-40 h-20 w-20 rounded-full bg-mint-200/35 blur-3xl" />

          <div className="relative flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-mint-700">
                Export workspace
              </p>
              <h1 className="mt-1 text-xl font-semibold tracking-tight text-ink-950 sm:text-2xl">
                PDF Preview
              </h1>
              <p className="mt-0.5 line-clamp-2 text-sm font-medium text-ink-500 sm:line-clamp-1">
                {document?.title ??
                  "Prepare, review, and download your final PDF export."}
              </p>
            </div>

            <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap sm:items-center">
              <Button
                onClick={generatePdf}
                icon={<RefreshCcw size={15} />}
                size="sm"
                className="w-full sm:w-auto"
                disabled={isGenerating}
              >
                {isGenerating
                  ? "Generating..."
                  : pdfHref
                    ? "Regenerate"
                    : "Generate PDF"}
              </Button>

              <Button
                type="button"
                size="sm"
                variant="secondary"
                icon={<Download size={15} />}
                className="w-full sm:w-auto"
                disabled={!pdfHref}
                onClick={() => pdfHref && window.open(pdfHref, "_blank")}
              >
                Download
              </Button>

              <div className="header-kpi sm:min-w-28">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Status
                </p>
                <p className="mt-1 line-clamp-1 text-sm font-semibold text-ink-950">
                  {exportStatus}
                </p>
              </div>

              <div className="header-kpi sm:min-w-28">
                <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                  Review
                </p>
                <p className="mt-1 text-sm font-semibold text-ink-950">
                  {checkedItems.length}/{checklist.length}
                </p>
              </div>
            </div>
          </div>
        </header>

        {error && (
          <div className="shrink-0 rounded-2xl border border-red-200 bg-red-50 px-3.5 py-3 text-xs leading-5 text-red-700 shadow-sm">
            {error}
          </div>
        )}

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_340px] 2xl:grid-cols-[minmax(0,1fr)_370px]">
          <section className="flex min-h-[32rem] flex-col overflow-hidden rounded-[1.1rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80 backdrop-blur sm:rounded-[1.25rem] xl:min-h-0">
            <div className="shrink-0 border-b border-ink-100 bg-gradient-to-r from-white via-ink-50/70 to-mint-50/60 px-4 py-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-mint-700">
                    Export canvas
                  </p>
                  <h2 className="mt-1 text-base font-semibold tracking-tight text-ink-950">
                    Generated PDF preview
                  </h2>
                </div>

                <div
                  className={`inline-flex w-fit items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-semibold ring-1 ${
                    statusTone === "ready"
                      ? "bg-mint-50 text-mint-700 ring-mint-100"
                      : statusTone === "failed"
                        ? "bg-red-50 text-red-700 ring-red-100"
                        : statusTone === "working"
                          ? "bg-iris-50 text-iris-700 ring-iris-100"
                          : "bg-ink-50 text-ink-600 ring-ink-100"
                  }`}
                >
                  {statusTone === "failed" ? (
                    <XCircle size={13} />
                  ) : (
                    <FileCheck2 size={13} />
                  )}
                  {exportStatus}
                </div>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-hidden p-2.5">
              <div className="flex h-full min-h-0 overflow-hidden rounded-2xl border border-ink-200 bg-[linear-gradient(135deg,#f8fafc,#eef2ff)] p-2 shadow-inner">
                {pdfHref ? (
                  <iframe
                    title="Generated PDF preview"
                    src={pdfHref}
                    className="h-full min-h-0 w-full rounded-xl bg-white"
                  />
                ) : (
                  <div className="flex min-h-0 flex-1 items-center justify-center rounded-xl border border-dashed border-ink-200 bg-white/75">
                    <div className="max-w-sm px-6 text-center">
                      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-ink-950 text-white shadow-xl shadow-ink-900/20">
                        <Download size={22} />
                      </div>

                      <h2 className="mt-4 text-lg font-semibold tracking-tight text-ink-950">
                        Generate a PDF preview
                      </h2>

                      <p className="mt-2 text-sm leading-6 text-ink-600">
                        Create an export to review the final layout before
                        downloading or publishing.
                      </p>

                      <Button
                        className="mt-4"
                        icon={<RefreshCcw size={15} />}
                        size="sm"
                        onClick={generatePdf}
                        disabled={isGenerating}
                      >
                        {isGenerating ? "Generating..." : "Generate PDF"}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {pdfExport && (
              <div className="shrink-0 border-t border-ink-100 bg-ink-50/70 px-3.5 py-2.5">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <p className="line-clamp-1 text-xs font-medium text-ink-600">
                    Export status:{" "}
                    <span className="font-semibold text-ink-900">
                      {pdfExport.status}
                    </span>
                  </p>

                  <Button
                    type="button"
                    size="sm"
                    icon={<Download size={15} />}
                    disabled={!pdfHref}
                    onClick={() => pdfHref && window.open(pdfHref, "_blank")}
                  >
                    Download PDF
                  </Button>
                </div>
              </div>
            )}
          </section>

          <aside className="flex min-h-0 flex-col gap-3 overflow-hidden">
            <section className="shrink-0 overflow-hidden rounded-[1.25rem] border border-ink-100/80 bg-white/90 shadow-[0_18px_60px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80">
              <div className="bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.26),transparent_42%),linear-gradient(135deg,#111827,#172033)] px-3.5 py-3 text-white">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20">
                      <FileCheck2 size={17} />
                    </div>

                    <div>
                      <h2 className="text-sm font-semibold">Export status</h2>
                      <p className="text-[11px] text-white/55">
                        PDF generation output
                      </p>
                    </div>
                  </div>

                  <span
                    className={`rounded-full px-2 py-1 text-[10px] font-semibold ${
                      statusTone === "ready"
                        ? "bg-mint-400/15 text-mint-100"
                        : statusTone === "failed"
                          ? "bg-red-400/15 text-red-100"
                          : "bg-white/10 text-white/70"
                    }`}
                  >
                    {exportStatus}
                  </span>
                </div>
              </div>

              <div className="p-3">
                <div className="rounded-2xl border border-ink-100 bg-ink-50/70 px-3 py-2.5">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                    File URL
                  </p>

                  <p className="mt-1 line-clamp-2 break-all text-xs leading-5 text-ink-600">
                    {pdfHref || "No export generated in this session."}
                  </p>
                </div>
              </div>
            </section>

            <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.25rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80">
              <div className="shrink-0 border-b border-ink-100 bg-gradient-to-r from-white via-ink-50/70 to-saffron-50/60 px-3.5 py-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-saffron-50 text-saffron-700 ring-1 ring-saffron-100">
                    <ShieldCheck size={17} />
                  </div>

                  <div>
                    <h2 className="text-sm font-semibold text-ink-950">
                      Marketplace checklist
                    </h2>
                    <p className="text-[11px] text-ink-500">
                      Final human review before publishing.
                    </p>
                  </div>
                </div>

                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-saffron-400 to-mint-500 transition-all"
                    style={{ width: `${reviewProgress}%` }}
                  />
                </div>

                <p className="mt-1.5 text-[11px] font-semibold text-ink-500">
                  {reviewProgress}% complete
                </p>
              </div>

              <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto p-2.5">
                {checklist.map((item) => {
                  const checked = checkedItems.includes(item);

                  return (
                    <label
                      key={item}
                      className={`flex cursor-pointer items-start gap-2.5 rounded-xl px-3 py-2 text-xs leading-5 transition ${
                        checked
                          ? "bg-mint-50 text-mint-800 ring-1 ring-mint-100"
                          : "bg-ink-50/70 text-ink-700 hover:bg-saffron-50/60"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleChecklistItem(item)}
                        className="mt-0.5 h-4 w-4 rounded border-ink-300 text-mint-600 focus:ring-mint-500"
                      />

                      <span className="font-medium">{item}</span>
                    </label>
                  );
                })}
              </div>

              <div className="shrink-0 border-t border-ink-100 p-2.5">
                <div className="flex items-center gap-2 rounded-2xl border border-mint-100 bg-mint-50 px-3 py-2.5 text-[11px] leading-4 text-mint-700">
                  <CheckCircle2 size={15} className="shrink-0" />
                  Complete this review before marketplace publishing.
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}
