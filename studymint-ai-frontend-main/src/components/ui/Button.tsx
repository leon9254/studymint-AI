import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "border-mint-700 bg-mint-700 text-white shadow-sm shadow-mint-900/10 hover:border-mint-800 hover:bg-mint-800 active:bg-mint-900",
  secondary: "border-ink-300 bg-white text-ink-800 shadow-sm hover:border-ink-400 hover:bg-ink-50 active:bg-ink-100",
  ghost: "border-transparent bg-transparent text-ink-700 hover:bg-ink-100 hover:text-ink-950 active:bg-ink-200",
  danger: "border-red-300 bg-red-50 text-red-800 shadow-sm hover:border-red-400 hover:bg-red-100 active:bg-red-200"
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-11 px-5 text-base"
};

export function Button({ children, icon, variant = "primary", size = "md", className = "", ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex min-w-0 items-center justify-center gap-2 whitespace-nowrap rounded-md border font-semibold transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-mint-200 focus-visible:ring-offset-1 focus-visible:ring-offset-white disabled:cursor-not-allowed disabled:opacity-55 ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
