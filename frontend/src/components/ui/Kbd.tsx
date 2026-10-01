import type { ReactNode } from "react";

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-border-strong bg-surface-2 px-[5px] py-px font-mono text-[11px] font-medium text-text-2">
      {children}
    </kbd>
  );
}
