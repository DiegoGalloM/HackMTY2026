// Contexto del negocio activo: sesión, cliente de la API ya atado al dueño
// y un contador de versión que las pantallas usan para recargar cuando algo
// cambió (una venta pagada, un ticket aplicado).
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { businessApi, type BusinessApi } from "../api/finance";
import type { Session } from "../auth/session";

export interface LocalProfile {
  category: string | null;
  answers: Record<string, boolean>;
  name?: string;
  lastName?: string;
}

interface BusinessState {
  session: Session | null;
  ownerId: string | null;
  businessName: string;
  api: BusinessApi | null;
  profile: LocalProfile | null;
  /** Cambia cada vez que algo financiero se modificó: las consultas lo usan como dependencia. */
  version: number;
  refresh: () => void;
}

const BusinessContext = createContext<BusinessState | null>(null);

export function BusinessProvider({ session, profile, children }: { session: Session | null; profile: LocalProfile | null; children: ReactNode }) {
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  const value = useMemo<BusinessState>(
    () => ({
      session,
      ownerId: session?.user.user_id ?? null,
      businessName: session?.user.business_name ?? "Mi negocio",
      api: session ? businessApi(session.user.user_id, session.token) : null,
      profile,
      version,
      refresh,
    }),
    [session, profile, version, refresh],
  );
  return <BusinessContext.Provider value={value}>{children}</BusinessContext.Provider>;
}

export function useBusiness(): BusinessState {
  const ctx = useContext(BusinessContext);
  if (!ctx) throw new Error("useBusiness fuera de <BusinessProvider>");
  return ctx;
}
