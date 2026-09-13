// Espejo de la política de contraseñas del backend.
//
// El servidor sigue siendo la autoridad: esto solo existe para que el usuario
// vea al instante qué le falta en vez de enterarse después de un viaje de red.
// Si el backend responde weak_password, se muestran SUS problems (ver api.ts).

export type PasswordProblem =
  | "too_short"
  | "too_long"
  | "missing_lowercase"
  | "missing_uppercase"
  | "missing_digit"
  | "contains_username"
  | "too_common";

export const MIN_PASSWORD_LENGTH = 12;
export const MAX_PASSWORD_LENGTH = 128;

/** Traducción de cada código del backend a una frase que el usuario entienda. */
const PROBLEM_TEXT: Record<PasswordProblem, string> = {
  too_short: `Usa al menos ${MIN_PASSWORD_LENGTH} caracteres.`,
  too_long: `Usa como máximo ${MAX_PASSWORD_LENGTH} caracteres.`,
  missing_lowercase: "Incluye al menos una letra minúscula.",
  missing_uppercase: "Incluye al menos una letra mayúscula.",
  missing_digit: "Incluye al menos un número.",
  contains_username: "No incluyas tu usuario dentro de la contraseña.",
  too_common: "Esa contraseña es de las más usadas del mundo. Elige algo menos predecible.",
};

/**
 * El backend puede añadir códigos nuevos antes que el front: cualquier código
 * desconocido se muestra tal cual en vez de desaparecer del aviso.
 */
export function describePasswordProblem(code: string): string {
  return PROBLEM_TEXT[code as PasswordProblem] ?? code;
}

/**
 * Requisitos que se pintan como checklist. El orden es el de la lista visible.
 * `contains_username` no entra aquí: solo aplica si ya escribió un usuario, y
 * como regla en negativo confunde en una lista de "lo que sí debe tener".
 */
export const PASSWORD_RULES: { id: PasswordProblem; label: string; met: (password: string) => boolean }[] = [
  { id: "too_short", label: `${MIN_PASSWORD_LENGTH} caracteres o más`, met: (p) => p.length >= MIN_PASSWORD_LENGTH },
  { id: "missing_lowercase", label: "Una letra minúscula", met: (p) => /[a-z]/.test(p) },
  { id: "missing_uppercase", label: "Una letra mayúscula", met: (p) => /[A-Z]/.test(p) },
  { id: "missing_digit", label: "Un número", met: (p) => /\d/.test(p) },
];

/** Lista de problemas, vacía cuando la contraseña cumple todo. */
export function checkPassword(password: string, username = ""): PasswordProblem[] {
  const problems: PasswordProblem[] = [];
  for (const rule of PASSWORD_RULES) if (!rule.met(password)) problems.push(rule.id);
  if (password.length > MAX_PASSWORD_LENGTH) problems.push("too_long");

  // Se compara en minúsculas porque el usuario ya se normaliza así antes de
  // mandarlo; y solo desde 3 caracteres, que es el mínimo del username.
  const handle = username.trim().toLowerCase();
  if (handle.length >= 3 && password.toLowerCase().includes(handle)) problems.push("contains_username");

  return problems;
}

/** Texto ya traducido, listo para renderizar bajo el campo. */
export function passwordProblemMessages(password: string, username = ""): string[] {
  return checkPassword(password, username).map(describePasswordProblem);
}
