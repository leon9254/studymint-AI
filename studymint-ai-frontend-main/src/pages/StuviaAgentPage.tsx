import {
  Bot,
  CheckCircle2,
  Circle,
  ExternalLink,
  FileText,
  Loader2,
  RadioTower,
  Send,
  Workflow,
  XCircle,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Textarea } from "../components/ui/Textarea";
import { listTemplates } from "../services/templatesApi";
import {
  getStuviaAgentRun,
  startStuviaAgentRun,
} from "../services/stuviaAgentApi";
import type {
  DifficultyMode,
  StuviaAgentPublishMode,
  StuviaAgentRun,
  StuviaAgentRunInput,
  Template,
} from "../types";

const educationLevels = [
  "Nursing School",
  "Undergraduate",
  "Graduate",
  "Professional Certification",
  "Continuing Education",
];

const questionCounts = [25, 50, 75, 100, 150, 200, 250, 300];

const topicCounts = [1, 2, 3, 4, 5, 6, 8, 10];

const difficulties: DifficultyMode[] = [
  "Mixed",
  "Foundational",
  "Intermediate",
  "Advanced",
];

const publishModes: Array<{ value: StuviaAgentPublishMode; label: string }> = [
  { value: "drafts_only", label: "Drafts only" },
  { value: "n8n_review", label: "Send for review" },
  { value: "n8n_auto_publish", label: "Auto-publish" },
];

const concurrencyOptions = [
  { value: "1", label: "1 steady" },
  { value: "3", label: "3 balanced" },
  { value: "5", label: "5 fast" },
  { value: "8", label: "8 high throughput" },
  { value: "10", label: "10 maximum" },
];

const stages = [
  { stage: "queued", label: "Queued", progress: 3 },
  { stage: "scraping_topics", label: "Scrape", progress: 12 },
  { stage: "ranking_topics", label: "Rank", progress: 24 },
  { stage: "generating_documents", label: "Generate", progress: 38 },
  { stage: "packaging_listings", label: "Package", progress: 86 },
  { stage: "n8n_review", label: "Publish", progress: 94 },
  { stage: "completed", label: "Done", progress: 100 },
];

function listingTone(listing: { status: string; error?: string | null }) {
  const status = listing.status.toLowerCase();
  if (listing.error || status.includes("failed")) {
    return {
      card: "border-red-200 bg-red-50/70",
      status: "text-red-700",
      button: "border-red-200 bg-white text-red-700 hover:bg-red-50",
    };
  }
  if (status.includes("submitted")) {
    return {
      card: "border-saffron-200 bg-saffron-50/70",
      status: "text-saffron-700",
      button: "border-saffron-200 bg-white text-saffron-700 hover:bg-saffron-50",
    };
  }
  return {
    card: "border-mint-100 bg-mint-50/60",
    status: "text-mint-700",
    button: "border-mint-200 bg-white text-mint-700 hover:bg-mint-50",
  };
}

const defaultForm: StuviaAgentRunInput = {
  profile_url: "https://www.stuvia.com/user/casewritters",
  manual_topics: [],
  max_topics: 3,
  question_count: 25,
  concurrency: 3,
  education_level: "Nursing School",
  document_type: "Question Bank",
  output_language: "English",
  length: "Medium",
  template_id: "",
  generation_mode: "GENERAL_KNOWLEDGE_DRAFT",
  user_instructions: "",
  source_notes: "",
  difficulty: "Mixed",
  publish_mode: "drafts_only",
  reset_topic_history: false,
};

export function StuviaAgentPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [form, setForm] = useState<StuviaAgentRunInput>(defaultForm);
  const [manualTopicText, setManualTopicText] = useState("");
  const [run, setRun] = useState<StuviaAgentRun | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void listTemplates()
      .then((items) => {
        setTemplates(items);
        setForm((current) => ({
          ...current,
          template_id:
            current.template_id ||
            items.find((template) => template.id === "exam_bundle_2026")?.id ||
            items[0]?.id ||
            "",
        }));
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Unable to load templates"),
      );
  }, []);

  useEffect(() => {
    if (!run || run.status === "COMPLETED" || run.status === "FAILED") return;

    const timer = window.setTimeout(() => {
      void getStuviaAgentRun(run.run_id)
        .then(setRun)
        .catch((err) =>
          setError(err instanceof Error ? err.message : "Unable to read agent status"),
        );
    }, 1500);

    return () => window.clearTimeout(timer);
  }, [run]);

  const topicLines = useMemo(
    () =>
      manualTopicText
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean),
    [manualTopicText],
  );

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setIsStarting(true);
    setRun(null);

    try {
      const nextRun = await startStuviaAgentRun({
        ...form,
        manual_topics: topicLines,
        template_id: form.template_id || undefined,
      });
      setRun(nextRun);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start agent");
    } finally {
      setIsStarting(false);
    }
  }

  function stageState(stage: (typeof stages)[number]) {
    if (!run) return "pending";
    if (run.status === "COMPLETED") return "complete";
    if (run.stage === stage.stage) return "active";
    if (run.progress >= stage.progress) return "complete";
    return "pending";
  }

  function stageIcon(stage: (typeof stages)[number]) {
    const state = stageState(stage);
    if (state === "complete") return <CheckCircle2 size={14} className="text-mint-600" />;
    if (state === "active") return <Loader2 size={14} className="animate-spin text-mint-700" />;
    return <Circle size={14} className="text-ink-300" />;
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto bg-ink-50/50">
      <div className="grid min-h-full gap-4 p-2 lg:grid-cols-[minmax(0,0.92fr)_minmax(360px,0.58fr)]">
        <form
          onSubmit={onSubmit}
          className="flex min-h-0 flex-col overflow-hidden rounded-[22px] border border-white/90 bg-white/95 shadow-[0_24px_80px_-58px_rgba(15,23,42,0.58)] ring-1 ring-ink-100/80"
        >
          <div className="flex items-center justify-between gap-3 border-b border-ink-100 bg-gradient-to-r from-white via-mint-50/50 to-iris-50/50 px-4 py-3.5">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-ink-950 text-white shadow-sm">
                <Bot size={18} />
              </span>
              <div className="min-w-0">
                <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-mint-700">
                  Stuvia agent
                </p>
                <h1 className="truncate text-lg font-bold tracking-tight text-ink-950">
                  Topic-to-document run
                </h1>
              </div>
            </div>
            <span className="hidden rounded-full border border-ink-100 bg-white px-3 py-1 text-xs font-bold text-ink-500 shadow-sm sm:inline-flex">
              {form.max_topics} topics
            </span>
          </div>

          {error && (
            <div className="mx-4 mt-4 flex items-start gap-2 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs leading-5 text-red-700">
              <XCircle size={15} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-12">
            <div className="sm:col-span-2 xl:col-span-12">
              <Input
                label="Public Stuvia source"
                value={form.profile_url}
                onChange={(event) =>
                  setForm({ ...form, profile_url: event.target.value })
                }
                placeholder="https://www.stuvia.com/user/casewritters"
                required
              />
            </div>

            <div className="xl:col-span-3">
              <Select
                label="Topics"
                value={String(form.max_topics)}
                options={topicCounts.map((count) => ({
                  value: String(count),
                  label: `${count} topic${count === 1 ? "" : "s"}`,
                }))}
                onChange={(event) =>
                  setForm({ ...form, max_topics: Number(event.target.value) })
                }
              />
            </div>

            <div className="xl:col-span-3">
              <Select
                label="Questions"
                value={String(form.question_count)}
                options={questionCounts.map((count) => ({
                  value: String(count),
                  label: `${count}`,
                }))}
                onChange={(event) =>
                  setForm({ ...form, question_count: Number(event.target.value) })
                }
              />
            </div>

            <div className="xl:col-span-3">
              <Select
                label="Concurrency"
                value={String(form.concurrency)}
                options={concurrencyOptions}
                onChange={(event) =>
                  setForm({ ...form, concurrency: Number(event.target.value) })
                }
              />
            </div>

            <div className="xl:col-span-3">
              <Select
                label="Handoff"
                value={form.publish_mode}
                options={publishModes}
                onChange={(event) =>
                  setForm({
                    ...form,
                    publish_mode: event.target.value as StuviaAgentPublishMode,
                  })
                }
              />
            </div>

            <label className="flex min-h-[68px] items-center gap-3 rounded-xl border border-ink-100 bg-ink-50/70 px-3 py-2 xl:col-span-3">
              <input
                type="checkbox"
                checked={Boolean(form.reset_topic_history)}
                onChange={(event) =>
                  setForm({ ...form, reset_topic_history: event.target.checked })
                }
                className="h-4 w-4 rounded border-ink-300 text-mint-700 focus:ring-mint-500"
              />
              <span className="text-xs font-bold text-ink-700">
                Clear used topic history
              </span>
            </label>

            <div className="xl:col-span-3">
              <Select
                label="Education"
                value={form.education_level}
                options={educationLevels.map((level) => ({
                  value: level,
                  label: level,
                }))}
                onChange={(event) =>
                  setForm({ ...form, education_level: event.target.value })
                }
              />
            </div>

            <div className="xl:col-span-3">
              <Select
                label="Difficulty"
                value={form.difficulty}
                options={difficulties.map((difficulty) => ({
                  value: difficulty,
                  label: difficulty,
                }))}
                onChange={(event) =>
                  setForm({ ...form, difficulty: event.target.value as DifficultyMode })
                }
              />
            </div>

            <div className="xl:col-span-3">
              <Select
                label="Template"
                value={form.template_id ?? ""}
                options={templates.map((template) => ({
                  value: template.id,
                  label: template.name,
                }))}
                onChange={(event) =>
                  setForm({ ...form, template_id: event.target.value })
                }
              />
            </div>

            <div className="sm:col-span-2 xl:col-span-6">
              <Textarea
                label="Manual topics"
                value={manualTopicText}
                onChange={(event) => setManualTopicText(event.target.value)}
                placeholder="One fallback topic per line"
                className="min-h-24"
              />
            </div>

            <div className="sm:col-span-2 xl:col-span-6">
              <Textarea
                label="Agent instructions"
                value={form.user_instructions ?? ""}
                onChange={(event) =>
                  setForm({ ...form, user_instructions: event.target.value })
                }
                placeholder="Scope, exclusions, or emphasis"
                className="min-h-24"
              />
            </div>
          </div>

          <div className="mt-auto border-t border-ink-100 bg-ink-50/70 p-3">
            <Button
              type="submit"
              className="w-full"
              size="lg"
              disabled={isStarting || templates.length === 0 || !!run && !["COMPLETED", "FAILED"].includes(run.status)}
              icon={isStarting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            >
              {isStarting ? "Starting agent..." : "Start agent"}
            </Button>
          </div>
        </form>

        <aside className="flex min-h-0 flex-col gap-4">
          <section className="overflow-hidden rounded-[22px] border border-white/90 bg-white/95 shadow-[0_24px_80px_-58px_rgba(15,23,42,0.58)] ring-1 ring-ink-100/80">
            <div className="bg-[linear-gradient(135deg,#0b100d,#1d1e37)] px-4 py-4 text-white">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/15">
                    {run?.status === "FAILED" ? (
                      <XCircle size={18} />
                    ) : run?.status === "COMPLETED" ? (
                      <CheckCircle2 size={18} />
                    ) : run ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <RadioTower size={18} />
                    )}
                  </span>
                  <div className="min-w-0">
                    <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-white/45">
                      Run status
                    </p>
                    <h2 className="mt-1 truncate text-sm font-bold">
                      {run?.stage_label ?? "Idle"}
                    </h2>
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-white/60">
                      {run?.message ?? "No active run."}
                    </p>
                  </div>
                </div>
                <span className="rounded-full bg-white/10 px-2.5 py-1 text-xs font-bold text-mint-100 ring-1 ring-white/10">
                  {run?.progress ?? 0}%
                </span>
              </div>
              <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    run?.status === "FAILED"
                      ? "bg-red-400"
                      : "bg-gradient-to-r from-mint-300 to-iris-300"
                  }`}
                  style={{ width: `${run?.progress ?? 0}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 p-3">
              {stages.map((stage) => (
                <div
                  key={stage.stage}
                  className={`flex min-w-0 items-center gap-1.5 rounded-xl border px-2 py-2 ${
                    stageState(stage) === "active"
                      ? "border-mint-200 bg-mint-50"
                      : "border-ink-100 bg-ink-50/70"
                  }`}
                >
                  {stageIcon(stage)}
                  <span className="truncate text-[10px] font-bold text-ink-700">
                    {stage.label}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section className="min-h-0 flex-1 overflow-hidden rounded-[22px] border border-white/90 bg-white/95 shadow-[0_24px_80px_-58px_rgba(15,23,42,0.58)] ring-1 ring-ink-100/80">
            <div className="flex items-center justify-between gap-3 border-b border-ink-100 px-4 py-3">
              <div className="flex min-w-0 items-center gap-2">
                <Workflow size={16} className="text-mint-700" />
                <h2 className="truncate text-sm font-bold text-ink-950">
                  Output queue
                </h2>
              </div>
              <span className="rounded-full bg-ink-50 px-2.5 py-1 text-[10px] font-bold text-ink-500 ring-1 ring-ink-100">
                {run?.n8n_status ?? "local"}
              </span>
            </div>

            <div className="max-h-[420px] space-y-3 overflow-y-auto p-3">
              {run?.topics.map((topic) => (
                <div key={`${topic.title}-${topic.score}`} className="rounded-2xl border border-ink-100 bg-ink-50/70 p-3">
                  <p className="line-clamp-1 text-sm font-bold text-ink-950">
                    {topic.title}
                  </p>
                  <p className="mt-1 line-clamp-1 text-xs font-medium text-ink-500">
                    {topic.topic}
                  </p>
                </div>
              ))}

              {run?.listings.map((listing) => {
                const tone = listingTone(listing);
                return (
                <div key={`${listing.title}-${listing.document_id ?? listing.status}`} className={`rounded-2xl border p-3 ${tone.card}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="line-clamp-1 text-sm font-bold text-ink-950">
                        {listing.title}
                      </p>
                      <p className={`mt-1 text-xs font-semibold ${tone.status}`}>
                        {listing.status.replace(/_/g, " ")}
                        {listing.attempts && listing.attempts > 1
                          ? ` - ${listing.attempts} attempts`
                          : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {listing.stuvia_url && (
                        <a
                          href={listing.stuvia_url}
                          target="_blank"
                          rel="noreferrer"
                          className={`inline-flex h-8 w-8 items-center justify-center rounded-md border shadow-sm transition ${tone.button}`}
                          aria-label="Open Stuvia listing"
                        >
                          <ExternalLink size={14} />
                        </a>
                      )}
                      {listing.document_id && (
                        <Link
                          to={`/documents/${listing.document_id}/studio`}
                          className={`inline-flex h-8 w-8 items-center justify-center rounded-md border shadow-sm transition ${tone.button}`}
                          aria-label="Open generated document"
                        >
                          <ExternalLink size={14} />
                        </Link>
                      )}
                    </div>
                  </div>
                  {listing.error && (
                    <p className="mt-2 line-clamp-2 text-xs leading-5 text-red-700">
                      {listing.error}
                    </p>
                  )}
                </div>
                );
              })}

              {!run && (
                <div className="flex min-h-52 flex-col items-center justify-center rounded-2xl border border-dashed border-ink-200 bg-ink-50/60 p-6 text-center">
                  <FileText size={22} className="text-ink-400" />
                  <p className="mt-2 text-sm font-bold text-ink-800">
                    No agent output yet
                  </p>
                </div>
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
