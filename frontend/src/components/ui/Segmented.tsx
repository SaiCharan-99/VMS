import { cn } from "@/lib/cn";

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

/** Single-choice segmented control (a radio group). */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
  stretch,
}: {
  label: string;
  options: SegmentedOption<T>[];
  value: T;
  onChange: (v: T) => void;
  stretch?: boolean;
}) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn(
        "inline-flex overflow-hidden rounded-ctl border border-border bg-surface",
        stretch && "flex w-full",
      )}
    >
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(o.value)}
            className={cn(
              "border-r border-border px-3 py-1.5 last:border-r-0 focus-visible:-outline-offset-2",
              stretch && "flex-1",
              on ? "bg-surface-2 font-medium text-text" : "text-text-2 hover:text-text",
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
