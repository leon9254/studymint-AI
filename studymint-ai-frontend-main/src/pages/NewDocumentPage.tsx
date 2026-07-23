import {
  CheckCircle2,
  Circle,
  Eye,
  FileDown,
  Layers,
  Loader2,
  Sparkles,
  XCircle,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import {
  getDocument,
  getGenerationJob,
  startDocumentGeneration,
} from "../services/documentsApi";
import { listTemplates } from "../services/templatesApi";
import type {
  DocumentCreateInput,
  DifficultyMode,
  GenerationJob,
  GenerationMode,
  StudyDocument,
  TargetPlatform,
  Template,
} from "../types";

const platforms: TargetPlatform[] = ["Stuvia", "Docsity/DocCity", "Other"];

const courses = [
  "Nursing Exit Exam",
  "Fundamentals of Nursing",
  "Medical-Surgical Nursing",
  "Pharmacology",
  "Maternal-Newborn Nursing",
  "Pediatric Nursing",
  "Psychiatric-Mental Health Nursing",
  "Anatomy & Physiology",
  "Biology",
  "Business Law",
  "Economics",
  "Organic Chemistry",
  "Computer Science",
  "Psychology",
  "Other",
];

const educationLevels = [
  "High School",
  "Certificate",
  "Diploma",
  "Associate Degree",
  "Undergraduate",
  "Graduate",
  "Nursing School",
  "Medical School",
  "Professional Certification",
  "Continuing Education",
];

const questionCountOptions = [25, 50, 75, 100, 150, 200, 250, 300];

const difficultyOptions: Array<{ value: DifficultyMode; label: string }> = [
  { value: "Mixed", label: "Mixed difficulty" },
  { value: "Foundational", label: "Foundational" },
  { value: "Intermediate", label: "Intermediate" },
  { value: "Advanced", label: "Advanced" },
];

const generationModeOptions: Array<{
  value: GenerationMode;
  label: string;
  description: string;
}> = [
  {
    value: "GENERAL_KNOWLEDGE_DRAFT",
    label: "AI draft",
    description: "Generate from verified general knowledge.",
  },
  {
    value: "SOURCE_GROUNDED",
    label: "Source-grounded",
    description: "Prioritize the notes and material supplied below.",
  },
];

const visibleTemplateIds = [
  "exam_bundle_2026",
  "tpl_blue_certification_test_bank",
];

const generationStages = [
  { stage: "queued", label: "Queued", progress: 5 },
  { stage: "validating_template", label: "Template", progress: 12 },
  { stage: "generating_blueprint", label: "Blueprint", progress: 22 },
  { stage: "generating_batch", label: "Questions", progress: 35 },
  { stage: "generating_content", label: "AI content", progress: 35 },
  { stage: "validating_batch", label: "Validation", progress: 55 },
  { stage: "repairing_questions", label: "Quality fix", progress: 65 },
  { stage: "compiling_document", label: "Compile", progress: 78 },
  { stage: "extracting_content", label: "Extract", progress: 82 },
  { stage: "saving_document", label: "Save", progress: 90 },
  { stage: "preview_ready", label: "Preview", progress: 100 },
];

const labelClassName =
  "mb-1.5 block text-[10px] font-bold uppercase tracking-[0.12em] text-ink-500";

const controlClassName =
  "h-9 w-full rounded-xl border border-ink-200/90 bg-white px-3 text-[13px] font-medium text-ink-950 shadow-[0_1px_2px_rgba(15,23,42,0.04)] outline-none transition duration-200 placeholder:font-normal placeholder:text-ink-400 hover:border-ink-300 focus:border-mint-500 focus:ring-4 focus:ring-mint-100/80";

const textareaClassName =
  "h-[74px] w-full resize-none rounded-xl border border-ink-200/90 bg-white px-3 py-2.5 text-[13px] leading-5 text-ink-950 shadow-[0_1px_2px_rgba(15,23,42,0.04)] outline-none transition duration-200 placeholder:text-ink-400 hover:border-ink-300 focus:border-mint-500 focus:ring-4 focus:ring-mint-100/80 xl:h-[68px]";

export function NewDocumentPage() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [customCourse, setCustomCourse] = useState("");
  const [generationJob, setGenerationJob] = useState<GenerationJob | null>(
    null,
  );
  const [generatedDocument, setGeneratedDocument] =
    useState<StudyDocument | null>(null);

  const [selectedPlatforms, setSelectedPlatforms] = useState<TargetPlatform[]>([
    "Stuvia",
  ]);

  const [form, setForm] = useState<DocumentCreateInput>({
    title: "",
    subject: "Nursing Exit Exam",
    education_level: "Nursing School",
    document_type: "Question Bank",
    target_platform: "Stuvia",
    output_language: "English",
    length: "Medium",
    template_id: "",
    question_count: 25,
    generation_mode: "GENERAL_KNOWLEDGE_DRAFT",
    user_instructions: "",
    source_notes: "",
    difficulty: "Mixed",
    speed_mode: true,
  });

  useEffect(() => {
    void listTemplates()
      .then((items) => {
        setTemplates(items);

        setForm((current) => {
          const currentTemplateExists = items.some(
            (template) => template.id === current.template_id,
          );
          const preferredTemplate =
            items.find((template) =>
              visibleTemplateIds.includes(template.id),
            ) ?? items[0];

          return {
            ...current,
            template_id: currentTemplateExists
              ? current.template_id
              : preferredTemplate?.id || "",
          };
        });
      })
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : "Unable to load templates",
        ),
      );
  }, []);

  useEffect(() => {
    if (!generationJob || !isSubmitting) return;

    if (generationJob.status === "COMPLETED") {
      if (!generationJob.document_id) {
        setError("Generation completed, but no document ID was returned.");
        setIsSubmitting(false);
        return;
      }

      if (generatedDocument?.id === generationJob.document_id) return;

      void getDocument(generationJob.document_id)
        .then((document) => {
          setGeneratedDocument(document);
          setIsSubmitting(false);
        })
        .catch((err) => {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load generated preview",
          );
          setIsSubmitting(false);
        });

      return;
    }

    if (generationJob.status === "FAILED") {
      setError(
        generationJob.error ||
          generationJob.message ||
          "Document generation failed",
      );
      setIsSubmitting(false);
      return;
    }

    const timer = window.setTimeout(() => {
      void getGenerationJob(generationJob.job_id)
        .then(setGenerationJob)
        .catch((err) => {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to read generation status",
          );
          setIsSubmitting(false);
        });
    }, 1250);

    return () => window.clearTimeout(timer);
  }, [generatedDocument?.id, generationJob, isSubmitting]);

  const visibleTemplates = useMemo(
    () =>
      templates.filter((template) => visibleTemplateIds.includes(template.id)),
    [templates],
  );

  const selectedTemplate = useMemo(
    () => templates.find((template) => template.id === form.template_id),
    [form.template_id, templates],
  );

  const selectedGenerationMode = generationModeOptions.find(
    (mode) => mode.value === form.generation_mode,
  );

  const qualitySummary =
    generatedDocument?.latest_version?.content.metadata?.quality_summary;

  const generatedQuestionCount =
    generatedDocument?.latest_version?.content.question_bank?.length ?? 0;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();

    setError("");
    setIsSubmitting(true);
    setGeneratedDocument(null);
    setGenerationJob(null);

    try {
      const subject =
        form.subject === "Other" ? customCourse.trim() : form.subject;

      if (!subject) {
        setError("Enter a custom course before generating.");
        setIsSubmitting(false);
        return;
      }

      if (selectedPlatforms.length === 0) {
        setError("Select at least one target platform.");
        setIsSubmitting(false);
        return;
      }

      const job = await startDocumentGeneration({
        ...form,
        subject,
        target_platform: selectedPlatforms.join(", ") as TargetPlatform,
      });

      setGenerationJob(job);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to generate document",
      );
      setIsSubmitting(false);
    }
  }

  function stageState(stage: (typeof generationStages)[number]) {
    if (!generationJob) return "pending";
    if (generationJob.status === "COMPLETED") return "complete";

    if (generationJob.status === "FAILED") {
      return generationJob.progress >= stage.progress ? "complete" : "pending";
    }

    if (generationJob.stage === stage.stage) return "active";
    if (generationJob.progress >= stage.progress) return "complete";

    return "pending";
  }

  function stageIcon(stage: (typeof generationStages)[number]) {
    const state = stageState(stage);

    if (state === "complete") {
      return <CheckCircle2 size={13} className="text-mint-600" />;
    }

    if (state === "active") {
      return <Loader2 size={13} className="animate-spin text-mint-700" />;
    }

    return <Circle size={13} className="text-ink-300" />;
  }

  function openGeneratedDocument() {
    if (generatedDocument) {
      navigate(`/documents/${generatedDocument.id}/studio`);
    }
  }

  function openGeneratedPdf() {
    if (generatedDocument) {
      navigate(`/documents/${generatedDocument.id}/pdf`);
    }
  }

  return (
    <div className="relative h-full min-h-0 overflow-y-auto bg-ink-50/50 xl:overflow-hidden">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-mint-100/50 blur-3xl" />
        <div className="absolute -right-20 top-1/3 h-80 w-80 rounded-full bg-iris-100/45 blur-3xl" />
      </div>

      <div className="relative flex min-h-full flex-col gap-3 p-1 sm:p-2 xl:h-full xl:min-h-0">
        <header className="relative shrink-0 overflow-hidden rounded-[22px] border border-white/90 bg-white/85 px-4 py-3.5 shadow-[0_20px_70px_-52px_rgba(15,23,42,0.55)] ring-1 ring-ink-100/70 backdrop-blur-xl sm:px-5">
          <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-mint-400 via-mint-600 to-iris-500" />
          <div className="absolute -right-16 -top-20 h-48 w-48 rounded-full bg-mint-100/70 blur-3xl" />
          <div className="absolute -bottom-20 right-1/4 h-40 w-40 rounded-full bg-iris-100/70 blur-3xl" />

          <div className="relative flex items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-mint-500 to-mint-700 text-white shadow-[0_12px_28px_-12px_rgba(13,148,136,0.8)] ring-1 ring-white/40">
                <Sparkles size={18} />
              </span>

              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-[9px] font-extrabold uppercase tracking-[0.22em] text-mint-700">
                    AI document studio
                  </p>
                  <span className="hidden h-1 w-1 rounded-full bg-ink-300 sm:block" />
                  <p className="hidden text-[10px] font-semibold text-ink-400 sm:block">
                    Question bank builder
                  </p>
                </div>
                <h1 className="mt-0.5 truncate text-lg font-bold tracking-[-0.02em] text-ink-950 sm:text-xl">
                  Create a polished study document
                </h1>
                <p className="mt-0.5 hidden max-w-2xl text-xs leading-5 text-ink-500 lg:block">
                  Shape the academic brief, choose a layout, and generate a
                  publication-ready question bank.
                </p>
              </div>
            </div>

            <div className="hidden shrink-0 items-center gap-2 md:flex">
              {[
                ["Questions", String(form.question_count ?? 25)],
                ["Difficulty", form.difficulty],
                ["Page", selectedTemplate?.page_size ?? "Auto"],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="min-w-[92px] rounded-2xl border border-white bg-white/75 px-3 py-2 shadow-[0_8px_24px_-18px_rgba(15,23,42,0.5)] ring-1 ring-ink-100/70 backdrop-blur"
                >
                  <p className="text-[8px] font-extrabold uppercase tracking-[0.16em] text-ink-400">
                    {label}
                  </p>
                  <p className="mt-0.5 truncate text-xs font-bold text-ink-900">
                    {value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </header>

        <form
          onSubmit={onSubmit}
          className="flex min-h-0 flex-1 flex-col gap-3 xl:grid xl:grid-cols-[minmax(0,1fr)_350px] 2xl:grid-cols-[minmax(0,1fr)_378px]"
        >
          <main className="flex min-h-0 flex-col gap-3 xl:h-full">
            {error && (
              <div className="flex shrink-0 items-start gap-2 rounded-2xl border border-red-200/90 bg-red-50/90 px-3.5 py-2.5 text-xs leading-5 text-red-700 shadow-sm">
                <XCircle size={15} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[22px] border border-white/90 bg-white/90 shadow-[0_24px_80px_-58px_rgba(15,23,42,0.58)] ring-1 ring-ink-100/80 backdrop-blur-xl">
              <div className="flex shrink-0 items-center justify-between gap-3 border-b border-ink-100/80 bg-gradient-to-r from-white via-white to-mint-50/60 px-4 py-3 sm:px-5">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-mint-50 text-mint-700 ring-1 ring-mint-100">
                    <Layers size={15} />
                  </span>
                  <div>
                    <p className="text-[9px] font-extrabold uppercase tracking-[0.18em] text-mint-700">
                      Generation brief
                    </p>
                    <h2 className="mt-0.5 text-sm font-bold text-ink-950">
                      Document settings
                    </h2>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 rounded-full border border-mint-100 bg-white px-2.5 py-1 text-[10px] font-bold text-mint-700 shadow-sm">
                  <span className="h-1.5 w-1.5 rounded-full bg-mint-500" />
                  {form.question_count ?? 25} questions
                </div>
              </div>

              <div className="flex-1 p-3.5 sm:p-4 xl:min-h-0 xl:overflow-hidden">
                <div className="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2 lg:grid-cols-12 xl:h-full xl:content-start">
                  <label
                    className={
                      form.subject === "Other"
                        ? "lg:col-span-3"
                        : "lg:col-span-6"
                    }
                  >
                    <span className={labelClassName}>Document title</span>
                    <input
                      className={controlClassName}
                      value={form.title}
                      onChange={(event) =>
                        setForm({ ...form, title: event.target.value })
                      }
                      placeholder="e.g. QSP Certification Test Bank"
                      required
                    />
                  </label>

                  <label className="lg:col-span-3">
                    <span className={labelClassName}>Course</span>
                    <select
                      className={controlClassName}
                      value={form.subject}
                      onChange={(event) =>
                        setForm({ ...form, subject: event.target.value })
                      }
                    >
                      {courses.map((course) => (
                        <option key={course} value={course}>
                          {course}
                        </option>
                      ))}
                    </select>
                  </label>

                  {form.subject === "Other" && (
                    <label className="lg:col-span-3">
                      <span className={labelClassName}>Custom course</span>
                      <input
                        className={controlClassName}
                        value={customCourse}
                        onChange={(event) =>
                          setCustomCourse(event.target.value)
                        }
                        placeholder="Exact course name"
                        required
                      />
                    </label>
                  )}

                  <label className="lg:col-span-3">
                    <span className={labelClassName}>Education level</span>
                    <select
                      className={controlClassName}
                      value={form.education_level}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          education_level: event.target.value,
                        })
                      }
                    >
                      {educationLevels.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </label>

                  <div className="lg:col-span-3">
                    <span className={labelClassName}>Document type</span>
                    <div className="flex h-9 items-center gap-2 rounded-xl border border-ink-200/90 bg-ink-50/80 px-3 text-[13px] font-bold text-ink-800">
                      <span className="flex h-5 w-5 items-center justify-center rounded-md bg-white text-mint-700 shadow-sm ring-1 ring-ink-100">
                        <CheckCircle2 size={12} />
                      </span>
                      Question Bank
                    </div>
                  </div>

                  <label className="lg:col-span-3">
                    <span className={labelClassName}>Question count</span>
                    <select
                      className={controlClassName}
                      value={String(form.question_count ?? 25)}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          question_count: Number(event.target.value),
                        })
                      }
                    >
                      {questionCountOptions.map((count) => (
                        <option key={count} value={count}>
                          {count} questions
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="lg:col-span-3">
                    <span className={labelClassName}>Difficulty</span>
                    <select
                      className={controlClassName}
                      value={form.difficulty}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          difficulty: event.target.value as DifficultyMode,
                        })
                      }
                    >
                      {difficultyOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="lg:col-span-3">
                    <span className={labelClassName}>Output language</span>
                    <input
                      className={controlClassName}
                      value={form.output_language}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          output_language: event.target.value,
                        })
                      }
                      required
                    />
                  </label>

                  <div className="sm:col-span-2 lg:col-span-7">
                    <span className={labelClassName}>Target platforms</span>
                    <div className="flex min-h-9 flex-wrap items-center gap-1.5 rounded-xl border border-ink-200/90 bg-ink-50/65 p-1">
                      {platforms.map((platform) => {
                        const selected = selectedPlatforms.includes(platform);

                        return (
                          <button
                            type="button"
                            key={platform}
                            aria-pressed={selected}
                            onClick={() => {
                              setSelectedPlatforms((current) =>
                                current.includes(platform)
                                  ? current.filter((item) => item !== platform)
                                  : [...current, platform],
                              );
                            }}
                            className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] font-bold transition duration-200 ${
                              selected
                                ? "border-mint-200 bg-white text-mint-800 shadow-sm ring-1 ring-mint-100"
                                : "border-transparent text-ink-500 hover:border-ink-100 hover:bg-white hover:text-ink-800"
                            }`}
                          >
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${
                                selected ? "bg-mint-500" : "bg-ink-300"
                              }`}
                            />
                            {platform}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="lg:col-span-5">
                    <span className={labelClassName}>
                      Generation preference
                    </span>
                    <div className="grid grid-cols-[minmax(0,1fr)_112px] gap-2">
                      <select
                        className={controlClassName}
                        value={form.generation_mode}
                        onChange={(event) =>
                          setForm({
                            ...form,
                            generation_mode: event.target
                              .value as GenerationMode,
                          })
                        }
                      >
                        {generationModeOptions.map((mode) => (
                          <option key={mode.value} value={mode.value}>
                            {mode.label}
                          </option>
                        ))}
                      </select>

                      <label className="flex h-9 cursor-pointer items-center justify-between rounded-xl border border-ink-200/90 bg-white px-2.5 text-[11px] font-bold text-ink-700 shadow-sm">
                        <span>Fast mode</span>
                        <span className="relative inline-flex items-center">
                          <input
                            type="checkbox"
                            checked={form.speed_mode ?? false}
                            onChange={(event) =>
                              setForm((current) => ({
                                ...current,
                                speed_mode: event.target.checked,
                              }))
                            }
                            className="peer sr-only"
                          />
                          <span className="h-5 w-9 rounded-full bg-ink-200 transition peer-checked:bg-mint-600 peer-focus-visible:ring-4 peer-focus-visible:ring-mint-100" />
                          <span className="absolute left-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition peer-checked:translate-x-4" />
                        </span>
                      </label>
                    </div>
                  </div>

                  <label className="sm:col-span-2 lg:col-span-6">
                    <span className={labelClassName}>
                      Learning objectives or instructions
                    </span>
                    <textarea
                      className={textareaClassName}
                      value={form.user_instructions ?? ""}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          user_instructions: event.target.value,
                        })
                      }
                      placeholder="Topics to emphasize, scope, exclusions, or assessment goals"
                    />
                  </label>

                  <label className="sm:col-span-2 lg:col-span-6">
                    <span className={labelClassName}>Source notes</span>
                    <textarea
                      className={`${textareaClassName} ${
                        form.generation_mode === "SOURCE_GROUNDED"
                          ? "border-mint-300 bg-mint-50/30"
                          : ""
                      }`}
                      value={form.source_notes ?? ""}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          source_notes: event.target.value,
                        })
                      }
                      placeholder="Paste source material for grounded generation"
                    />
                  </label>

                  <div className="hidden items-center justify-between rounded-xl border border-ink-100 bg-ink-50/55 px-3 py-2 text-[10px] text-ink-500 lg:col-span-12 xl:flex">
                    <span>
                      <strong className="font-bold text-ink-700">
                        {selectedGenerationMode?.label}:
                      </strong>{" "}
                      {selectedGenerationMode?.description}
                    </span>
                    <span className="font-semibold text-ink-400">
                      Template content is never copied.
                    </span>
                  </div>
                </div>
              </div>
            </section>
          </main>

          <aside className="flex min-h-0 flex-col gap-3 xl:h-full">
            <section className="flex min-h-0 flex-col overflow-hidden rounded-[22px] border border-white/90 bg-white/90 shadow-[0_24px_80px_-58px_rgba(15,23,42,0.58)] ring-1 ring-ink-100/80 backdrop-blur-xl xl:flex-1">
              <div className="flex shrink-0 items-center justify-between gap-3 border-b border-ink-100/80 bg-gradient-to-r from-white via-white to-iris-50/60 px-4 py-3">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-iris-50 text-iris-600 ring-1 ring-iris-100">
                    <Layers size={15} />
                  </span>
                  <div>
                    <p className="text-[9px] font-extrabold uppercase tracking-[0.18em] text-iris-600">
                      Visual system
                    </p>
                    <h2 className="mt-0.5 text-sm font-bold text-ink-950">
                      Choose a layout
                    </h2>
                  </div>
                </div>

                <span className="rounded-full border border-ink-100 bg-white px-2.5 py-1 text-[10px] font-bold text-ink-500 shadow-sm">
                  {visibleTemplates.length} styles
                </span>
              </div>

              <div className="grid gap-2.5 p-3 sm:grid-cols-2 xl:min-h-0 xl:flex-1 xl:grid-cols-1 xl:content-start xl:overflow-hidden">
                {visibleTemplates.map((template, index) => {
                  const selected = form.template_id === template.id;

                  return (
                    <label
                      key={template.id}
                      className={`group relative cursor-pointer overflow-hidden rounded-2xl border p-2.5 transition duration-200 ${
                        selected
                          ? "border-mint-400 bg-gradient-to-br from-mint-50/90 to-white shadow-[0_14px_34px_-24px_rgba(13,148,136,0.75)] ring-2 ring-mint-100"
                          : "border-ink-100 bg-white hover:-translate-y-0.5 hover:border-ink-200 hover:shadow-[0_14px_32px_-26px_rgba(15,23,42,0.5)]"
                      }`}
                    >
                      <input
                        className="sr-only"
                        type="radio"
                        name="template"
                        value={template.id}
                        checked={selected}
                        onChange={() =>
                          setForm({ ...form, template_id: template.id })
                        }
                      />

                      {selected && (
                        <span className="absolute right-2 top-2 z-10 flex h-5 w-5 items-center justify-center rounded-full bg-mint-600 text-white shadow-sm">
                          <CheckCircle2 size={12} />
                        </span>
                      )}

                      <div className="grid grid-cols-[76px_minmax(0,1fr)] gap-3">
                        <div className="relative h-[88px] overflow-hidden rounded-xl border border-ink-100 bg-white p-2 shadow-inner">
                          <div
                            className={`absolute inset-x-0 top-0 h-2 ${
                              index % 2 === 0
                                ? "bg-gradient-to-r from-mint-500 to-mint-700"
                                : "bg-gradient-to-r from-iris-500 to-iris-700"
                            }`}
                          />
                          <div className="mt-3 h-2 w-3/4 rounded-full bg-ink-800" />
                          <div className="mt-1 h-1 w-1/2 rounded-full bg-ink-200" />
                          <div className="mt-3 space-y-1.5">
                            <div className="h-1 rounded-full bg-ink-100" />
                            <div className="h-1 w-5/6 rounded-full bg-ink-100" />
                            <div className="h-1 w-2/3 rounded-full bg-ink-100" />
                          </div>
                          <div className="absolute bottom-2 left-2 right-2 grid grid-cols-2 gap-1">
                            <div className="h-3 rounded bg-mint-50 ring-1 ring-mint-100" />
                            <div className="h-3 rounded bg-ink-50 ring-1 ring-ink-100" />
                          </div>
                        </div>

                        <div className="min-w-0 py-0.5">
                          <div className="flex items-start justify-between gap-2 pr-5">
                            <h3 className="line-clamp-1 text-xs font-bold text-ink-950">
                              {template.name}
                            </h3>
                          </div>

                          <span className="mt-1 inline-flex rounded-full bg-ink-50 px-2 py-0.5 text-[9px] font-bold text-ink-500 ring-1 ring-ink-100">
                            {template.page_size}
                          </span>

                          <p className="mt-1.5 line-clamp-3 text-[10px] leading-4 text-ink-500">
                            {template.description}
                          </p>

                          <p
                            className={`mt-1.5 text-[9px] font-bold uppercase tracking-[0.12em] ${
                              selected ? "text-mint-700" : "text-ink-400"
                            }`}
                          >
                            {selected ? "Selected layout" : "Select layout"}
                          </p>
                        </div>
                      </div>
                    </label>
                  );
                })}

                {visibleTemplates.length === 0 && (
                  <div className="rounded-2xl border border-dashed border-ink-200 bg-ink-50/70 px-4 py-6 text-center text-xs text-ink-500 sm:col-span-2 xl:col-span-1">
                    No compatible templates are available.
                  </div>
                )}
              </div>

              <div className="mx-3 mb-3 hidden items-center justify-between rounded-xl border border-ink-100 bg-ink-50/60 px-3 py-2 xl:flex">
                <div className="min-w-0">
                  <p className="text-[8px] font-extrabold uppercase tracking-[0.16em] text-ink-400">
                    Current selection
                  </p>
                  <p className="mt-0.5 truncate text-[11px] font-bold text-ink-800">
                    {selectedTemplate?.name ?? "Select a layout"}
                  </p>
                </div>
                <span className="rounded-full bg-white px-2 py-1 text-[9px] font-bold text-ink-500 ring-1 ring-ink-100">
                  Style only
                </span>
              </div>
            </section>

            <section className="shrink-0 overflow-hidden rounded-[22px] border border-white/90 bg-white shadow-[0_20px_60px_-48px_rgba(15,23,42,0.65)] ring-1 ring-ink-100/80">
              <div className="relative overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(45,212,191,0.28),transparent_42%),linear-gradient(135deg,#0f172a,#172033_58%,#202942)] px-4 py-3.5 text-white">
                <div className="absolute -right-8 -top-10 h-28 w-28 rounded-full bg-iris-400/15 blur-2xl" />
                <div className="relative flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-2.5">
                    <span
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ring-1 ring-white/15 ${
                        generationJob?.status === "FAILED"
                          ? "bg-red-500/20 text-red-100"
                          : generationJob?.status === "COMPLETED"
                            ? "bg-mint-400/20 text-mint-100"
                            : "bg-white/10 text-white"
                      }`}
                    >
                      {generationJob?.status === "FAILED" ? (
                        <XCircle size={16} />
                      ) : generationJob?.status === "COMPLETED" ? (
                        <CheckCircle2 size={16} />
                      ) : generationJob ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Sparkles size={16} />
                      )}
                    </span>

                    <div className="min-w-0">
                      <p className="text-[8px] font-extrabold uppercase tracking-[0.18em] text-white/45">
                        Generation status
                      </p>
                      <h2 className="mt-0.5 truncate text-xs font-bold">
                        {generationJob?.stage_label ?? "Ready to generate"}
                      </h2>
                      <p className="mt-0.5 line-clamp-2 text-[10px] leading-4 text-white/60">
                        {generationJob?.message ??
                          "Everything is ready. Review the brief and start generation."}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-bold ring-1 ring-white/10 ${
                      generationJob?.status === "FAILED"
                        ? "bg-red-500/15 text-red-200"
                        : "bg-white/10 text-mint-100"
                    }`}
                  >
                    {generationJob?.progress ?? 0}%
                  </span>
                </div>

                <div className="relative mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      generationJob?.status === "FAILED"
                        ? "bg-red-400"
                        : "bg-gradient-to-r from-mint-300 via-mint-400 to-iris-300"
                    }`}
                    style={{ width: `${generationJob?.progress ?? 0}%` }}
                  />
                </div>
              </div>

              {generatedDocument ? (
                <div className="p-3.5">
                  <div className="flex items-center gap-1.5 text-[9px] font-extrabold uppercase tracking-[0.15em] text-mint-700">
                    <CheckCircle2 size={13} />
                    Generation complete
                  </div>

                  <h3 className="mt-1.5 line-clamp-1 text-sm font-bold text-ink-950">
                    {generatedDocument.latest_version?.content.title_page ||
                      generatedDocument.title}
                  </h3>

                  {qualitySummary && (
                    <div className="mt-2.5 grid grid-cols-3 gap-1.5">
                      {[
                        [
                          "Requested",
                          qualitySummary.requested_question_count ?? 0,
                        ],
                        [
                          "Generated",
                          qualitySummary.generated_question_count ??
                            generatedQuestionCount,
                        ],
                        ["Repaired", qualitySummary.questions_repaired ?? 0],
                      ].map(([label, value]) => (
                        <div
                          key={label}
                          className="rounded-xl border border-ink-100 bg-ink-50/70 px-2 py-1.5 text-center"
                        >
                          <p className="text-[8px] font-bold uppercase tracking-wide text-ink-400">
                            {label}
                          </p>
                          <p className="mt-0.5 text-xs font-extrabold text-ink-900">
                            {value}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-2.5 grid grid-cols-2 gap-2">
                    <Button
                      type="button"
                      size="sm"
                      icon={<Eye size={14} />}
                      onClick={openGeneratedDocument}
                    >
                      Open studio
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      icon={<FileDown size={14} />}
                      onClick={openGeneratedPdf}
                    >
                      View PDF
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-1.5 p-3">
                  {generationStages.map((stage) => (
                    <div
                      key={stage.stage}
                      className={`flex min-w-0 items-center gap-1.5 rounded-lg border px-2 py-1.5 transition ${
                        stageState(stage) === "active"
                          ? "border-mint-200 bg-mint-50"
                          : "border-transparent bg-ink-50/80"
                      }`}
                    >
                      {stageIcon(stage)}
                      <span
                        className={`truncate text-[9px] ${
                          stageState(stage) === "pending"
                            ? "text-ink-400"
                            : "font-bold text-ink-800"
                        }`}
                      >
                        {stage.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <div className="sticky bottom-2 z-20 shrink-0 rounded-2xl border border-white/80 bg-white/90 p-1.5 shadow-[0_18px_44px_-26px_rgba(15,23,42,0.7)] backdrop-blur-xl xl:static xl:border-0 xl:bg-transparent xl:p-0 xl:shadow-none">
              <Button
                type="submit"
                className="w-full shadow-[0_14px_30px_-16px_rgba(13,148,136,0.85)]"
                size="lg"
                icon={
                  isSubmitting ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Sparkles size={16} />
                  )
                }
                disabled={isSubmitting || templates.length === 0}
              >
                {isSubmitting
                  ? "Generating document..."
                  : generatedDocument
                    ? "Generate another"
                    : "Generate question bank"}
              </Button>
              <p className="mt-1.5 text-center text-[9px] font-medium text-ink-400 xl:hidden">
                Review the details above before generating.
              </p>
            </div>
          </aside>
        </form>
      </div>
    </div>
  );
}
