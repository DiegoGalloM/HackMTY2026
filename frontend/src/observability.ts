// Visibilidad básica de errores del frontend (Fase 6 del roadmap).
//
// Con VITE_SENTRY_DSN los errores se mandan a Sentry (capa gratuita). Sin DSN
// el SDK ni siquiera se descarga (import dinámico): el demo no paga ese peso y
// los errores sólo quedan en la consola.
//
// Nunca sale hacia Sentry: el token del QR (#/pay/<token>), query strings de
// URLs, ni datos de usuario. La sesión vive en sessionStorage y el SDK no la lee.

import type { Breadcrumb, ErrorEvent } from "@sentry/react";

type SentryModule = typeof import("@sentry/react");

const DSN = (import.meta.env.VITE_SENTRY_DSN as string | undefined)?.trim();

const PAY_TOKEN = /(\/pay\/)[^/?#\s"']+/g;
const URL_QUERY = /(https?:\/\/[^\s?#"']+)\?[^\s#"']*/g;

let sentry: SentryModule | null = null;
let loading: Promise<SentryModule | null> | null = null;

export function scrubText(value: string): string {
  return value.replace(URL_QUERY, "$1?[filtrado]").replace(PAY_TOKEN, "$1[token]");
}

export function scrubEvent(event: ErrorEvent): ErrorEvent {
  if (event.request) {
    if (event.request.url) event.request.url = scrubText(event.request.url);
    delete event.request.headers;
    delete event.request.cookies;
    delete event.request.query_string;
    delete event.request.data;
  }
  delete event.user;
  if (event.transaction) event.transaction = scrubText(event.transaction);
  for (const exception of event.exception?.values ?? []) {
    if (exception.value) exception.value = scrubText(exception.value);
  }
  for (const crumb of event.breadcrumbs ?? []) scrubBreadcrumb(crumb);
  return event;
}

export function scrubBreadcrumb(crumb: Breadcrumb): Breadcrumb {
  if (crumb.message) crumb.message = scrubText(crumb.message);
  if (crumb.data) {
    for (const key of ["url", "from", "to"]) {
      const value = crumb.data[key];
      if (typeof value === "string") crumb.data[key] = scrubText(value);
    }
  }
  return crumb;
}

/** Activa Sentry si hay DSN. Resuelve true si quedó activo. */
export function initErrorTracking(): Promise<boolean> {
  if (!DSN) return Promise.resolve(false);
  loading ??= import("@sentry/react")
    .then((mod) => {
      mod.init({
        dsn: DSN,
        environment: (import.meta.env.VITE_SENTRY_ENVIRONMENT as string | undefined) ?? import.meta.env.MODE,
        sendDefaultPii: false,
        tracesSampleRate: 0, // sólo errores: la capa gratuita alcanza
        beforeSend: scrubEvent,
        beforeBreadcrumb: scrubBreadcrumb,
      });
      sentry = mod;
      return mod;
    })
    .catch((err) => {
      console.warn("No se pudo cargar el tracking de errores:", err);
      return null;
    });
  return loading.then(Boolean);
}

/**
 * Reporta un error atrapado (p. ej. por un ErrorBoundary). Regresa el id del
 * evento de Sentry para mostrarlo como referencia, o null si Sentry está apagado.
 */
export function reportError(error: unknown, context?: Record<string, unknown>): string | null {
  console.error(error);
  if (!sentry) return null;
  return sentry.captureException(error, context ? { extra: context } : undefined);
}
