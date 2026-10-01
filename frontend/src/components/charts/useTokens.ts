import { useEffect, useState } from "react";

const NAMES = [
  "pass",
  "review",
  "fail",
  "accent",
  "surface",
  "border",
  "text-2",
  "text-3",
] as const;
export type Tokens = Record<(typeof NAMES)[number], string>;

function read(): Tokens {
  const css = getComputedStyle(document.documentElement);
  return Object.fromEntries(
    NAMES.map((n) => [n, css.getPropertyValue(`--${n}`).trim() || "currentColor"]),
  ) as Tokens;
}

/** Resolved design tokens for SVG charts (Recharts sets colours as attributes, where
 *  `var(--x)` isn't reliable). Re-reads on theme toggle and OS theme change. */
export function useTokens(): Tokens {
  const [tokens, setTokens] = useState(read);
  useEffect(() => {
    const update = () => setTokens(read());
    const obs = new MutationObserver(update);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    mq?.addEventListener("change", update);
    return () => {
      obs.disconnect();
      mq?.removeEventListener("change", update);
    };
  }, []);
  return tokens;
}
