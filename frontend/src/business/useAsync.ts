// Hook de consulta: carga, error, vacío y recarga, sin librería.
import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";
import type { ApiError, ApiResult } from "../api/client";
import type { BusinessApi } from "../api/finance";
import { useBusiness } from "./BusinessContext";

export type QueryState<T> =
  | { status: "no-session"; data: null; error: null }
  | { status: "loading"; data: T | null; error: null }
  | { status: "error"; data: T | null; error: ApiError }
  | { status: "ready"; data: T; error: null };

export interface Query<T> {
  state: QueryState<T>;
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  reload: () => void;
}

/**
 * Ejecuta `fn(api)` cuando hay sesión y cada vez que cambian `deps` o la
 * versión del negocio (algo se vendió, se compró, se ajustó). El dato
 * anterior se conserva mientras recarga para que la pantalla no parpadee.
 */
export function useBusinessQuery<T>(fn: (api: BusinessApi) => Promise<ApiResult<T>>, deps: DependencyList = []): Query<T> {
  const { api, version } = useBusiness();
  const [state, setState] = useState<QueryState<T>>(api ? { status: "loading", data: null, error: null } : { status: "no-session", data: null, error: null });
  const [tick, setTick] = useState(0);
  const latest = useRef(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!api) {
      setState({ status: "no-session", data: null, error: null });
      return;
    }
    const run = ++latest.current;
    setState((prev) => ({ status: "loading", data: prev.data, error: null }));
    fnRef.current(api).then((result) => {
      if (run !== latest.current) return; // llegó una respuesta vieja
      if (result.ok) setState({ status: "ready", data: result.data, error: null });
      else setState((prev) => ({ status: "error", data: prev.data, error: result }));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, version, tick, ...deps]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { state, data: state.data, loading: state.status === "loading", error: state.status === "error" ? state.error : null, reload };
}
