import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import BottomNav from "./components/BottomNav";
import ErrorBoundary from "./components/ErrorBoundary";
import Asistente from "./screens/Asistente";
import CobroEfectivo from "./screens/CobroEfectivo";
import Compras from "./screens/Compras";
import Cuenta from "./screens/Cuenta";
import Educacion from "./screens/Educacion";
import Inventario from "./screens/Inventario";
import Libros from "./screens/Libros";
import Mas from "./screens/Mas";
import Pagos from "./screens/Pagos";
import Pay from "./screens/Pay";
import Resumen from "./screens/Resumen";
import Retiros from "./screens/Retiros";
import Transferencias from "./screens/Transferencias";
import Vender from "./screens/Vender";
import PhoneFrame from "./onboarding/PhoneFrame.jsx";
import Onboarding from "./onboarding/OnboardingFlow.jsx";
import Welcome, { DEMO_BUSINESSES } from "./onboarding/Welcome";
import Landing from "./landing/Landing";
import { demoSession } from "./api/finance";
import type { DemoBusinessKey } from "./api/types";
import { getProfile, type BusinessProfile as RemoteProfile } from "./auth/api";
import { clearSession, readSession, saveSession, sessionFromAuth, type Session } from "./auth/session";
import { BusinessProvider, type LocalProfile } from "./business/BusinessContext";

type BusinessProfile = LocalProfile;

/** El perfil local (nombre para el saludo, categoría para la educación) también sobrevive al refresh. */
const PROFILE_KEY = "c1b.profile";

function readProfile(): BusinessProfile | null {
  try {
    const raw = window.sessionStorage.getItem(PROFILE_KEY);
    return raw ? (JSON.parse(raw) as BusinessProfile) : null;
  } catch {
    return null;
  }
}

function saveProfile(profile: BusinessProfile | null) {
  try {
    if (profile) window.sessionStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
    else window.sessionStorage.removeItem(PROFILE_KEY);
  } catch {
    // sin storage la app sigue; solo se pierde al refrescar
  }
}

/** Nombre y apellidos a partir del nombre completo de la cuenta. */
function splitName(fullName: string): { name: string; lastName: string } {
  const [name, ...rest] = fullName.trim().split(" ");
  return { name, lastName: rest.join(" ") };
}

/** El perfil local que usan las pantallas, a partir del guardado en el backend. */
function localProfileFrom(remote: RemoteProfile, fullName: string): BusinessProfile {
  return { category: remote.category, answers: remote.answers ?? {}, ...splitName(fullName) };
}

function MainApp({ profile }: { profile: BusinessProfile | null }) {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    // w-full y NO `mx-auto max-w-md`: el ancho ya lo fija el mockup de celular
    // (.phone-frame__screen). Además ese contenedor es un flex column, y un
    // margen lateral `auto` en un flex item cancela el stretch del eje cruzado
    // — el shell se encogía a fit-content y quedaba centrado con huecos a los
    // lados, de ancho distinto en cada pantalla según su contenido.
    // El shell no scrollea; el scroll vive dentro de cada pantalla
    // (ver Screen.tsx), así la barra inferior nunca se mueve.
    <div className="relative flex h-full w-full flex-col overflow-hidden bg-surface">
      {/* Si una pantalla truena, el error se queda en ella: la barra inferior
          sigue ahí y cambiar de ruta (resetKey) vuelve a intentar. */}
      <ErrorBoundary resetKey={location.pathname} actionLabel="Ir a Cuenta" onAction={() => navigate("/")}>
        {/* mode="wait" evita que dos pantallas se solapen durante la transición.
            La key es la ruta: sin ella AnimatePresence no detecta el cambio. */}
        <AnimatePresence mode="wait" initial={false}>
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<Cuenta profile={profile} />} />
            <Route path="/vender" element={<Vender />} />
            <Route path="/inventario" element={<Inventario />} />
            <Route path="/compras" element={<Compras />} />
            {/* El botón central abre la conversación; los datos viven en /resumen
                y los indicadores en /libros. /asistente se conserva como alias. */}
            <Route path="/analisis" element={<Asistente />} />
            <Route path="/asistente" element={<Navigate to="/analisis" replace />} />
            <Route path="/resumen" element={<Resumen />} />
            <Route path="/libros" element={<Libros />} />
            <Route path="/retiros" element={<Retiros />} />
            <Route path="/transferencias" element={<Transferencias />} />
            <Route path="/cobro-efectivo" element={<CobroEfectivo />} />
            <Route path="/pagos" element={<Pagos />} />
            <Route path="/educacion" element={<Educacion profile={profile} />} />
            <Route path="/mas" element={<Mas />} />
            <Route path="*" element={<Cuenta profile={profile} />} />
          </Routes>
        </AnimatePresence>
      </ErrorBoundary>

      <BottomNav />
    </div>
  );
}

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  // landing: logo animado + "Empezar"; de ahí a la bienvenida y el resto del flujo.
  const [stage, setStage] = useState<"landing" | "welcome" | "survey" | "account">("landing");
  const [surveyStarted, setSurveyStarted] = useState(false);
  // A dónde vuelve la encuesta al salir: a la bienvenida (cuenta nueva) o a
  // la app ("Más → Actualizar mi perfil").
  const [surveyOrigin, setSurveyOrigin] = useState<"welcome" | "account">("welcome");
  const [profile, setProfileState] = useState<BusinessProfile | null>(null);
  // La sesión vive aquí y no en un contexto propio: la encuesta la necesita
  // para el POST del perfil y el BusinessProvider para la API financiera.
  const [session, setSession] = useState<Session | null>(null);

  const setProfile = (next: BusinessProfile | null) => {
    setProfileState(next);
    saveProfile(next);
  };

  // Se rehidrata en el primer render del cliente (no en el estado inicial)
  // porque leer sessionStorage puede lanzar y useState no tiene dónde
  // recuperarse. readSession() ya descarta un token caducado. Con sesión viva
  // (un refresh a media demo) se entra directo a la app.
  useEffect(() => {
    const live = readSession();
    setSession(live);
    if (live) {
      setProfileState(readProfile());
      setStage("account");
    }
  }, []);

  const openSurvey = (origin: "welcome" | "account") => {
    setSurveyOrigin(origin);
    setSurveyStarted(true);
    setStage("survey");
  };

  // Una sola regla después de CUALQUIER autenticación (registro o login):
  // si la cuenta ya tiene perfil guardado, a la app; si no, a la encuesta.
  // Una cuenta nueva no tiene perfil, así que el registro sigue llevando a la
  // encuesta; quien cerró la pestaña a media encuesta también la vuelve a ver.
  // Si el backend falla al leer el perfil, se entra a la app con perfil vacío
  // (todas las pantallas lo aguantan) en vez de atrapar al usuario en la
  // encuesta: puede rehacerla desde "Más".
  const authenticated = async (next: Session) => {
    saveSession(next);
    setSession(next);
    const result = await getProfile(next.user.user_id, next.token);
    if (result.ok) {
      if (result.data) {
        setProfile(localProfileFrom(result.data, next.user.full_name));
        setStage("account");
      } else {
        openSurvey("welcome");
      }
      return;
    }
    console.warn("No se pudo leer el perfil del negocio; se entra sin perfil:", result.message);
    setProfile(null);
    setStage("account");
  };

  // "Explorar la demo": entra con el negocio de ejemplo elegido, ya
  // sembrado. Si el backend no responde, entra igual sin sesión (las
  // pantallas lo explican).
  const explore = async (business: DemoBusinessKey) => {
    const res = await demoSession(business);
    const demo = DEMO_BUSINESSES[business];
    if (res.ok) {
      const next = sessionFromAuth(res.data);
      saveSession(next);
      setSession(next);
      setProfile({ category: demo.category, answers: demo.answers, ...splitName(res.data.user.full_name) });
    }
    setStage("account");
  };

  // "Más → Cerrar sesión": no queda nada de la cuenta en el dispositivo.
  const logout = useCallback(() => {
    clearSession();
    saveProfile(null);
    setProfileState(null);
    setSession(null);
    setSurveyStarted(false);
    setStage("welcome");
    navigate("/", { replace: true });
  }, [navigate]);

  const updateProfile = useCallback(() => openSurvey("account"), []);

  // La página pública de pago (QR) vive fuera del flujo de sesión: la abre
  // el cliente, sin cuenta, dentro del mismo mockup para que se vea como app.
  if (location.pathname.startsWith("/pay/")) {
    return (
      <PhoneFrame>
        <Routes>
          <Route path="/pay/:token" element={<Pay />} />
        </Routes>
      </PhoneFrame>
    );
  }

  // Un solo mockup de celular para toda la sesión: landing, bienvenida, encuesta y app
  // principal viven dentro del mismo PhoneFrame, así el marco no se desmonta
  // ni cambia de tamaño al pasar de una etapa a otra.
  return (
    <PhoneFrame>
      {stage === "account" ? (
        <BusinessProvider session={session} profile={profile} onLogout={logout} onUpdateProfile={updateProfile}>
          <MainApp profile={profile} />
        </BusinessProvider>
      ) : <>
        {stage === "landing" && <Landing onStart={() => setStage("welcome")} />}
        {stage === "welcome" && <Welcome
          onAuthenticated={authenticated}
          onExplore={(business) => { void explore(business); }}
        />}
        {/* La encuesta se oculta (no se desmonta) para conservar las respuestas
            si el usuario vuelve a la bienvenida. */}
        {surveyStarted && <div className="phone-stage" hidden={stage !== "survey"}>
          <Onboarding
            // El perfil se guarda bajo el user_id de la cuenta y el backend
            // exige que el token sea de ese mismo dueño (403 si no coincide).
            ownerId={session?.user.user_id}
            token={session?.token ?? ""}
            active={stage === "survey"}
            onExit={() => setStage(surveyOrigin)}
            onComplete={(completedProfile?: BusinessProfile) => {
              setProfile(completedProfile ?? null);
              setStage("account");
            }}
          />
        </div>}
      </>}
    </PhoneFrame>
  );
}
