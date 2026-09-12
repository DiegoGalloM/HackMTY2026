import { useId } from "react";

interface SwooshProps {
  className?: string;
}

/**
 * El swoosh de Capital One: elipse exterior menos una elipse interior corrida
 * a la izquierda y un pelo más chica. La diferencia queda gruesa en el extremo
 * derecho y se afila en dos puntas hacia la izquierda — la silueta del logo.
 *
 * Va con máscara y no con fill-rule="evenodd" porque la elipse interior se
 * sale por la izquierda de la exterior: con evenodd ese pedazo se pintaría.
 */
export function Swoosh({ className }: SwooshProps) {
  // id único: el logo puede renderizarse más de una vez en la misma página.
  // Se limpian los caracteres raros de useId (`:r0:`, `«r0»`) porque van
  // dentro de un `url(#…)` y no todos los navegadores los aceptan ahí.
  const maskId = `swoosh-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;

  // La inclinación se aplica por CSS sobre el <svg>, no con un `transform`
  // adentro: así la máscara y la elipse quedan en el mismo espacio sin
  // depender del orden en que el navegador resuelve transform vs. mask.
  return (
    <svg viewBox="0 0 100 44" aria-hidden className={`-rotate-6 ${className}`}>
      <mask id={maskId}>
        <rect width="100" height="44" fill="white" />
        <ellipse cx="46.29" cy="22" rx="46.04" ry="19.53" fill="black" />
      </mask>
      <ellipse
        cx="50"
        cy="22"
        rx="49.5"
        ry="21"
        fill="currentColor"
        mask={`url(#${maskId})`}
      />
    </svg>
  );
}

interface LogoProps {
  /** Clases de tipografía (tamaño y color del wordmark). */
  className?: string;
  /**
   * Dibuja el swoosh detrás del wordmark. Se apaga cuando el contenedor ya
   * tiene un swoosh grande de fondo (la tarjeta), para no repetirlo.
   */
  withSwoosh?: boolean;
  /**
   * Agrega "BUSINESS" en versalitas espaciadas debajo del wordmark, como en
   * el logo oficial de Capital One Business (tarjetas, member center).
   */
  business?: boolean;
}

/**
 * Wordmark "Capital One" con el swoosh cruzando por detrás. El texto es HTML
 * y no SVG para que herede el tamaño de fuente del contenedor.
 */
export default function CapitalOneLogo({
  className = "",
  withSwoosh = true,
  business = false,
}: LogoProps) {
  return (
    <div
      className={`relative inline-block leading-none ${className}`}
      role="img"
      aria-label={business ? "Capital One Business" : "Capital One"}
    >
      {withSwoosh && (
        <Swoosh className="pointer-events-none absolute -top-[0.75em] -right-[0.5em] w-[120%] text-accent" />
      )}
      <span className="relative font-bold tracking-tight">
        Capital<span className="font-serif font-normal italic">One</span>
      </span>
      {business && (
        <div className="relative mt-0.5 text-[0.32em] font-semibold tracking-[0.35em] opacity-90">
          BUSINESS
        </div>
      )}
    </div>
  );
}
