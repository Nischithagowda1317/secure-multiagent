import type { ChatResponse, DemoAccount, UserProfile } from "./types";

const API = "/api";

function token(): string | null {
  return localStorage.getItem("enterprise_token");
}

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = body.detail ?? JSON.stringify(body);
    } catch {
      // Keep status text.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  return parse<{ access_token: string; user: UserProfile }>(
    await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    })
  );
}

export async function demoAccounts() {
  return parse<DemoAccount[]>(await fetch(`${API}/auth/demo-accounts`));
}

export async function me() {
  return get<UserProfile>("/auth/me");
}

export async function get<T>(path: string): Promise<T> {
  return parse<T>(
    await fetch(`${API}${path}`, {
      headers: { Authorization: `Bearer ${token()}` }
    })
  );
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  return parse<T>(
    await fetch(`${API}${path}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token()}`,
        "Content-Type": "application/json"
      },
      body: body === undefined ? undefined : JSON.stringify(body)
    })
  );
}

export async function sendChat(message: string, files: File[]): Promise<ChatResponse> {
  const form = new FormData();
  form.append("message", message);
  files.forEach((file) => form.append("files", file));
  return parse<ChatResponse>(
    await fetch(`${API}/chat`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token()}` },
      body: form
    })
  );
}

export async function uploadDocument(form: FormData) {
  return parse<Record<string, unknown>>(
    await fetch(`${API}/documents/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token()}` },
      body: form
    })
  );
}
