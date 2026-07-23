import type { ReactNode } from "react";

export function StatCard({ label, value, icon, tone = "mint" }: { label: string; value: string | number; icon: ReactNode; tone?: "mint" | "iris" | "saffron" | "ink" }) {
  const tones = {
    mint: { icon: "bg-mint-50 text-mint-800 ring-1 ring-mint-200", line: "bg-mint-700" },
    iris: { icon: "bg-iris-50 text-iris-700 ring-1 ring-iris-200", line: "bg-iris-600" },
    saffron: { icon: "bg-saffron-50 text-saffron-800 ring-1 ring-saffron-200", line: "bg-saffron-600" },
    ink: { icon: "bg-ink-100 text-ink-800 ring-1 ring-ink-200", line: "bg-ink-800" }
  };
  const activeTone = tones[tone];

  return (
    <div className="overflow-hidden rounded-lg border border-ink-200 bg-white shadow-sm">
      <div className={`h-1 ${activeTone.line}`} />
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 p-3 sm:p-4">
          <p className="truncate text-xs font-semibold text-ink-600 sm:text-sm">{label}</p>
          <p className="mt-1.5 text-xl font-semibold text-ink-950 sm:mt-2 sm:text-2xl">{value}</p>
        </div>
        <div className={`mr-3 flex h-9 w-9 shrink-0 items-center justify-center rounded-md sm:mr-4 sm:h-10 sm:w-10 ${activeTone.icon}`}>{icon}</div>
      </div>
    </div>
  );
}
