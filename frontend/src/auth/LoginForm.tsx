import { useId, useState, type FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, LoaderCircle } from "lucide-react";
import { login } from "./api";
import type { Session } from "./session";

interface LoginFormProps {
  onAuthenticated: (session: Session) => void;
  onSwitchToRegister: () => void;
}

type FieldKey = "username" | "password";

/**
 * Inicio de sesión contra POST /auth/login.
 *
 * A propósito NO valida la política de contraseñas: quien ya tiene cuenta pudo
 * crearla con reglas anteriores, y bloquearle el acceso en el cliente lo
 * dejaría fuera de su propia cuenta. Solo se exige que los campos no vayan
 * vacíos; de la verdad se encarga el servidor.
 */
export default function LoginForm({ onAuthenticated, onSwitchToRegister }: LoginFormProps) {
  const uid = useId();
  const [values, setValues] = useState({ username: "", password: "" });
  const [errors, setErrors] = useState<Partial<Record<FieldKey, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [reveal, setReveal] = useState(false);
  const [busy, setBusy] = useState(false);

  const fieldId = (name: FieldKey) => `${uid}-${name}`;
  const set = (name: FieldKey) => (event: { target: { value: string } }) =>
    setValues((prev) => ({ ...prev, [name]: event.target.value }));
  const describedBy = (name: FieldKey) => (errors[name] ? `${fieldId(name)}-error` : undefined);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;

    const username = values.username.trim().toLowerCase();
    const next: Partial<Record<FieldKey, string>> = {};
    if (!username) next.username = "Escribe tu usuario.";
    if (!values.password) next.password = "Escribe tu contraseña.";
    setErrors(next);
    setFormError(null);

    const firstInvalid = (["username", "password"] as FieldKey[]).find((key) => next[key]);
    if (firstInvalid) {
      document.getElementById(fieldId(firstInvalid))?.focus();
      return;
    }

    setBusy(true);
    const result = await login({ username, password: values.password });

    if (result.ok) {
      onAuthenticated(result.session);
      return;
    }

    // La contraseña se queda escrita: reescribirla entera por un typo en el
    // usuario es la forma más rápida de que alguien abandone el login.
    setBusy(false);
    setFormError(result.message);
  };

  return (
    <form className="entry-form" onSubmit={handleSubmit} noValidate>
      <div className="entry-field">
        <label htmlFor={fieldId("username")}>Usuario</label>
        <input
          id={fieldId("username")} name="username" type="text" autoComplete="username"
          autoCapitalize="none" autoCorrect="off" spellCheck={false}
          placeholder="Tu usuario" value={values.username} onChange={set("username")}
          aria-invalid={errors.username ? true : undefined} aria-describedby={describedBy("username")}
        />
        {errors.username && <p className="entry-error" id={`${fieldId("username")}-error`} role="alert">{errors.username}</p>}
      </div>

      <div className="entry-field">
        <label htmlFor={fieldId("password")}>Contraseña</label>
        <div className="entry-input-reveal">
          <input
            id={fieldId("password")} name="password" type={reveal ? "text" : "password"} autoComplete="current-password"
            value={values.password} onChange={set("password")}
            aria-invalid={errors.password ? true : undefined} aria-describedby={describedBy("password")}
          />
          <button type="button" className="entry-reveal" aria-pressed={reveal}
            aria-label={reveal ? "Ocultar contraseña" : "Mostrar contraseña"} onClick={() => setReveal((on) => !on)}>
            {reveal ? <EyeOff size={18} aria-hidden /> : <Eye size={18} aria-hidden />}
          </button>
        </div>
        {errors.password && <p className="entry-error" id={`${fieldId("password")}-error`} role="alert">{errors.password}</p>}
      </div>

      {formError && <p className="entry-form-error" role="alert">{formError}</p>}

      <div className="entry-actions">
        <button type="submit" className="entry-primary" disabled={busy} aria-busy={busy}>
          {busy
            ? <><LoaderCircle className="entry-spinner" size={18} aria-hidden /> Entrando…</>
            : <>Entrar a mi cuenta <ArrowRight size={18} aria-hidden /></>}
        </button>
        <button type="button" className="entry-switch" onClick={onSwitchToRegister} disabled={busy}>
          ¿Es tu primera vez? Regístrate
        </button>
      </div>
    </form>
  );
}
