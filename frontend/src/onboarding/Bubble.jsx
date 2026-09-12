// frontend/src/onboarding/Bubble.jsx
export function Bubble({ label, icon, selected, onClick, size = "normal", variant }) {
  const classes = ["bubble", size === "large" ? "bubble--large" : "", selected ? "bubble--selected" : "", variant ? `bubble--${variant}` : ""]
    .filter(Boolean).join(" ");
  return (
    <button type="button" className={classes} onClick={onClick}>
      {icon && <span className="bubble__icon">{icon}</span>}
      {label}
    </button>
  );
}

export function BubbleGrid({ children }) {
  return <div className="bubble-grid">{children}</div>;
}