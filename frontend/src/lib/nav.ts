// Post-login redirect target from `?next=`. Only same-origin paths are allowed: browsers read
// `//host` and `/\host` as other origins, so anything that doesn't resolve to our own origin
// (or contains a backslash or control character) falls back to the dashboard.
export function safeNext(next: string | null): string {
  if (!next || !next.startsWith("/") || next.includes("\\")) return "/";
  if ([...next].some((ch) => ch.charCodeAt(0) < 32)) return "/";
  const base = "http://same.origin";
  try {
    const url = new URL(next, base);
    return url.origin === base ? url.pathname + url.search + url.hash : "/";
  } catch {
    return "/";
  }
}
