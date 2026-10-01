import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "pass" | "fail" | "ghost";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent border-accent text-on-accent hover:brightness-110",
  secondary: "bg-surface border-border-strong text-text hover:bg-surface-2",
  pass: "bg-pass border-pass text-on-status hover:brightness-110",
  fail: "bg-fail border-fail text-on-status hover:brightness-110",
  ghost: "bg-transparent border-transparent text-text-2 hover:bg-surface-2 hover:text-text",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md";
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "secondary",
    size = "md",
    loading = false,
    className,
    children,
    disabled,
    type,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-ctl border font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
        size === "sm" ? "px-2.5 py-1 text-sm" : "px-3.5 py-[7px]",
        VARIANTS[variant],
        className,
      )}
      {...rest}
    >
      {loading && <span className="spin" aria-hidden />}
      {children}
    </button>
  );
});

export function IconButton({
  label,
  className,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "grid h-[34px] w-[34px] flex-none place-items-center rounded-ctl border border-border bg-surface text-text-2 hover:bg-surface-2 hover:text-text",
        className,
      )}
      {...rest}
    />
  );
}
