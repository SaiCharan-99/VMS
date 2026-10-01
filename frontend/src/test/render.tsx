import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { makeQueryClient } from "@/api/queryClient";
import { AuthProvider } from "@/auth/AuthProvider";
import { setToken } from "@/auth/tokenStore";
import { ROUTER_FUTURE } from "@/lib/routerFlags";
import { ToastProvider } from "@/components/ui";

/** Renders `element` at `path` inside the app providers, logged in via a mocked /auth/me. */
export function renderPage(
  element: ReactNode,
  { path = "/", url = path }: { path?: string; url?: string } = {},
) {
  setToken("test-token");
  const qc = makeQueryClient();
  qc.setDefaultOptions({ queries: { ...qc.getDefaultOptions().queries, retry: false } });
  const router = createMemoryRouter(
    [
      { path, element: <AuthProvider>{element}</AuthProvider> },
      { path: "/login", element: <p>login page</p> },
    ],
    { initialEntries: [url], future: ROUTER_FUTURE },
  );
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <RouterProvider router={router} future={{ v7_startTransition: true }} />
      </ToastProvider>
    </QueryClientProvider>,
  );
}
