import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
}

export function Input({ label, helperText, className = "", ...props }: InputProps) {
  return (
    <label className="block">
      {label && <span className="mb-1.5 block text-sm font-semibold text-ink-900">{label}</span>}
      <input
        className={`h-11 w-full rounded-md border border-ink-300 bg-white px-3 text-sm text-ink-950 shadow-sm outline-none transition placeholder:text-ink-500 focus:border-mint-600 focus:ring-4 focus:ring-mint-100 disabled:cursor-not-allowed disabled:bg-ink-100 disabled:text-ink-500 ${className}`}
        {...props}
      />
      {helperText && <span className="mt-1.5 block text-xs font-medium text-ink-600">{helperText}</span>}
    </label>
  );
}
