import { useId } from "react";
import type { Denomination } from "../data/cash";

interface BanknoteProps {
  denomination: Denomination;
}

/**
 * Billete estilizado en SVG: rectángulo con degradado en el color de la
 * denominación, un óvalo que hace de retrato y el número impreso.
 *
 * Se dibuja en vez de usar fotos porque el repo no trae escaneos de billetes.
 * Si consiguen imágenes reales, esto se reemplaza por un <img> aquí mismo y
 * el resto de la pantalla no cambia.
 */
export default function Banknote({ denomination }: BanknoteProps) {
  // id único por instancia: el degradado se referencia con url(#...) y en la
  // pantalla se renderizan seis billetes a la vez.
  const gradientId = `bn-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const { value, tint, tintLight } = denomination;

  return (
    <svg
      viewBox="0 0 120 62"
      role="img"
      aria-label={`Billete de ${value} pesos`}
      className="block aspect-[120/62] h-auto w-full rounded-[3px] shadow-sm ring-1 ring-black/10"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={tintLight} />
          <stop offset="1" stopColor={tint} />
        </linearGradient>
      </defs>

      <rect width="120" height="62" fill={`url(#${gradientId})`} />

      {/* Ventana transparente del polímero, a la derecha como en los reales. */}
      <rect
        x="96"
        y="8"
        width="16"
        height="46"
        rx="8"
        fill="#ffffff"
        opacity="0.35"
      />

      {/* Retrato. */}
      <ellipse cx="34" cy="31" rx="17" ry="22" fill="#000" opacity="0.16" />

      {/* Líneas que simulan el texto impreso. */}
      <rect x="58" y="40" width="30" height="3" rx="1.5" fill="#fff" opacity="0.5" />
      <rect x="58" y="46" width="20" height="3" rx="1.5" fill="#fff" opacity="0.35" />

      <text
        x="58"
        y="28"
        fill="#ffffff"
        fontSize="20"
        fontWeight="700"
        fontFamily="system-ui, sans-serif"
      >
        {value}
      </text>
    </svg>
  );
}
