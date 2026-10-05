import { QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, type ReactNode } from "react";
import {
  createBrowserRouter,
  Link,
  Outlet,
  RouterProvider,
  type RouteObject,
} from "react-router-dom";
import { makeQueryClient } from "@/api/queryClient";
import { ROUTER_FUTURE } from "@/lib/routerFlags";
import { AuthProvider } from "@/auth/AuthProvider";
import { RequireRole } from "@/auth/RequireRole";
import { AppShell } from "@/components/AppShell";
import { Skeleton, ToastProvider } from "@/components/ui";
import { ADMIN_ONLY, REVIEWER_UP } from "@/auth/roles";
import { LoginPage } from "@/pages/LoginPage";
import { UploadPage } from "@/pages/UploadPage";
import { VideoDetailPage } from "@/pages/VideoDetailPage";
import { VideosPage } from "@/pages/VideosPage";

// Chart-heavy and role-restricted pages load on demand, keeping Recharts out of the main bundle.
const DashboardPage = lazy(() =>
  import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const ReviewPage = lazy(() =>
  import("@/pages/ReviewPage").then((m) => ({ default: m.ReviewPage })),
);
const ReportsPage = lazy(() =>
  import("@/pages/ReportsPage").then((m) => ({ default: m.ReportsPage })),
);
const AdminPage = lazy(() => import("@/pages/AdminPage").then((m) => ({ default: m.AdminPage })));
// Behind the DEV check so production builds don't emit the gallery chunk at all.
const UiGallery = import.meta.env.DEV
  ? lazy(() => import("@/pages/UiGallery").then((m) => ({ default: m.UiGallery })))
  : () => null;

function Loading({ children }: { children: ReactNode }) {
  return <Suspense fallback={<Skeleton className="h-64 w-full" />}>{children}</Suspense>;
}

function Root() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  );
}

function NotFound() {
  return (
    <div className="py-12 text-center text-text-2">
      Page not found.{" "}
      <Link to="/" className="font-medium text-accent-text hover:underline">
        Go to the dashboard
      </Link>
    </div>
  );
}

const routes: RouteObject[] = [
  {
    element: <Root />,
    children: [
      { path: "/login", element: <LoginPage /> },
      {
        element: (
          <RequireRole>
            <AppShell />
          </RequireRole>
        ),
        children: [
          {
            path: "/",
            element: (
              <Loading>
                <DashboardPage />
              </Loading>
            ),
            handle: { title: "Dashboard" },
          },
          { path: "/upload", element: <UploadPage />, handle: { title: "Upload" } },
          { path: "/videos", element: <VideosPage />, handle: { title: "Inspections" } },
          { path: "/videos/:id", element: <VideoDetailPage />, handle: { title: "Inspection" } },
          {
            path: "/review",
            element: (
              <RequireRole roles={REVIEWER_UP}>
                <Loading>
                  <ReviewPage />
                </Loading>
              </RequireRole>
            ),
            handle: { title: "Review queue" },
          },
          {
            path: "/reports",
            element: (
              <RequireRole roles={REVIEWER_UP}>
                <Loading>
                  <ReportsPage />
                </Loading>
              </RequireRole>
            ),
            handle: { title: "Reports" },
          },
          {
            path: "/admin",
            element: (
              <RequireRole roles={ADMIN_ONLY}>
                <Loading>
                  <AdminPage />
                </Loading>
              </RequireRole>
            ),
            handle: { title: "Admin" },
          },
          ...(import.meta.env.DEV
            ? [
                {
                  path: "/_ui",
                  element: (
                    <Loading>
                      <UiGallery />
                    </Loading>
                  ),
                  handle: { title: "UI components" },
                },
              ]
            : []),
          { path: "*", element: <NotFound />, handle: { title: "Not found" } },
        ],
      },
    ],
  },
];

const router = createBrowserRouter(routes, { future: ROUTER_FUTURE });
const queryClient = makeQueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <RouterProvider router={router} future={{ v7_startTransition: true }} />
      </ToastProvider>
    </QueryClientProvider>
  );
}
