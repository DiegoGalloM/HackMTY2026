import type { Ref } from "react";

interface SwooshProps {
  className?: string;
}

/**
 * Contorno del swoosh de Capital One, vectorizado (el mismo trazo que
 * public/swoosh.svg). Va embebido y no como <img src="/swoosh.svg"> por dos
 * razones: así toma el color con `currentColor` (el archivo trae el fill negro
 * fijo) y así la landing puede animarlo como un elemento más del DOM.
 *
 * El <g> conserva el transform del trazo original (invierte el eje Y, que es
 * como lo exporta el vectorizador) y el viewBox está recortado a la caja real
 * de la figura, para que posicionarla no dependa del relleno vacío del SVG.
 *
 * preserveAspectRatio="none": el trazo es proporcionalmente más alto que el
 * swoosh del logo oficial, así que se achata a la medida que le da el
 * contenedor en vez de deformar el resto del logo para acomodarlo.
 */
export function Swoosh({ className }: SwooshProps) {
  return (
    <svg
      viewBox="0 124.38 512 263.11"
      preserveAspectRatio="none"
      aria-hidden
      className={className}
    >
      <g transform="translate(0,512) scale(0.1,-0.1)" fill="currentColor">
        <path d="M3600 3874 c-714 -29 -1559 -123 -2495 -280 -445 -74 -1083 -199 -1100 -215 -13 -13 -11 -13 257 31 571 93 1144 160 1733 202 281 20 1021 17 1213 -5 392 -45 640 -124 773 -245 81 -74 104 -126 104 -237 0 -83 -3 -96 -38 -169 -77 -162 -162 -257 -457 -510 -212 -182 -514 -428 -616 -501 -135 -97 -466 -314 -771 -504 -161 -101 -293 -187 -293 -192 0 -12 -12 -19 665 346 319 172 659 359 755 415 296 174 779 474 921 571 389 267 658 505 782 692 45 68 87 174 87 221 -1 185 -255 310 -735 361 -142 15 -608 26 -785 19z" />
      </g>
    </svg>
  );
}

/**
 * Refs opcionales a cada pieza del logo. Existen para que la intro de la
 * landing pueda animarlas por separado (ver landing/Landing.tsx) sin duplicar
 * este markup: el logo se define en un solo lugar.
 */
export interface LogoPartRefs {
  capital?: Ref<HTMLSpanElement>;
  one?: Ref<HTMLSpanElement>;
  swoosh?: Ref<HTMLSpanElement>;
  business?: Ref<HTMLDivElement>;
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
  /** Refs por pieza, solo para animar la entrada en la landing. */
  partRefs?: LogoPartRefs;
}

/**
 * Wordmark "Capital One" con el swoosh cruzando por detrás.
 */
export default function CapitalOneLogo({
  className = "",
  withSwoosh = true,
  business = false,
  partRefs,
}: LogoProps) {
  return (
    <div
      className={`relative inline-block leading-none ${className}`}
      role="img"
      aria-label={business ? "Capital One Business" : "Capital One"}
    >
      {/* El swoosh va primero en el DOM y el wordmark lleva `relative`: así el
          texto se pinta encima sin recurrir a un z-index negativo, que lo
          mandaría detrás del fondo de la pantalla y lo haría invisible.
          Medidas sacadas de comparar contra el logo oficial
          (public/logo-capital-one-business.jpeg): la cola nace arriba de
          "Capital", el cuerpo grueso queda sobre "One" y el gancho baja
          cruzando el texto hasta justo encima de "BUSINESS". */}
      {withSwoosh && (
        <span
          ref={partRefs?.swoosh}
          className="pointer-events-none absolute -top-[0.38em] -right-[0.03em] block h-[1.34em] w-[82%] text-[#d22e1e]"
          aria-hidden
        >
          <Swoosh className="block h-full w-full" />
        </span>
      )}

      {/* La marca Capital One usa una tipografía serif para ambas palabras */}
      <span className="relative block font-serif font-bold tracking-tight text-[#003a6f]">
        <span ref={partRefs?.capital} className="inline-block">
          Capital
        </span>
        {/* `isolate` + `-z-10` dejan el relleno por debajo del texto del span
            pero dentro de su propio contexto de apilamiento, así tapa el
            swoosh sin irse detrás de él ni del fondo de la pantalla. */}
        <span ref={partRefs?.one} className="relative isolate inline-block font-normal italic">
          {withSwoosh && (
            <span
              aria-hidden
              className="absolute -z-10 top-[0.156em] left-[0.106em] h-[0.69em] w-[0.555em] rotate-[4deg] rounded-[50%] bg-white"
            />
          )}
          One
        </span>
      </span>

      {/* Alineado a la derecha (debajo de "One") y con el tono teal del logo.
          El margen derecho negativo cancela el espacio que `tracking` agrega
          después de la última letra; sin él la palabra queda descuadrada. */}
      {business && (
        <div
          ref={partRefs?.business}
          className="relative -mr-[0.35em] mt-0.5 text-right font-sans text-[0.32em] font-semibold tracking-[0.35em] text-[#006778]"
        >
          BUSINESS
        </div>
      )}
    </div>
  );
}
