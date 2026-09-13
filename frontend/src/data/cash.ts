/**
 * Denominaciones de billetes para el cobro en efectivo.
 *
 * `tint` es el color dominante del billete real, usado por <Banknote /> para
 * dibujarlo. Son aproximaciones de la familia G de Banxico — si consiguen
 * escaneos reales de los billetes, ver el comentario en Banknote.tsx.
 */
export interface Denomination {
  value: number;
  /** Color base del billete. */
  tint: string;
  /** Tono más claro, para el degradado. */
  tintLight: string;
}

export const denominations: Denomination[] = [
  { value: 20, tint: "#0f8a8a", tintLight: "#7fd4cf" },
  { value: 50, tint: "#7a3f9d", tintLight: "#c9a3dd" },
  { value: 100, tint: "#b8323c", tintLight: "#e79aa0" },
  { value: 200, tint: "#2f7d46", tintLight: "#9ed0ac" },
  { value: 500, tint: "#26558f", tintLight: "#9db8d8" },
  { value: 1000, tint: "#8a5a2b", tintLight: "#d6b48c" },
];
