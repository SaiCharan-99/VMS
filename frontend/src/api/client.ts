import type { z } from "zod";
import { getToken, setToken } from "@/auth/tokenStore";

export const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let onUnauthorized: () => void = () => {};

/** Called once by AuthProvider: what to do when the API rejects the token. */
export function setUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn;
}

/** Absolute URL for an API path (media URLs come back from the API as paths). */
export function apiUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_URL}${path}`;
}

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((e) => (e as { msg?: string }).msg ?? "").join("; ");
  }
  return fallback;
}

function handleStatus(status: number, body: unknown, hadToken: boolean): never {
  if (status === 401 && hadToken) {
    setToken(null);
    onUnauthorized();
  }
  const fallback =
    status === 429
      ? "Too many attempts. Try again in a few minutes."
      : `Request failed (${status}).`;
  throw new ApiError(status, status === 429 ? fallback : detailOf(body, fallback));
}

export async function request<T>(
  path: string,
  schema: z.ZodType<T, z.ZodTypeDef, unknown> | null,
  init: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && typeof init.body === "string") headers.set("Content-Type", "application/json");
  let resp: Response;
  try {
    resp = await fetch(apiUrl(path), { ...init, headers });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection.");
  }
  const text = await resp.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!resp.ok) handleStatus(resp.status, body, Boolean(token));
  if (!schema) return body as T;
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    console.error("Unexpected API response", path, parsed.error.issues);
    throw new ApiError(resp.status, "The server sent an unexpected response.");
  }
  return parsed.data;
}

export interface UploadHandle<T> {
  promise: Promise<T>;
  abort: () => void;
}

/** Multipart upload via XHR, which (unlike fetch) reports upload progress. */
export function uploadWithProgress<T>(
  path: string,
  form: FormData,
  schema: z.ZodType<T, z.ZodTypeDef, unknown>,
  onProgress: (fraction: number) => void,
): UploadHandle<T> {
  const xhr = new XMLHttpRequest();
  const promise = new Promise<T>((resolve, reject) => {
    const token = getToken();
    xhr.open("POST", apiUrl(path));
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onerror = () => reject(new ApiError(0, "Upload failed. Check your connection."));
    xhr.onabort = () => reject(new ApiError(0, "Upload cancelled."));
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        body = xhr.responseText;
      }
      try {
        if (xhr.status < 200 || xhr.status >= 300) handleStatus(xhr.status, body, Boolean(token));
        const parsed = schema.safeParse(body);
        if (!parsed.success)
          throw new ApiError(xhr.status, "The server sent an unexpected response.");
        resolve(parsed.data);
      } catch (err) {
        reject(err);
      }
    };
    xhr.send(form);
  });
  return { promise, abort: () => xhr.abort() };
}
