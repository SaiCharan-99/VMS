import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  icon: Icon,
  title,
  action,
}: {
  icon: LucideIcon;
  title: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
      <div className="grid h-11 w-11 place-items-center rounded-card bg-surface-2 text-text-2">
        <Icon size={20} strokeWidth={1.8} aria-hidden />
      </div>
      <p className="m-0 text-text-2">{title}</p>
      {action}
    </div>
  );
}
