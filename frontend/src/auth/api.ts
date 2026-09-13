// Cliente de /auth. Traduce el contrato del backend a un resultado que la UI
// pueda pintar sin saber nada de códigos HTTP.
import { describePasswordProblem } from "./passwordPolicy";
import { sessionFromAuth, type Session, type UserPublic } from "./session";

// La URL del backend vive en api/config.ts (VITE_API_URL o el local de cada quien).
import { apiFetch, type ApiResult } from "../api/client";
import { API_BASE } from "../api/config";

export interface RegisterInput {
  username: string;
  business_name: string;
  full_name: string;
  /** "YYYY-MM-DD". */
  birthdate: string;
  password: string;
}

export interface LoginInput {
  username: string;
  password: string;
}

export type AuthFailureKind =
  | "username_taken"
  | "invalid_credentials"
  | "weak_password"
  | "validation"
  | "unauthorized"
  | "network"
  | "unexpected";

export interface AuthFailure {
  ok: false;
  kind: AuthFailureKind;
  /** Ya en español y listo para mostrarse en un role="alert". */
  message: string;
  /** Reglas de contraseña que el servidor rechazó, traducidas. */
  problems: string[];
  /** Campo al que pintarle el error, si el fallo es de uno en concreto. */
  field?: "username" | "password";
}

export type AuthResult = { ok: true; session: Session } | AuthFailure;

/** El perfil del onboarding tal como lo guarda el backend (BusinessProfile). */
export interface BusinessProfile {
  category: string;
  category_detail: string | null;
  operating_days: string[];
  city: string;
  employees: string | null;
  answers: Record<string, boolean>;
  week_description_mode: string | null;
  week_description_text: string | null;
}

/**
 * GET /business-profile/{ownerId}: el perfil guardado, o null si la cuenta
 * todavía no terminó la encuesta. Es lo que decide, después de cualquier
 * login o registro, si se entra a la app o a la encuesta.
 */
export function getProfile(ownerId: string, token: string): Promise<ApiResult<BusinessProfile | null>> {
  return apiFetch<BusinessProfile | null>(`/business-profile/${encodeURIComponent(ownerId)}`, { token });
}
export type MeResult = { ok: true; user: UserPublic } | AuthFailure;

export const NETWORK_MESSAGE = "No se pudo conectar con el servidor. Revisa tu conexión y vuelve a intentar.";

/** Header que esperan los endpoints protegidos (incluido /business-profile). */
export function authHeaders(token: string | null | undefined): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function fail(kind: AuthFailureKind, message: string, extra: Partial<AuthFailure> = {}): AuthFailure {
  return { ok: false, kind, message, problems: [], ...extra };
}

/** El cuerpo puede venir vacío o no ser JSON (proxy, 502 de un gateway). */
async function readJson(res: Response): Promise<any> {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Traduce un 4xx/5xx de /auth a un fallo con mensaje en español.
 * `detail` llega como string en 401/409 y como objeto en weak_password.
 */
async function describeFailure(res: Response): Promise<AuthFailure> {
  const body = await readJson(res);
  const detail = body?.detail;

  if (res.status === 409 || detail === "username_taken") {
    return fail("username_taken", "Ese usuario ya está registrado. Prueba con otro.", { field: "username" });
  }
  if (res.status === 401 || detail === "invalid_credentials") {
    return fail("invalid_credentials", "Usuario o contraseña incorrectos. Revísalos e inténtalo de nuevo.");
  }
  if (detail?.code === "weak_password") {
    const problems = Array.isArray(detail.problems) ? detail.problems.map(String).map(describePasswordProblem) : [];
    return fail("weak_password", "Tu contraseña todavía no cumple los requisitos.", { problems, field: "password" });
  }
  if (res.status === 422) {
    return fail("validation", "Algunos datos no tienen el formato que esperamos. Revísalos e inténtalo de nuevo.");
  }
  if (res.status === 403) {
    return fail("unauthorized", "Tu sesión expiró. Vuelve a iniciar sesión para continuar.");
  }
  return fail("unexpected", `No pudimos completar la operación (el servidor respondió ${res.status}). Inténtalo de nuevo.`);
}

/**
 * POST a /auth y, si todo va bien, la sesión ya construida.
 *
 * fetch NO lanza con 4xx/5xx: hay que revisar res.ok a mano. Si no, un 409 se
 * leería como registro exitoso y entraríamos a la app sin token.
 */
async function post(path: string, payload: RegisterInput | LoginInput): Promise<AuthResult> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // Las credenciales van SIEMPRE en el cuerpo: en la URL acabarían en los
      // logs del servidor, en el historial y en el header Referer.
      body: JSON.stringify(payload),
    });
  } catch {
    return fail("network", NETWORK_MESSAGE);
  }

  if (!res.ok) return await describeFailure(res);

  const body = await readJson(res);
  if (!body?.access_token || !body?.user) {
    // 2xx sin token: tampoco es un éxito utilizable.
    return fail("unexpected", "El servidor respondió sin sesión. Inténtalo de nuevo.");
  }
  return { ok: true, session: sessionFromAuth(body) };
}

export function register(input: RegisterInput): Promise<AuthResult> {
  return post("/auth/register", input);
}

export function login(input: LoginInput): Promise<AuthResult> {
  return post("/auth/login", input);
}

/** Valida un token guardado contra el backend. */
export async function me(token: string): Promise<MeResult> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders(token) });
  } catch {
    return fail("network", NETWORK_MESSAGE);
  }
  if (!res.ok) return await describeFailure(res);

  const body = await readJson(res);
  if (!body?.user_id) return fail("unexpected", "El servidor respondió sin usuario. Inténtalo de nuevo.");
  return { ok: true, user: body as UserPublic };
}
