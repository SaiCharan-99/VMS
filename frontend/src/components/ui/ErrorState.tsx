import { AlertTriangle } from "lucide-react";
import { Button } from "./Button";

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div role="alert" className="flex flex-col items-center gap-3 px-4 py-12 text-center">
      <div className="grid h-11 w-11 place-items-center rounded-card bg-surface-2 text-text-2">
        <AlertTriangle size={20} strokeWidth={1.8} aria-hidden />
      </div>
      <p className="m-0 text-text-2">{message}</p>
      {onRetry && <Button onClick={onRetry}>Retry</Button>}
    </div>
  );
}
