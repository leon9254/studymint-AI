import type { ReactNode } from "react";

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 border-b border-ink-200 pb-4 sm:flex-row sm:items-start sm:justify-between sm:gap-4 sm:pb-5">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-normal text-ink-950 sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-700">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
