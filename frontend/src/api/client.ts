// Cliente HTTP mínimo para la API financiera. Traduce fetch a un resultado
// que la UI pinta sin saber de códigos HTTP, con los mismos mensajes en
// español que usa auth/api.ts.
import { API_BASE } from "./config";

export type ApiErrorKind = "network" | "unauthorized" | "forbidden" | "not_found" | "validation" | "conflict" | "rate_limited" | "server" | "unexpected";

export interface ApiError {
  ok: false;
  kind: ApiErrorKind;
  status?: number;
  /** Listo para mostrarse en un role="alert". */
  message: string;
}

export type ApiResult<T> = { ok: true; data: T } | ApiError;

export const NETWORK_MESSAGE = "No se pudo conectar con el servidor. Revisa tu conexión y vuelve a intentar.";

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string | null;
  signal?: AbortSignal;
}

async function readJson(res: Response): Promise<any> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

function describe(res: Response, body: any): ApiError {
  const detail = body?.detail;
  const text = typeof detail === "string" ? detail : Array.isArray(detail) ? "Algunos datos no tienen el formato esperado." : detail?.message;
  switch (res.status) {
    case 401:
      return { ok: false, kind: "unauthorized", status: 401, message: "Tu sesión expiró. Vuelve a iniciar sesión." };
    case 403:
      return { ok: false, kind: "forbidden", status: 403, message: "No tienes acceso a este negocio." };
    case 404:
      return { ok: false, kind: "not_found", status: 404, message: text || "No encontramos lo que buscabas." };
    case 409:
      return { ok: false, kind: "conflict", status: 409, message: text || "Esta operación ya se hizo o choca con otra." };
    case 429: {
      // Límite de peticiones de las rutas públicas (backend/app/ratelimit.py).
      const wait = Number(res.headers.get("Retry-After"));
      const when = Number.isFinite(wait) && wait > 0 ? ` Intenta de nuevo en ${wait} s.` : " Espera un momento e intenta de nuevo.";
      return { ok: false, kind: "rate_limited", status: 429, message: `Demasiados intentos seguidos.${when}` };
    }
    case 400:
    case 422:
      return { ok: false, kind: "validation", status: res.status, message: text || "Revisa los datos e inténtalo de nuevo." };
    default:
      if (res.status >= 500) return { ok: false, kind: "server", status: res.status, message: "El servidor tuvo un problema. Inténtalo de nuevo en un momento." };
      return { ok: false, kind: "unexpected", status: res.status, message: text || `El servidor respondió ${res.status}.` };
  }
}

export async function apiFetch<T>(path: string, { method = "GET", body, token, signal }: RequestOptions = {}): Promise<ApiResult<T>> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if ((err as { name?: string })?.name === "AbortError") return { ok: false, kind: "unexpected", message: "Cancelado." };
    return { ok: false, kind: "network", message: NETWORK_MESSAGE };
  }
  const json = await readJson(res);
  // fetch NO lanza con 4xx/5xx: hay que revisar res.ok a mano.
  if (!res.ok) return describe(res, json);
  return { ok: true, data: json as T };
}
