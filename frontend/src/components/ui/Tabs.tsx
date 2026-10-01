import { useRef, type KeyboardEvent } from "react";
import { cn } from "@/lib/cn";

export interface TabItem<T extends string> {
  value: T;
  label: string;
}

/** WAI-ARIA tab list (arrow keys move between tabs). Panels use `tabPanelProps`. */
export function Tabs<T extends string>({
  label,
  tabs,
  value,
  onChange,
  idPrefix,
}: {
  label: string;
  tabs: TabItem<T>[];
  value: T;
  onChange: (v: T) => void;
  idPrefix: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent, i: number) => {
    const delta = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!delta) return;
    e.preventDefault();
    const next = (i + delta + tabs.length) % tabs.length;
    refs.current[next]?.focus();
    const tab = tabs[next];
    if (tab) onChange(tab.value);
  };
  return (
    <div
      role="tablist"
      aria-label={label}
      className="mb-4 flex gap-1 overflow-x-auto border-b border-border"
    >
      {tabs.map((t, i) => {
        const on = t.value === value;
        return (
          <button
            key={t.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`${idPrefix}-tab-${t.value}`}
            aria-selected={on}
            aria-controls={`${idPrefix}-panel-${t.value}`}
            tabIndex={on ? 0 : -1}
            onClick={() => onChange(t.value)}
            onKeyDown={(e) => onKey(e, i)}
            className={cn(
              "-mb-px whitespace-nowrap border-b-2 px-3 py-2 focus-visible:-outline-offset-2",
              on
                ? "border-accent font-medium text-accent-text"
                : "border-transparent text-text-2 hover:text-text",
            )}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

/** Label + control stacked, as on the upload and login forms. */
export function Field({
  id,
  label,
  hint,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={id} className="text-[12.5px] font-medium text-text-2">
        {label}
      </label>
      {children}
      {hint && <span className="text-xs text-text-3">{hint}</span>}
    </div>
  );
}
