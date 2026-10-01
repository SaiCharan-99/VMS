import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Skeleton } from "@/components/ui";
import type { Role } from "@/types/api";
import { useAuth } from "./AuthProvider";
import { ALL_ROLES, hasRole } from "./roles";

/** Route guard. The API enforces roles too; this only keeps the UI honest. */
export function RequireRole({
  roles = ALL_ROLES,
  children,
}: {
  roles?: readonly Role[];
  children: ReactNode;
}) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="p-7" aria-busy="true">
        <Skeleton className="h-8 w-48" />
      </div>
    );
  }
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (!hasRole(user, roles)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
