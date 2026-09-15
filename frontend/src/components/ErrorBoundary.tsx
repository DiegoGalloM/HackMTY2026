import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { reportError } from "../observability";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Al cambiar (p. ej. la ruta), se descarta el error y se vuelve a intentar. */
  resetKey?: string;
  /** Texto y acción del botón. Por default recarga la app desde el inicio. */
  actionLabel?: string;
  onAction?: () => void;
}

interface ErrorBoundaryState {
  error: Error | null;
  eventId: string | null;
  resetKey?: string;
}

/**
 * Si una pantalla truena al renderizar, en vez de dejar la app en blanco se
 * muestra un mensaje con salida, y el error se reporta (a Sentry si está activo).
 */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null, eventId: null, resetKey: this.props.resetKey };

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { error };
  }

  static getDerivedStateFromProps(props: ErrorBoundaryProps, state: ErrorBoundaryState): Partial<ErrorBoundaryState> | null {
    // Navegar a otra pantalla limpia el error: la siguiente puede estar bien.
    if (props.resetKey !== state.resetKey) return { error: null, eventId: null, resetKey: props.resetKey };
    return null;
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.setState({ eventId: reportError(error, { componentStack: info.componentStack }) });
  }

  private handleAction = () => {
    if (this.props.onAction) {
      this.setState({ error: null, eventId: null });
      this.props.onAction();
      return;
    }
    window.location.hash = "#/";
    window.location.reload();
  };

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="flex h-full flex-1 flex-col items-center justify-center bg-surface px-6 text-center" role="alert">
        <AlertTriangle size={40} className="text-accent" aria-hidden />
        <h1 className="mt-4 text-xl font-semibold text-ink">Algo salió mal en esta pantalla</h1>
        <p className="mt-2 max-w-xs text-sm text-muted">No perdiste nada: tus datos siguen guardados. Puedes seguir desde otra pantalla.</p>
        {this.state.eventId && <p className="mt-3 text-[11px] text-muted">Referencia del error: {this.state.eventId.slice(0, 12)}</p>}
        <button
          type="button"
          onClick={this.handleAction}
          className="mt-6 inline-flex min-h-12 items-center gap-2 rounded-full bg-brand px-6 text-sm font-semibold text-white"
        >
          <RefreshCw size={16} aria-hidden /> {this.props.actionLabel ?? "Volver al inicio"}
        </button>
      </div>
    );
  }
}
