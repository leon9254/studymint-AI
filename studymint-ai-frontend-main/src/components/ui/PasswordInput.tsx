import { Eye, EyeOff } from "lucide-react";
import { useId, useState } from "react";
import type { InputHTMLAttributes } from "react";

interface PasswordInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
  helperText?: string;
}

export function PasswordInput({ label, helperText, className = "", id, ...props }: PasswordInputProps) {
  const [visible, setVisible] = useState(false);
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const Icon = visible ? EyeOff : Eye;

  return (
    <div>
      {label && (
        <label className="mb-1.5 block text-sm font-semibold text-ink-900" htmlFor={inputId}>
          {label}
        </label>
      )}
      <div className="relative">
        <input
          id={inputId}
          className={`h-11 w-full rounded-md border border-ink-300 bg-white px-3 pr-11 text-sm text-ink-950 shadow-sm outline-none transition placeholder:text-ink-500 focus:border-mint-600 focus:ring-4 focus:ring-mint-100 disabled:cursor-not-allowed disabled:bg-ink-100 disabled:text-ink-500 ${className}`}
          type={visible ? "text" : "password"}
          {...props}
        />
        <button
          type="button"
          className="absolute right-2 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-ink-500 transition hover:bg-ink-100 hover:text-ink-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-mint-100"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? "Hide password" : "Show password"}
          title={visible ? "Hide password" : "Show password"}
        >
          <Icon size={18} />
        </button>
      </div>
      {helperText && <span className="mt-1.5 block text-xs font-medium text-ink-600">{helperText}</span>}
    </div>
  );
}
