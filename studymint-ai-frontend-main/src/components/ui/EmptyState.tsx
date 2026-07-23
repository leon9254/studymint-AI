import type { ReactNode } from "react";

export function EmptyState({ icon, title, description, action }: { icon: ReactNode; title: string; description: string; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-ink-300 bg-white px-6 py-12 text-center shadow-sm">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-md bg-ink-100 text-ink-800 ring-1 ring-ink-200">{icon}</div>
      <h3 className="mt-4 text-base font-semibold text-ink-950">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-600">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
