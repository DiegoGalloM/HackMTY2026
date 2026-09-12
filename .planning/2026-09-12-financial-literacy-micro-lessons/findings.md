# Findings & Decisions

## Requirements
- Add three practical micro-lessons for micro-businesses: next-seven-days cash, margin per sale, and simple inventory movement.
- Each must need at most three simple inputs and give an immediate Spanish result.
- Reuse the existing financial-literacy entry card and visual theme.

## Research Findings
- `CashInsightCard` currently selects one trigger from onboarding `{ category, answers }`, sits in `Cuenta` below the bank card, and only logs its action.
- `App.tsx` holds the onboarding profile in memory and passes it to `Cuenta`.
- The frontend uses React 19, TypeScript and Tailwind plus `theme.css`; JSX modules are supported by `allowJs`.
- Production build completes after adding `MicroLessonDialog.jsx` and its styling. The available Computer Use browser surface was unavailable, so no visual automation could run.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use a compact overlay/modal for the lesson journey | Preserves the home layout and lets a user return after one short interaction. |
| Use chips and two numeric fields rather than a form/table | Matches the user's requirement to keep registration simple and quick. |
| Require three amounts for cash, two for margin, and one selection plus optional amount for inventory | Keeps each lesson within the one-minute constraint while still producing a concrete result. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
- Existing `frontend/src/financial-literacy/insights.js` triggers.
