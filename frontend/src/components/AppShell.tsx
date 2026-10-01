import { LayoutDashboard, LogOut, Moon, Plus, Search, Sun, Upload, Video } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useState, type FormEvent } from "react";
import { NavLink, Outlet, useMatches, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { ALL_ROLES, hasRole } from "@/auth/roles";
import { Button, IconButton } from "@/components/ui";
import { cn } from "@/lib/cn";
import { useTheme } from "@/lib/theme";
import type { Role } from "@/types/api";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  roles: readonly Role[];
}

// Review queue, Reports and Admin join this list in Phase 5 (reviewer+/admin only).
const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ALL_ROLES },
  { to: "/upload", label: "Upload", icon: Upload, roles: ALL_ROLES },
  { to: "/videos", label: "Inspections", icon: Video, roles: ALL_ROLES },
];

const ROLE_LABEL: Record<Role, string> = {
  operator: "Operator",
  reviewer: "Reviewer",
  admin: "Admin",
};

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

function usePageTitle(): string {
  const matches = useMatches();
  for (let i = matches.length - 1; i >= 0; i--) {
    const handle = matches[i]?.handle as { title?: string } | undefined;
    if (handle?.title) return handle.title;
  }
  return "VMS Inspect";
}

function GlobalSearch() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const term = q.trim();
    navigate(term ? `/videos?q=${encodeURIComponent(term)}` : "/videos");
  };
  return (
    <form
      role="search"
      onSubmit={submit}
      className="hidden w-[280px] items-center gap-2 rounded-ctl border border-border bg-surface-2 px-2.5 py-1.5 text-text-3 focus-within:outline focus-within:outline-2 focus-within:outline-accent lg:flex"
    >
      <Search size={15} strokeWidth={2} aria-hidden />
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label="Search AWB, barcode or file"
        placeholder="Search AWB, barcode, file…"
        className="w-full border-0 bg-transparent text-text outline-none placeholder:text-text-3"
      />
    </form>
  );
}

export function AppShell() {
  const { user, logout } = useAuth();
  const [theme, toggleTheme] = useTheme();
  const title = usePageTitle();
  const navigate = useNavigate();
  const items = NAV.filter((n) => hasRole(user, n.roles));

  return (
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-[232px_minmax(0,1fr)]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-ctl focus:bg-surface focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <aside className="flex items-center gap-0.5 overflow-x-auto md:items-stretch border-b border-border bg-surface p-2 md:sticky md:top-0 md:h-screen md:flex-col md:overflow-visible md:border-b-0 md:border-r md:px-3 md:py-[18px]">
        <div className="hidden items-center gap-2.5 px-2.5 pb-[18px] pt-1 font-semibold md:flex">
          <div className="grid h-7 w-7 place-items-center rounded-[7px] bg-accent text-[13px] font-bold text-on-accent">
            V
          </div>
          VMS Inspect
        </div>
        <nav aria-label="Main" className="contents">
          {items.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex flex-none items-center gap-2.5 whitespace-nowrap rounded-ctl px-2.5 py-2",
                  isActive
                    ? "bg-accent-soft font-medium text-accent-text"
                    : "text-text-2 hover:bg-surface-2 hover:text-text",
                )
              }
            >
              <n.icon size={17} strokeWidth={1.8} aria-hidden />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden flex-1 md:block" />
        {user && (
          <div className="ml-auto flex flex-none items-center gap-2.5 md:ml-0 md:mt-2 md:border-t md:border-border md:p-2.5">
            <div
              aria-hidden
              className="hidden h-[30px] w-[30px] flex-none place-items-center rounded-full bg-surface-2 text-xs font-semibold text-text-2 md:grid"
            >
              {initials(user.name)}
            </div>
            <div className="hidden min-w-0 flex-1 md:block">
              <div className="truncate text-[13px] font-medium">{user.name}</div>
              <div className="text-xs text-text-3">{ROLE_LABEL[user.role]}</div>
            </div>
            <IconButton label="Sign out" onClick={logout} className="h-8 w-8 border-0">
              <LogOut size={16} strokeWidth={1.8} aria-hidden />
            </IconButton>
          </div>
        )}
      </aside>

      <div className="min-w-0">
        <header className="flex h-[60px] items-center gap-3 border-b border-border bg-surface px-4 md:px-7">
          <h1 className="m-0 min-w-0 flex-1 truncate text-base font-semibold">{title}</h1>
          <GlobalSearch />
          <IconButton
            label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            onClick={toggleTheme}
          >
            {theme === "dark" ? (
              <Sun size={16} strokeWidth={2} aria-hidden />
            ) : (
              <Moon size={16} strokeWidth={2} aria-hidden />
            )}
          </IconButton>
          <Button variant="primary" onClick={() => navigate("/upload")}>
            <Plus size={16} strokeWidth={2} aria-hidden />
            <span className="hidden sm:inline">Upload videos</span>
            <span className="sm:hidden">Upload</span>
          </Button>
        </header>
        <main id="main" tabIndex={-1} className="max-w-[1280px] px-4 pb-12 pt-4 md:px-7 md:pt-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
