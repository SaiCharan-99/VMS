import { useEffect, useRef, type ReactNode } from "react";

/** Modal dialog on the native <dialog> element: focus is trapped and Esc closes it. */
export function Dialog({
  open,
  title,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal?.();
    if (!open && el.open) el.close?.();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-label={title}
      className="w-[min(440px,calc(100vw-32px))] rounded-card border border-border bg-surface p-0 text-text shadow-xl backdrop:bg-black/40"
    >
      {open && (
        <div>
          <h2 className="m-0 border-b border-border px-[18px] py-3.5 text-base font-semibold">
            {title}
          </h2>
          <div className="px-[18px] py-4">{children}</div>
          {footer && (
            <div className="flex justify-end gap-2 border-t border-border px-[18px] py-3">
              {footer}
            </div>
          )}
        </div>
      )}
    </dialog>
  );
}
