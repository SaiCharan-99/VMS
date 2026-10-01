import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { Button, Card } from "@/components/ui";
import { safeNext } from "@/lib/nav";

export function LoginPage() {
  const { user, login } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const next = safeNext(params.get("next"));

  if (user) return <Navigate to={next} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(next, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="grid min-h-screen place-items-center px-4 py-10">
      <Card className="w-full max-w-[380px] px-6 py-7">
        <div className="mb-6 flex items-center gap-2.5 font-semibold">
          <div className="grid h-7 w-7 place-items-center rounded-[7px] bg-accent text-[13px] font-bold text-on-accent">
            V
          </div>
          VMS Inspect
        </div>
        <h1 className="m-0 mb-5 text-base font-semibold">Sign in</h1>
        <form onSubmit={submit} className="grid gap-3.5" noValidate>
          <div className="grid gap-1.5">
            <label htmlFor="email" className="text-[12.5px] font-medium text-text-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <label htmlFor="password" className="text-[12.5px] font-medium text-text-2">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && (
            <p role="alert" className="m-0 rounded-ctl bg-fail-soft px-3 py-2 text-sm text-fail">
              {error}
            </p>
          )}
          <Button type="submit" variant="primary" loading={busy} disabled={!email || !password}>
            Sign in
          </Button>
        </form>
      </Card>
    </main>
  );
}
