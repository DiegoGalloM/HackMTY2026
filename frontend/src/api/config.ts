// URL del backend, en UN solo lugar.
//
// Por default apunta al backend local de cada quien. Para usar un backend
// compartido (o el desplegado), pongan VITE_API_URL en frontend/.env.local o
// en las variables del build (render.yaml): no hace falta tocar código.
export const API_BASE: string = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, "") ?? "http://localhost:8000";

/**
 * URL pública de la página de pago de una orden. El QR lleva esto.
 *
 * Se arma con el origen y el path actuales (la app usa HashRouter y `base:
 * "./"`, así que funciona igual en localhost, en Render o empaquetada). Si el
 * cliente escanea desde su celular, este origen tiene que ser alcanzable
 * desde su red: en desarrollo, `python dev.py --host 0.0.0.0` y abrir la app
 * por la IP de la laptop en vez de localhost.
 */
export function checkoutUrl(token: string): string {
  const { origin, pathname } = window.location;
  return `${origin}${pathname}#/pay/${token}`;
}
