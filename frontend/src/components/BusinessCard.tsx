import { useId } from "react";
import "./BusinessCard.css";

/** Original demo artwork: all shapes and lettering are rendered inline. */
export default function BusinessCard() {
  const id = useId();

  return (
    <svg
      className="business-card"
      viewBox="0 0 660 400"
      role="img"
      aria-labelledby={`${id}-title`}
      focusable="false"
    >
      <title id={`${id}-title`}>
        CAPITAL ONE BUSINESS. Tarjeta de demostración terminada en 4242.
        Titular: NEGOCIO DEMO.
      </title>
      <defs>
        <linearGradient id={`${id}-light`} x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="white" stopOpacity=".13" />
          <stop offset=".5" stopColor="white" stopOpacity="0" />
          <stop offset="1" stopColor="black" stopOpacity=".38" />
        </linearGradient>
        <linearGradient id={`${id}-chip`} x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#eee3be" />
          <stop offset=".5" stopColor="#c7b77e" />
          <stop offset="1" stopColor="#f1e8cf" />
        </linearGradient>
        <clipPath id={`${id}-outline`}>
          <rect width="660" height="400" rx="28" />
        </clipPath>
      </defs>
      <g aria-hidden="true" clipPath={`url(#${id}-outline)`}>
        <rect width="660" height="400" fill="var(--c1-navy)" />
        <rect width="660" height="400" fill={`url(#${id}-light)`} />
        {/* Geometric accents, deliberately independent of any bank logo. */}
        <path d="M470 0H660V400H610L410 200Z" fill="white" opacity=".035" />
        <path d="M520 0 320 400M625 0 425 400" stroke="white" strokeOpacity=".07" />
        <rect x="1.5" y="1.5" width="657" height="397" rx="27" fill="none" stroke="white" strokeOpacity=".25" />

        <g fill="var(--c1-white)" textAnchor="end">
          <text x="610" y="66" fontSize="27" fontWeight="700" letterSpacing="2">CAPITAL ONE</text>
          <text x="610" y="95" fontSize="17" fontWeight="500" letterSpacing="5">BUSINESS</text>
        </g>
        <rect x="557" y="113" width="53" height="5" rx="2.5" fill="var(--c1-red)" />

        <g transform="translate(54 143)" stroke="#756b4d" strokeWidth="1.7">
          <rect width="85" height="66" rx="13" fill={`url(#${id}-chip)`} />
          <rect x="28" y="18" width="29" height="30" rx="7" fill="none" />
          <path d="M0 23H28M0 43H28M57 23H85M57 43H85M26 0 34 18M59 0 51 18M26 66 34 48M59 66 51 48" fill="none" />
        </g>

        <text x="54" y="272" fill="var(--c1-white)" fontFamily="ui-monospace, monospace" fontSize="31" letterSpacing="2">•••• •••• •••• 4242</text>
        <text x="54" y="352" fill="var(--c1-white)" fontSize="20" fontWeight="500" letterSpacing="3">NEGOCIO DEMO</text>
      </g>
    </svg>
  );
}
