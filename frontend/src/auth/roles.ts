import type { Role, User } from "@/types/api";

export const ALL_ROLES: readonly Role[] = ["operator", "reviewer", "admin"];
export const REVIEWER_UP: readonly Role[] = ["reviewer", "admin"];
export const ADMIN_ONLY: readonly Role[] = ["admin"];

export function hasRole(user: User | null, roles: readonly Role[]): boolean {
  return user !== null && roles.includes(user.role);
}
