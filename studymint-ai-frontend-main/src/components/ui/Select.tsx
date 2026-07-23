import type { SelectHTMLAttributes } from "react";

interface Option {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: Option[];
}

export function Select({ label, options, className = "", ...props }: SelectProps) {
  return (
    <label className="block">
      {label && <span className="mb-1.5 block text-sm font-semibold text-ink-900">{label}</span>}
      <select
        className={`h-11 w-full rounded-md border border-ink-300 bg-white px-3 text-sm text-ink-950 shadow-sm outline-none transition focus:border-mint-600 focus:ring-4 focus:ring-mint-100 disabled:cursor-not-allowed disabled:bg-ink-100 disabled:text-ink-500 ${className}`}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
