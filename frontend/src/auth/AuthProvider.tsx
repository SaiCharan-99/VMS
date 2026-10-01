import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { setUnauthorizedHandler } from "@/api/client";
import { api } from "@/api/endpoints";
import type { User } from "@/types/api";
import { getToken, setToken } from "./tokenStore";

interface AuthState {
  user: User | null;
  /** True while a stored token is being checked against /auth/me. */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const me = useQuery({
    queryKey: ["me"],
    queryFn: api.me,
    enabled: getToken() !== null,
    staleTime: Infinity,
    retry: false,
  });

  const logout = useCallback(() => {
    setToken(null);
    qc.clear();
    navigate("/login", { replace: true });
  }, [qc, navigate]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      qc.clear();
      const here = window.location.pathname + window.location.search;
      navigate(`/login?next=${encodeURIComponent(here)}`, { replace: true });
    });
  }, [qc, navigate]);

  const login = useCallback(
    async (email: string, password: string) => {
      const token = await api.login(email, password);
      setToken(token.access_token);
      qc.setQueryData(["me"], token.user);
    },
    [qc],
  );

  const value = useMemo<AuthState>(
    () => ({
      user: getToken() ? (me.data ?? null) : null,
      loading: getToken() !== null && me.isPending,
      login,
      logout,
    }),
    [me.data, me.isPending, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
