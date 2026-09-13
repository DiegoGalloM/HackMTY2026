import { useId, useState, type FormEvent } from "react";
import { ArrowRight, Check, CircleSmall, Eye, EyeOff, LoaderCircle } from "lucide-react";
import { register } from "./api";
import { PASSWORD_RULES, checkPassword, describePasswordProblem } from "./passwordPolicy";
import type { Session } from "./session";

interface RegisterFormProps {
  /** Puede ser asíncrono: el formulario sigue ocupado mientras la app decide a dónde entrar. */
  onAuthenticated: (session: Session) => void | Promise<void>;
  onSwitchToLogin: () => void;
}

type FieldKey = "business_name" | "full_name" | "birthdate" | "username" | "password" | "confirm";

/** Orden visual: define a qué campo se manda el foco al fallar la validación. */
const FIELD_ORDER: FieldKey[] = ["business_name", "full_name", "birthdate", "username", "password", "confirm"];

const USERNAME_PATTERN = /^[a-z0-9._-]+$/;
const USERNAME_HINT = "Entre 3 y 32 caracteres: minúsculas, números, punto, guion o guion bajo.";

/**
 * Edad cumplida a día de hoy, o null si la fecha no existe (31 de febrero, año
 * de 3 cifras…). El backend valida lo mismo; esto solo evita el viaje de red.
 */
function ageFromBirthdate(birthdate: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(birthdate);
  if (!match) return null;
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const date = new Date(year, month - 1, day);
  // new Date(1990, 1, 31) rueda a marzo: comparar de vuelta descarta fechas
  // inexistentes que el navegador sí aceptaría en el value.
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;

  const today = new Date();
  const notYetThisYear =
    today.getMonth() < date.getMonth() || (today.getMonth() === date.getMonth() && today.getDate() < date.getDate());
  return today.getFullYear() - year - (notYetThisYear ? 1 : 0);
}

/**
 * Registro real contra POST /auth/register. Vive dentro de la bienvenida
 * (Welcome), en la pantalla del mockup de celular: una sola columna, porque a
 * 320px cualquier rejilla de dos campos deja inputs de 140px.
 */
export default function RegisterForm({ onAuthenticated, onSwitchToLogin }: RegisterFormProps) {
  const uid = useId();
  const [values, setValues] = useState({
    business_name: "",
    full_name: "",
    birthdate: "",
    username: "",
    password: "",
    confirm: "",
  });
  const [errors, setErrors] = useState<Partial<Record<FieldKey, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [passwordProblems, setPasswordProblems] = useState<string[]>([]);
  const [reveal, setReveal] = useState(false);
  const [busy, setBusy] = useState(false);

  const fieldId = (name: FieldKey) => `${uid}-${name}`;
  const set = (name: FieldKey) => (event: { target: { value: string } }) =>
    setValues((prev) => ({ ...prev, [name]: event.target.value }));

  /** Une el id del error con los de las ayudas en un solo aria-describedby. */
  const describedBy = (name: FieldKey, ...extra: (string | false | null)[]) => {
    const ids = [errors[name] ? `${fieldId(name)}-error` : null, ...extra].filter((id): id is string => !!id);
    return ids.length ? ids.join(" ") : undefined;
  };

  const username = values.username.trim().toLowerCase();

  const validate = (): Partial<Record<FieldKey, string>> => {
    const next: Partial<Record<FieldKey, string>> = {};
    if (!values.business_name.trim()) next.business_name = "Escribe el nombre de tu negocio.";
    else if (values.business_name.trim().length > 120) next.business_name = "Usa como máximo 120 caracteres.";
    if (!values.full_name.trim()) next.full_name = "Escribe tu nombre completo.";
    else if (values.full_name.trim().length > 120) next.full_name = "Usa como máximo 120 caracteres.";

    const age = ageFromBirthdate(values.birthdate);
    if (!values.birthdate) next.birthdate = "Escribe tu fecha de nacimiento.";
    else if (age === null) next.birthdate = "Esa fecha no existe. Revísala.";
    else if (age < 18) next.birthdate = "Necesitas tener al menos 18 años para abrir una cuenta.";
    else if (age > 120) next.birthdate = "Revisa el año: esa fecha parece muy antigua.";

    if (username.length < 3 || username.length > 32 || !USERNAME_PATTERN.test(username)) next.username = USERNAME_HINT;

    const problems = checkPassword(values.password, username);
    if (problems.length) next.password = "Tu contraseña todavía no cumple los requisitos.";
    else if (values.confirm !== values.password) next.confirm = "Las contraseñas no coinciden.";

    return next;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;

    const found = validate();
    setErrors(found);
    setFormError(null);
    // Se espeja la política del servidor para que ninguna contraseña que él
    // rechazaría salga del navegador. El servidor sigue siendo la autoridad.
    setPasswordProblems(found.password ? checkPassword(values.password, username).map(describePasswordProblem) : []);

    const firstInvalid = FIELD_ORDER.find((key) => found[key]);
    if (firstInvalid) {
      document.getElementById(fieldId(firstInvalid))?.focus();
      return;
    }

    setBusy(true);
    const result = await register({
      username,
      business_name: values.business_name.trim(),
      full_name: values.full_name.trim(),
      birthdate: values.birthdate,
      password: values.password,
    });

    if (result.ok) {
      // No se limpia nada: Welcome desmonta esta pantalla al avanzar.
      await onAuthenticated(result.session);
      return;
    }

    // Nunca se borra lo que escribió el usuario: solo se pinta el error.
    setBusy(false);
    setPasswordProblems(result.problems);
    if (result.field) {
      setErrors({ [result.field]: result.message });
      document.getElementById(fieldId(result.field))?.focus();
    } else {
      setErrors({});
      setFormError(result.message);
    }
  };

  const rulesId = `${uid}-password-rules`;
  const passwordAlert = errors.password || passwordProblems.length > 0;

  return (
    <form className="entry-form" onSubmit={handleSubmit} noValidate>
      <div className="entry-field">
        <label htmlFor={fieldId("business_name")}>Nombre de tu negocio</label>
        <input
          id={fieldId("business_name")} name="business_name" type="text" autoComplete="organization"
          placeholder="Ej. Tacos Don Beto" maxLength={120} value={values.business_name} onChange={set("business_name")}
          aria-invalid={errors.business_name ? true : undefined} aria-describedby={describedBy("business_name")}
        />
        {errors.business_name && <p className="entry-error" id={`${fieldId("business_name")}-error`} role="alert">{errors.business_name}</p>}
      </div>

      <div className="entry-field">
        <label htmlFor={fieldId("full_name")}>Tu nombre completo</label>
        <input
          id={fieldId("full_name")} name="full_name" type="text" autoComplete="name"
          placeholder="Ej. Roberto Ramírez" maxLength={120} value={values.full_name} onChange={set("full_name")}
          aria-invalid={errors.full_name ? true : undefined} aria-describedby={describedBy("full_name")}
        />
        {errors.full_name && <p className="entry-error" id={`${fieldId("full_name")}-error`} role="alert">{errors.full_name}</p>}
      </div>

      <div className="entry-field">
        <label htmlFor={fieldId("birthdate")}>Fecha de nacimiento</label>
        <input
          id={fieldId("birthdate")} name="birthdate" type="date" autoComplete="bday"
          value={values.birthdate} onChange={set("birthdate")}
          aria-invalid={errors.birthdate ? true : undefined}
          aria-describedby={describedBy("birthdate", `${fieldId("birthdate")}-hint`)}
        />
        <p className="entry-hint" id={`${fieldId("birthdate")}-hint`}>Debes tener 18 años o más.</p>
        {errors.birthdate && <p className="entry-error" id={`${fieldId("birthdate")}-error`} role="alert">{errors.birthdate}</p>}
      </div>

      <div className="entry-field">
        <label htmlFor={fieldId("username")}>Usuario</label>
        <input
          id={fieldId("username")} name="username" type="text" autoComplete="username"
          autoCapitalize="none" autoCorrect="off" spellCheck={false}
          placeholder="Ej. donbeto.tacos" maxLength={32} value={values.username} onChange={set("username")}
          aria-invalid={errors.username ? true : undefined}
          aria-describedby={describedBy("username", `${fieldId("username")}-hint`)}
        />
        <p className="entry-hint" id={`${fieldId("username")}-hint`}>{USERNAME_HINT}</p>
        {errors.username && <p className="entry-error" id={`${fieldId("username")}-error`} role="alert">{errors.username}</p>}
      </div>

      <div className="entry-field">
        <label htmlFor={fieldId("password")}>Contraseña</label>
        <div className="entry-input-reveal">
          <input
            id={fieldId("password")} name="password" type={reveal ? "text" : "password"} autoComplete="new-password"
            value={values.password} onChange={set("password")}
            aria-invalid={errors.password ? true : undefined}
            aria-describedby={describedBy("password", rulesId)}
          />
          {/* aria-pressed comunica el estado sin que la etiqueta cambie a media lectura. */}
          <button type="button" className="entry-reveal" aria-pressed={reveal}
            aria-label={reveal ? "Ocultar contraseña" : "Mostrar contraseña"} onClick={() => setReveal((on) => !on)}>
            {reveal ? <EyeOff size={18} aria-hidden /> : <Eye size={18} aria-hidden />}
          </button>
        </div>
        <ul className="entry-checklist" id={rulesId}>
          {PASSWORD_RULES.map((rule) => {
            const met = rule.met(values.password);
            return (
              <li key={rule.id} data-met={met}>
                {met ? <Check size={13} aria-hidden /> : <CircleSmall size={13} aria-hidden />}
                <span className="sr-only">{met ? "Cumplido:" : "Falta:"}</span> {rule.label}
              </li>
            );
          })}
        </ul>
        {passwordAlert && (
          <div className="entry-error" id={`${fieldId("password")}-error`} role="alert">
            {errors.password && <p>{errors.password}</p>}
            {passwordProblems.length > 0 && <ul>{passwordProblems.map((problem) => <li key={problem}>{problem}</li>)}</ul>}
          </div>
        )}
      </div>

      <div className="entry-field">
        <label htmlFor={fieldId("confirm")}>Confirmar contraseña</label>
        <input
          id={fieldId("confirm")} name="confirm_password" type={reveal ? "text" : "password"} autoComplete="new-password"
          value={values.confirm} onChange={set("confirm")}
          aria-invalid={errors.confirm ? true : undefined} aria-describedby={describedBy("confirm")}
        />
        {errors.confirm && <p className="entry-error" id={`${fieldId("confirm")}-error`} role="alert">{errors.confirm}</p>}
      </div>

      {formError && <p className="entry-form-error" role="alert">{formError}</p>}

      <div className="entry-actions">
        <button type="submit" className="entry-primary" disabled={busy} aria-busy={busy}>
          {busy
            ? <><LoaderCircle className="entry-spinner" size={18} aria-hidden /> Creando tu cuenta…</>
            : <>Crear mi cuenta <ArrowRight size={18} aria-hidden /></>}
        </button>
        <button type="button" className="entry-switch" onClick={onSwitchToLogin} disabled={busy}>
          ¿Ya tienes cuenta? Inicia sesión
        </button>
      </div>
    </form>
  );
}
