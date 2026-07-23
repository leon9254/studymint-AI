import type { TextareaHTMLAttributes } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export function Textarea({ label, className = "", ...props }: TextareaProps) {
  return (
    <label className="block">
      {label && <span className="mb-1.5 block text-sm font-semibold text-ink-900">{label}</span>}
      <textarea
        className={`min-h-28 w-full resize-y rounded-md border border-ink-300 bg-white px-3 py-2 text-sm leading-6 text-ink-950 shadow-sm outline-none transition placeholder:text-ink-500 focus:border-mint-600 focus:ring-4 focus:ring-mint-100 disabled:cursor-not-allowed disabled:bg-ink-100 disabled:text-ink-500 ${className}`}
        {...props}
      />
    </label>
  );
}
