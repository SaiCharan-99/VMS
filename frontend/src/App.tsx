import { QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
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
import { ToastProvider } from "@/components/ui";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { UploadPage } from "@/pages/UploadPage";
import { VideoDetailPage } from "@/pages/VideoDetailPage";
import { VideosPage } from "@/pages/VideosPage";

const UiGallery = lazy(() => import("@/pages/UiGallery").then((m) => ({ default: m.UiGallery })));

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
          { path: "/", element: <DashboardPage />, handle: { title: "Dashboard" } },
          { path: "/upload", element: <UploadPage />, handle: { title: "Upload" } },
          { path: "/videos", element: <VideosPage />, handle: { title: "Inspections" } },
          { path: "/videos/:id", element: <VideoDetailPage />, handle: { title: "Inspection" } },
          ...(import.meta.env.DEV
            ? [
                {
                  path: "/_ui",
                  element: (
                    <Suspense fallback={null}>
                      <UiGallery />
                    </Suspense>
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
