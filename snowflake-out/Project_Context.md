Repository: HackMTY2026 Capital One business-finance prototype.

Architecture:
- frontend/: React 19 + TypeScript/Vite + React Router + Framer Motion + Tailwind.
- backend/: FastAPI service exposing accounts, transactions, business-profile, and health endpoints.
- desktop/: documentation for packaging the same frontend build with Tauri or Electron.
- graphify-out/: generated architecture graph and report.

Frontend entry:
- frontend/src/main.tsx -> HashRouter -> frontend/src/App.tsx.
- App.tsx manages welcome -> onboarding -> account stages.
- Account stage renders route-based screens under frontend/src/screens/.
- Shared visual components are under frontend/src/components/.
- Current dashboard data comes mostly from frontend/src/data/mock.ts.
- Onboarding state is local React state and is intended to POST a BusinessProfile to the backend.
- financial-literacy/insights.js maps onboarding answers to educational recommendations.

Backend entry:
- backend/app/main.py creates FastAPI app, configures CORS, and registers routers.
- routers/accounts.py exposes account lookup/listing.
- routers/transactions.py exposes transaction listing and simulated purchases.
- routers/business_profile.py exposes profile save/read/category statistics.
- models/schemas.py defines API contracts.

Provider abstraction:
- Routers depend on NessieClient through get_nessie_client().
- NessieClient is implemented by MockNessieClient and RealNessieClient.
- USE_MOCK_NESSIE or missing API key selects mock mode.
- RealNessieClient normalizes purchases, transfers, deposits, and withdrawals into Transaction objects.
- MockNessieClient generates account and transaction data in memory for offline demos/tests.

Profile storage abstraction:
- Business-profile router depends on ProfileStore through get_store().
- MemoryProfileStore is the default.
- SnowflakeProfileStore is selected when Snowflake settings are enabled.
- Both stores must preserve the same BusinessProfile/category-statistics behavior.

Analytics:
- backend/app/services/insights.py is currently a placeholder.
- Future domain logic should likely connect transactions, profiles, category statistics, and frontend analysis/education screens.

Planning guidance:
- For frontend API integration, start with frontend/src/data/mock.ts and the relevant screen, then add an API client/data-loading layer.
- For new backend domain behavior, add schemas in backend/app/models/schemas.py, routes in backend/app/routers/, and business logic in backend/app/services/.
- Do not call httpx directly from routers or services; use NessieClient.
- Preserve MockNessieClient and RealNessieClient interface compatibility.
- Do not create separate web and desktop frontends; desktop should package frontend/dist.
- The final product domain is still evolving, so avoid overcommitting to the placeholder analytics implementation.