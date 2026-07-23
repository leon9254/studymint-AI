import type { DocumentStatus } from "../../types";

const statusClasses: Record<DocumentStatus, { badge: string; dot: string }> = {
  DRAFT: { badge: "bg-ink-100 text-ink-800 ring-1 ring-ink-200", dot: "bg-ink-500" },
  GENERATING: { badge: "bg-iris-50 text-iris-700 ring-1 ring-iris-200", dot: "bg-iris-500" },
  READY_FOR_REVIEW: { badge: "bg-saffron-50 text-saffron-800 ring-1 ring-saffron-200", dot: "bg-saffron-500" },
  PDF_READY: { badge: "bg-mint-50 text-mint-800 ring-1 ring-mint-200", dot: "bg-mint-500" },
  MARKETPLACE_READY: { badge: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200", dot: "bg-emerald-500" },
  ARCHIVED: { badge: "bg-stone-100 text-stone-800 ring-1 ring-stone-200", dot: "bg-stone-500" }
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const style = statusClasses[status];

  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${style.badge}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {status.replace(/_/g, " ")}
    </span>
  );
}
