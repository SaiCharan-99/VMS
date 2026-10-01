import type { ReactNode } from "react";

/** Row of filter controls; pages keep the state in URL query params. */
export function FilterBar({ children, end }: { children: ReactNode; end?: ReactNode }) {
  return (
    <div role="search" aria-label="Filters" className="mb-3.5 flex flex-wrap items-center gap-2">
      {children}
      {end && <div className="ml-auto flex items-center gap-2">{end}</div>}
    </div>
  );
}
