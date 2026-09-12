import { pickBestTrigger } from "./insights.js";

export default function CashInsightCard({ profile }) {
  const trigger = pickBestTrigger(profile);

  if (!trigger) return null;

  return (
    <section className="cash-insight-card" aria-labelledby={`cash-insight-${trigger.id}`}>
      <div className="cash-insight-card__icon" aria-hidden="true">⚡</div>
      <div className="cash-insight-card__content">
        <h2 id={`cash-insight-${trigger.id}`} className="cash-insight-card__title">
          {trigger.title}
        </h2>
        <p className="cash-insight-card__body">{trigger.body}</p>
        <button
          type="button"
          className="cash-insight-card__action"
          onClick={() => console.log("Financial literacy action selected:", trigger.id)}
        >
          {trigger.action}
        </button>
      </div>
    </section>
  );
}
