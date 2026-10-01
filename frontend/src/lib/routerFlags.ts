/** Opt into React Router v7 behaviour now (silences the v6 future-flag warnings). */
export const ROUTER_FUTURE = {
  v7_fetcherPersist: true,
  v7_normalizeFormMethod: true,
  v7_partialHydration: true,
  v7_relativeSplatPath: true,
  v7_skipActionErrorRevalidation: true,
} as const;
