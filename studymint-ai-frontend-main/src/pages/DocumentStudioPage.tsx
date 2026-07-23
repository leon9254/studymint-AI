import {
  BookOpenCheck,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileDown,
  Layers,
  Send,
  ShieldCheck,
  WandSparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { useDocumentStudio } from "../contexts/DocumentStudioContext";
import { getDocument } from "../services/documentsApi";
import { publishStuviaDocument } from "../services/stuviaAgentApi";

const aiActions = [
  "Regenerate section",
  "Make more detailed",
  "Simplify wording",
  "Add examples",
  "Improve formatting",
  "Add study questions",
  "Prepare for PDF",
];

const SECTIONS_PER_PAGE = 10;

export function DocumentStudioPage() {
  const { id } = useParams();
  const studio = useDocumentStudio();
  const [sectionPage, setSectionPage] = useState(1);
  const [isPublishingToStuvia, setIsPublishingToStuvia] = useState(false);
  const [publishMessage, setPublishMessage] = useState("");
  const [publishError, setPublishError] = useState("");

  useEffect(() => {
    if (!id) return;
    setPublishMessage("");
    setPublishError("");
    void getDocument(id).then(studio.loadDocument);
  }, [id]);

  const selectedSection = useMemo(
    () =>
      studio.sections.find(
        (section) => section.id === studio.selectedSectionId,
      ),
    [studio.sections, studio.selectedSectionId],
  );

  const selectedIndex = useMemo(
    () =>
      studio.sections.findIndex(
        (section) => section.id === studio.selectedSectionId,
      ),
    [studio.sections, studio.selectedSectionId],
  );

  const totalSectionPages = Math.max(
    1,
    Math.ceil(studio.sections.length / SECTIONS_PER_PAGE),
  );

  const sectionPageStart = (sectionPage - 1) * SECTIONS_PER_PAGE;
  const sectionPageEnd = Math.min(
    sectionPageStart + SECTIONS_PER_PAGE,
    studio.sections.length,
  );

  const visibleSectionButtons = studio.sections.slice(
    sectionPageStart,
    sectionPageEnd,
  );

  const canGoPreviousRange = sectionPage > 1;
  const canGoNextRange = sectionPage < totalSectionPages;

  const canGoPreviousSection = selectedIndex > 0;
  const canGoNextSection =
    selectedIndex >= 0 && selectedIndex < studio.sections.length - 1;

  const titlePage =
    studio.document?.latest_version?.content?.title_page ??
    studio.document?.title ??
    "Untitled document";

  const introduction =
    studio.document?.latest_version?.content?.introduction ??
    "No introduction available yet.";

  const isStuviaDocument = studio.document?.target_platform === "Stuvia";

  useEffect(() => {
    if (selectedIndex < 0) return;

    const activePage = Math.floor(selectedIndex / SECTIONS_PER_PAGE) + 1;

    if (activePage !== sectionPage) {
      setSectionPage(activePage);
    }
  }, [selectedIndex, sectionPage]);

  useEffect(() => {
    if (sectionPage > totalSectionPages) {
      setSectionPage(totalSectionPages);
    }
  }, [sectionPage, totalSectionPages]);

  function selectSectionPage(nextPage: number) {
    const safePage = Math.min(Math.max(nextPage, 1), totalSectionPages);
    const nextStart = (safePage - 1) * SECTIONS_PER_PAGE;
    const firstSectionInRange = studio.sections[nextStart];

    setSectionPage(safePage);

    if (firstSectionInRange) {
      studio.selectSection(firstSectionInRange.id);
    }
  }

  function goToPreviousRange() {
    if (!canGoPreviousRange) return;
    selectSectionPage(sectionPage - 1);
  }

  function goToNextRange() {
    if (!canGoNextRange) return;
    selectSectionPage(sectionPage + 1);
  }

  function goToPreviousSection() {
    if (!canGoPreviousSection) return;
    studio.selectSection(studio.sections[selectedIndex - 1].id);
  }

  function goToNextSection() {
    if (!canGoNextSection) return;
    studio.selectSection(studio.sections[selectedIndex + 1].id);
  }

  async function publishCurrentDocumentToStuvia() {
    if (!studio.document || isPublishingToStuvia) return;

    setIsPublishingToStuvia(true);
    setPublishMessage("");
    setPublishError("");

    try {
      const result = await publishStuviaDocument(studio.document.id);
      setPublishMessage(result.message);
    } catch (err) {
      setPublishError(
        err instanceof Error ? err.message : "Unable to publish this document to Stuvia.",
      );
    } finally {
      setIsPublishingToStuvia(false);
    }
  }

  if (!studio.document) {
    return (
      <div className="flex h-full min-h-0 items-center justify-center overflow-hidden">
        <div className="rounded-2xl border border-ink-100 bg-white px-5 py-4 text-sm font-medium text-ink-500 shadow-sm">
          Loading document studio...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto lg:overflow-hidden">
      <div className="flex min-h-full flex-col gap-3 lg:h-full lg:min-h-0">
        <header className="relative shrink-0 overflow-hidden rounded-[1.05rem] border border-white/70 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.14),transparent_30%),linear-gradient(135deg,#ffffff_0%,#f8fafc_54%,#eef2ff_100%)] px-3.5 py-3 shadow-[0_18px_60px_-46px_rgba(15,23,42,0.65)] ring-1 ring-ink-100/70 sm:rounded-[1.25rem] sm:px-4">
          <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-iris-200/35 blur-3xl" />
          <div className="absolute bottom-0 right-36 h-20 w-20 rounded-full bg-mint-200/35 blur-3xl" />

          <div className="relative flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-mint-700">
                Editing workspace
              </p>
              <h1 className="mt-1 line-clamp-1 text-xl font-semibold tracking-tight text-ink-950 sm:text-2xl">
                Document Studio
              </h1>
              <p className="mt-0.5 line-clamp-2 text-sm font-medium text-ink-500 sm:line-clamp-1">
                {studio.document.title}
              </p>
            </div>

            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center">
              {isStuviaDocument ? (
                <Button
                  icon={<Send size={15} />}
                  variant="primary"
                  size="sm"
                  className="w-full sm:w-auto"
                  disabled={isPublishingToStuvia}
                  onClick={publishCurrentDocumentToStuvia}
                >
                  {isPublishingToStuvia ? "Sending..." : "Publish to Stuvia"}
                </Button>
              ) : null}

              <Link className="w-full sm:w-auto" to={`/documents/${studio.document.id}/pdf`}>
                <Button
                  icon={<FileDown size={15} />}
                  variant={studio.isPreparingPdf ? "primary" : "secondary"}
                  size="sm"
                  className="w-full sm:w-auto"
                >
                  PDF Preview
                </Button>
              </Link>

              <div className="header-kpi-grid">
                <div className="header-kpi">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                      Sections
                    </p>
                    <Layers size={13} className="text-mint-700" />
                  </div>
                  <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                    {studio.sections.length}
                  </p>
                </div>

                <div className="header-kpi">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                      AI Tools
                    </p>
                    <WandSparkles size={13} className="text-iris-600" />
                  </div>
                  <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                    {aiActions.length}
                  </p>
                </div>

                <div className="header-kpi">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                      Review
                    </p>
                    <ShieldCheck size={13} className="text-saffron-600" />
                  </div>
                  <p className="mt-1 text-lg font-semibold leading-none text-ink-950">
                    Ready
                  </p>
                </div>
              </div>
            </div>
          </div>

          {publishMessage || publishError ? (
            <div
              className={`relative mt-3 rounded-xl border px-3 py-2 text-xs font-semibold ${
                publishError
                  ? "border-red-200 bg-red-50 text-red-700"
                  : "border-mint-200 bg-mint-50 text-mint-800"
              }`}
            >
              {publishError || publishMessage}
            </div>
          ) : null}
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-[230px_minmax(0,1fr)_246px] 2xl:grid-cols-[240px_minmax(0,1fr)_260px]">
          <aside className="order-2 flex min-h-0 flex-col overflow-hidden rounded-[1.1rem] border border-ink-100/80 bg-white/90 shadow-[0_18px_60px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80 sm:rounded-[1.25rem] lg:order-none">
            <div className="shrink-0 border-b border-ink-100 bg-ink-950 px-3.5 py-3 text-white">
              <h2 className="text-sm font-semibold">Document setup</h2>
              <p className="mt-0.5 text-[11px] font-medium text-white/50">
                Format and source details
              </p>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-2.5">
              <dl className="grid gap-1.5 sm:grid-cols-2 lg:block lg:space-y-1.5">
                {[
                  ["Subject", studio.document.subject],
                  ["Level", studio.document.education_level],
                  ["Type", studio.document.document_type],
                  ["Platform", studio.document.target_platform],
                  ["Language", studio.document.output_language],
                  ["Length", studio.document.length],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="flex items-center justify-between gap-3 rounded-xl border border-ink-100 bg-ink-50/70 px-3 py-2"
                  >
                    <dt className="text-[9px] font-semibold uppercase tracking-[0.14em] text-ink-400">
                      {label}
                    </dt>
                    <dd className="max-w-[120px] truncate text-right text-[11px] font-semibold text-ink-900">
                      {value}
                    </dd>
                  </div>
                ))}
              </dl>

              <div className="mt-2 rounded-2xl border border-mint-100 bg-mint-50/70 px-3 py-2.5 text-[11px] leading-4 text-mint-800">
                <p className="font-semibold">Navigation moved</p>
                <p className="mt-1 text-mint-700/80">
                  Use the question range controls above the editor to access all
                  sections.
                </p>
              </div>
            </div>
          </aside>

          <main className="order-1 flex min-h-[34rem] flex-col overflow-hidden rounded-[1.1rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80 sm:rounded-[1.25rem] lg:order-none lg:min-h-0">
            <div className="shrink-0 border-b border-ink-100 bg-gradient-to-r from-white via-ink-50/70 to-mint-50/60 px-3.5 py-2.5">
              <div className="flex flex-col gap-2.5">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-mint-50 text-mint-700 ring-1 ring-mint-100">
                      <BookOpenCheck size={16} />
                    </div>

                    <div className="min-w-0">
                      <p className="line-clamp-1 text-sm font-semibold text-ink-950">
                        {selectedSection?.title ?? "Editable document preview"}
                      </p>
                      <p className="mt-0.5 text-[11px] font-medium text-ink-500">
                        Question {selectedIndex >= 0 ? selectedIndex + 1 : 0} of{" "}
                        {studio.sections.length}
                      </p>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-2">
                    <div className="flex items-center rounded-full border border-ink-100 bg-white p-1 shadow-sm">
                      <button
                        type="button"
                        disabled={!canGoPreviousSection}
                        onClick={goToPreviousSection}
                        className="inline-flex h-7 w-7 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-35"
                        aria-label="Previous question"
                      >
                        <ChevronLeft size={15} />
                      </button>

                      <span className="min-w-12 px-1.5 text-center text-[11px] font-semibold text-ink-600">
                        {selectedIndex >= 0 ? selectedIndex + 1 : 0}/
                        {studio.sections.length}
                      </span>

                      <button
                        type="button"
                        disabled={!canGoNextSection}
                        onClick={goToNextSection}
                        className="inline-flex h-7 w-7 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-35"
                        aria-label="Next question"
                      >
                        <ChevronRight size={15} />
                      </button>
                    </div>

                    <span className="hidden rounded-full border border-mint-100 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-mint-700 sm:inline-flex">
                      Autosave-ready
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 rounded-2xl border border-ink-100 bg-white/80 px-2 py-1.5 shadow-sm">
                  <button
                    type="button"
                    disabled={!canGoPreviousRange}
                    onClick={goToPreviousRange}
                    className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-35"
                    aria-label="Previous question range"
                  >
                    <ChevronLeft size={16} />
                  </button>

                  <div className="flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto">
                    <span className="shrink-0 rounded-full bg-ink-950 px-3 py-1.5 text-[11px] font-semibold text-white">
                      {sectionPageStart + 1}-{sectionPageEnd}
                    </span>

                    {visibleSectionButtons.map((section, index) => {
                      const actualIndex = sectionPageStart + index;
                      const isActive = section.id === studio.selectedSectionId;

                      return (
                        <button
                          key={section.id}
                          type="button"
                          onClick={() => studio.selectSection(section.id)}
                          className={`inline-flex h-8 min-w-8 shrink-0 items-center justify-center rounded-full px-2 text-[11px] font-semibold transition ${
                            isActive
                              ? "bg-mint-600 text-white shadow-sm shadow-mint-700/20"
                              : "bg-ink-50 text-ink-600 hover:bg-mint-50 hover:text-mint-700"
                          }`}
                          title={section.title}
                        >
                          {actualIndex + 1}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    type="button"
                    disabled={!canGoNextRange}
                    onClick={goToNextRange}
                    className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-ink-600 transition hover:bg-ink-50 disabled:cursor-not-allowed disabled:opacity-35"
                    aria-label="Next question range"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-hidden p-2.5">
              <div className="shrink-0 rounded-2xl border border-ink-100 bg-gradient-to-br from-white to-ink-50/80 px-3.5 py-2.5">
                <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-ink-400">
                  Title page
                </p>
                <h2 className="mt-0.5 line-clamp-1 break-words text-base font-semibold leading-tight tracking-tight text-ink-950">
                  {titlePage}
                </h2>
              </div>

              <div className="shrink-0 rounded-2xl border border-mint-100 bg-mint-50/60 px-3.5 py-2 ring-1 ring-white/80">
                <p className="line-clamp-2 text-xs leading-5 text-ink-700">
                  {introduction}
                </p>
              </div>

              {selectedSection ? (
                <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white">
                  <div className="shrink-0 border-b border-ink-100 bg-ink-50/70 px-3.5 py-2">
                    <label htmlFor="section-body" className="text-[10px] font-semibold uppercase tracking-[0.16em] text-ink-400">
                      Section body
                    </label>
                  </div>

                  <textarea
                    id="section-body"
                    value={selectedSection.body}
                    onChange={(event) =>
                      studio.updateSection(
                        selectedSection.id,
                        event.target.value,
                      )
                    }
                    placeholder="Write the section content here"
                    className="min-h-0 flex-1 resize-none border-0 bg-white px-3.5 py-3 text-sm leading-6 text-ink-800 outline-none placeholder:text-ink-400 focus:ring-0"
                  />
                </div>
              ) : (
                <div className="flex min-h-0 flex-1 items-center justify-center rounded-2xl border border-dashed border-ink-200 bg-ink-50 p-5 text-sm text-ink-500">
                  Select a question to edit.
                </div>
              )}
            </div>
          </main>

          <aside className="order-3 flex min-h-0 flex-col overflow-hidden rounded-[1.1rem] border border-ink-100/80 bg-white/90 shadow-[0_20px_70px_-50px_rgba(15,23,42,0.58)] ring-1 ring-white/80 sm:rounded-[1.25rem] lg:order-none">
            <div className="shrink-0 bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.26),transparent_38%),linear-gradient(135deg,#111827,#172033)] px-3.5 py-3 text-white">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/10 text-white ring-1 ring-white/20">
                  <WandSparkles size={17} />
                </div>
                <div>
                  <h2 className="text-sm font-semibold">AI assistant</h2>
                  <p className="text-[11px] text-white/55">
                    Section refinement queue
                  </p>
                </div>
              </div>
            </div>

            <div className="grid min-h-0 flex-1 auto-rows-min grid-cols-1 gap-2 overflow-y-auto p-2.5 sm:grid-cols-2 lg:grid-cols-1">
              {aiActions.map((action) => (
                <Button
                  key={action}
                  variant="secondary"
                  size="sm"
                  className="h-9 w-full justify-center rounded-xl text-xs"
                  onClick={() => studio.applyAiAction(action)}
                >
                  {action}
                </Button>
              ))}
            </div>

            <div className="shrink-0 border-t border-ink-100 p-2.5">
              <div className="rounded-2xl border border-saffron-100 bg-saffron-50 px-3 py-2.5 text-[11px] leading-4 text-saffron-700">
                <div className="mb-1 flex items-center gap-1.5 font-semibold">
                  <CheckCircle2 size={14} />
                  Quality checkpoint
                </div>
                Review originality, citations, and brand alignment before
                export.
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
