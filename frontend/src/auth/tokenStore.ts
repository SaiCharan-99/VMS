// The token lives in memory, mirrored to localStorage so a reload keeps the session.
const KEY = "vms.token";
let token: string | null = read();

function read(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return token;
}

export function setToken(value: string | null): void {
  token = value;
  try {
    if (value) localStorage.setItem(KEY, value);
    else localStorage.removeItem(KEY);
  } catch {
    // Storage blocked (private mode): the session lasts until reload.
  }
}
