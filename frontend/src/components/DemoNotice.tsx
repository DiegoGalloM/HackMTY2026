// Los dos avisos de transparencia viven aquí para que la landing, la página
// pública de pago y la franja de la app digan exactamente lo mismo que el
// README (ver docs/ROADMAP_PULIDO.md, fases 1 y 8).

/** Lo mínimo que tiene que entender cualquiera que vea UNA sola pantalla. */
export const DEMO_NOTICE =
  "Esto es una demo: todas las transacciones son simuladas. No se procesa dinero real ni se conecta a cuentas bancarias reales.";

/** Disclaimer de no afiliación con Capital One. */
export const AFFILIATION_DISCLAIMER =
  "Capital One Business fue construido en 36 horas para el reto de Capital One en HackMTY 2026. No es un producto de Capital One ni está afiliado, respaldado o patrocinado por Capital One, N.A. — el nombre y la identidad visual se usan únicamente para describir honestamente el reto para el que fue construido.";

/** La etiqueta corta de la franja persistente dentro de la app. */
export const DEMO_BADGE = "Modo demo — datos simulados";

interface DemoNoticeProps {
  className?: string;
}

/**
 * Pie de transparencia: primero el aviso de demo, legible y no en letra
 * pequeña, y debajo el disclaimer de afiliación.
 *
 * <aside> con nombre y no <footer>: un footer dentro de un <section> (como en
 * la landing) pierde su rol de landmark y los lectores de pantalla no lo
 * anuncian; el aside nombrado es un landmark en cualquier lugar.
 */
export default function DemoNotice({ className = "" }: DemoNoticeProps) {
  return (
    <aside className={`text-center ${className}`} aria-label="Aviso de demo">
      <p className="text-[13px] leading-snug font-semibold text-ink">{DEMO_NOTICE}</p>
      <p className="mt-2 text-[11px] leading-snug text-muted">{AFFILIATION_DISCLAIMER}</p>
    </aside>
  );
}
