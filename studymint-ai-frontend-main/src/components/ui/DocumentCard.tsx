import { FileText } from "lucide-react";
import { Link } from "react-router-dom";
import type { StudyDocument } from "../../types";
import { StatusBadge } from "./StatusBadge";

export function DocumentCard({ document }: { document: StudyDocument }) {
  return (
    <Link
      to={`/documents/${document.id}/studio`}
      className="block rounded-lg border border-ink-200 bg-white p-3 shadow-sm transition hover:border-mint-400 hover:shadow-soft focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-mint-100 sm:p-4"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-mint-50 text-mint-800 ring-1 ring-mint-200">
          <FileText size={19} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="min-w-0 truncate text-sm font-semibold text-ink-950">
              {document.title}
            </h3>
            <StatusBadge status={document.status} />
          </div>
          <p className="mt-1 truncate text-sm font-medium text-ink-600">
            {document.subject}
          </p>
          <p className="mt-3 text-xs font-semibold text-ink-500">
            {document.document_type} - {document.target_platform}
          </p>
          {document.generation_time_seconds != null && (
            <p className="mt-1 text-xs font-medium text-mint-700">
              Ready in {Math.floor(document.generation_time_seconds / 60)}:
              {String(document.generation_time_seconds % 60).padStart(2, "0")}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}
