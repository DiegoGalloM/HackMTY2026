// Sesión del usuario: token + datos públicos, guardados en sessionStorage.
//
// sessionStorage y no localStorage a propósito: el token muere al cerrar la
// pestaña, que es lo que se espera de un dispositivo compartido (varias
// personas atendiendo el mismo negocio con la misma tablet).

export interface UserPublic {
  user_id: string;
  username: string;
  business_name: string;
  full_name: string;
  /** "YYYY-MM-DD", tal como lo manda el backend. */
  birthdate: string;
}

export interface Session {
  token: string;
  user: UserPublic;
  /** Epoch en ms. Se calcula al guardar a partir de expires_in (segundos). */
  expiresAt: number;
}

/** Una sola llave: así clearSession() no puede dejar restos a medias. */
export const SESSION_KEY = "c1b.session";

/**
 * Construye la sesión a partir de la respuesta de /auth/register|login.
 * El expires_in del backend es relativo; aquí se vuelve absoluto para poder
 * comparar contra Date.now() sin arrastrar el momento de la petición.
 */
export function sessionFromAuth(payload: { access_token: string; expires_in: number; user: UserPublic }): Session {
  return {
    token: payload.access_token,
    user: payload.user,
    expiresAt: Date.now() + Math.max(0, payload.expires_in) * 1000,
  };
}

/**
 * Devuelve la sesión solo si sigue vigente. Es el único lugar que decide si un
 * token sirve, así ninguna pantalla usa uno caducado por su cuenta.
 */
export function activeSession(session: Session | null): Session | null {
  if (!session) return null;
  return session.expiresAt > Date.now() ? session : null;
}

/**
 * Todo acceso a sessionStorage va en try/catch: en modo privado de Safari, con
 * cookies de terceros bloqueadas o con las políticas de un navegador
 * corporativo, leer o escribir *lanza* — y tirar la app entera por no poder
 * cachear un token sería absurdo. Sin storage la sesión solo vive en memoria.
 */
export function readSession(): Session | null {
  let raw: string | null = null;
  try {
    raw = window.sessionStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
  if (!raw) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    // JSON corrupto (otra versión del formato, storage manipulado a mano):
    // se descarta en vez de arrastrar el problema a cada lectura.
    clearSession();
    return null;
  }

  const session = parsed as Partial<Session> | null;
  if (!session || typeof session.token !== "string" || typeof session.expiresAt !== "number" || !session.user) {
    clearSession();
    return null;
  }

  const live = activeSession(session as Session);
  if (!live) clearSession();
  return live;
}

export function saveSession(session: Session): void {
  try {
    window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // Ignorado a propósito: el estado de React ya tiene la sesión, solo
    // perdemos la posibilidad de sobrevivir a un refresh.
  }
}

export function clearSession(): void {
  try {
    window.sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // Ídem: si no se puede borrar, no hay nada más que hacer aquí.
  }
}
