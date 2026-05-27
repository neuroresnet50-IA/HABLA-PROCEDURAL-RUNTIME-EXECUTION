import { useEffect, useMemo, useState } from "react";

const AUTH_TOKEN_STORAGE_KEY = "hablaAuthToken";
const AUTH_INTRO_STORAGE_KEY = "hablaAuthIntroCompleted";
const DEFAULT_LOADING_MS = 1200;
const AUTH_REQUEST_TIMEOUT_MS = 45000;
const AUTH_RETRY_DELAY_MS = 600;

function storageGet(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return "";
  }
}

function storageSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Local storage can be blocked; the current session still works in memory.
  }
}

function storageRemove(key) {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Ignore storage failures.
  }
}

function buildApiUrl(apiBaseUrl, path) {
  const base = String(apiBaseUrl || "").replace(/\/+$/, "");
  const normalizedPath = String(path || "").startsWith("/") ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

function normalizeFieldErrors(fields) {
  return fields && typeof fields === "object" ? fields : {};
}

function isAbortLike(error) {
  const rawMessage = String(error?.message || "");
  return error?.name === "AbortError" || rawMessage === "auth_request_timeout" || rawMessage.includes("aborted");
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function fetchWithAuthTimeout(requestUrl, options, timeoutMs) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(new Error("auth_request_timeout")), timeoutMs);
  try {
    return await fetch(requestUrl, { ...options, signal: controller.signal });
  } catch (error) {
    if (isAbortLike(error)) {
      const timeoutSeconds = Math.round(timeoutMs / 1000);
      const timeoutError = new Error(`Tiempo de espera agotado al contactar autenticacion en ${requestUrl} despues de ${timeoutSeconds}s.`);
      timeoutError.code = "auth_request_timeout";
      timeoutError.cause = error;
      throw timeoutError;
    }
    const networkError = new Error(`No fue posible contactar autenticacion en ${requestUrl}.`);
    networkError.code = "auth_network_error";
    networkError.cause = error;
    throw networkError;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function authFetch(apiBaseUrl, path, { token = "", timeoutMs = AUTH_REQUEST_TIMEOUT_MS, retryOnTimeout = false, ...options } = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const requestUrl = buildApiUrl(apiBaseUrl, path);
  const attempts = retryOnTimeout ? 2 : 1;
  let response;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      response = await fetchWithAuthTimeout(requestUrl, { ...options, headers }, timeoutMs);
      break;
    } catch (error) {
      if (error?.code === "auth_request_timeout" && attempt + 1 < attempts) {
        await wait(AUTH_RETRY_DELAY_MS);
        continue;
      }
      throw error;
    }
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload?.ok === false) {
    const error = new Error(payload?.message || "Servicio temporalmente no disponible.");
    error.payload = payload;
    error.status = response.status;
    throw error;
  }
  return payload;
}

function initialRegisterForm() {
  return {
    usuario_nombre: "",
    usuario_email: "",
    usuario_telefono: "",
    usuario_password: "",
    usuario_confirmar_password: "",
  };
}

function initialLoginForm() {
  return {
    usuario_email: "",
    usuario_password: "",
  };
}

function validateRegisterForm(form) {
  const errors = {};
  if (form.usuario_nombre.trim().length < 2) errors.usuario_nombre = "Nombre requerido.";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.usuario_email.trim())) errors.usuario_email = "Email invalido.";
  if (!/^[0-9+()\-\s.]{7,32}$/.test(form.usuario_telefono.trim())) errors.usuario_telefono = "Telefono invalido.";
  if (form.usuario_password.length < 8) errors.usuario_password = "Minimo 8 caracteres.";
  if (form.usuario_password !== form.usuario_confirmar_password) errors.usuario_confirmar_password = "No coincide.";
  return errors;
}

function validateLoginForm(form) {
  const errors = {};
  const identifier = form.usuario_email.trim();
  const looksLikeEmail = identifier.includes("@");
  const validIdentifier = /^[A-Za-z0-9_.@+-]{3,254}$/.test(identifier);
  const validEmail = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(identifier);
  if (!validIdentifier || (looksLikeEmail && !validEmail)) errors.usuario_email = "Usuario o email invalido.";
  if (!form.usuario_password) errors.usuario_password = "Contrasena requerida.";
  return errors;
}

export default function WelcomeAuthGate({ apiBaseUrl, logoSrc }) {
  const loadingDurationMs = useMemo(() => {
    const rawValue = Number(import.meta.env.VITE_HABLA_AUTH_LOADING_MS || DEFAULT_LOADING_MS);
    return Number.isFinite(rawValue) && rawValue >= 0 ? rawValue : DEFAULT_LOADING_MS;
  }, []);
  const [phase, setPhase] = useState("checking");
  const [mode, setMode] = useState("register");
  const [progress, setProgress] = useState(0);
  const [sessionToken, setSessionToken] = useState("");
  const [profile, setProfile] = useState(null);
  const [registerForm, setRegisterForm] = useState(initialRegisterForm);
  const [loginForm, setLoginForm] = useState(initialLoginForm);
  const [fieldErrors, setFieldErrors] = useState({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const existingToken = storageGet(AUTH_TOKEN_STORAGE_KEY);
    async function checkAuthService() {
      try {
        const payload = await authFetch(apiBaseUrl, "/api/health");
        const postgres = payload?.auth?.postgres || {};
        if (!postgres.configured || postgres.driver === "missing" || postgres.ready === false) {
          setMessage("PostgreSQL aun no esta configurado para autenticacion. Puedes entrar en modo local temporal.");
          setPhase("unavailable");
          return false;
        }
        return true;
      } catch (error) {
        setMessage(error.message || "Autenticacion temporalmente no disponible. Puedes entrar en modo local.");
        setPhase("unavailable");
        return false;
      }
    }

    async function checkExistingSession() {
      const authServiceReady = await checkAuthService();
      if (cancelled || !authServiceReady) return;
      if (!existingToken) {
        if (storageGet(AUTH_INTRO_STORAGE_KEY) === "1") {
          setPhase("setup");
        } else {
          setPhase("loading");
        }
        return;
      }
      try {
        const payload = await authFetch(apiBaseUrl, "/api/auth/me", { token: existingToken });
        if (cancelled) return;
        setSessionToken(existingToken);
        setProfile(payload.user || null);
        setPhase("authenticated");
      } catch {
        storageRemove(AUTH_TOKEN_STORAGE_KEY);
        if (cancelled) return;
        setSessionToken("");
        setProfile(null);
        setPhase(storageGet(AUTH_INTRO_STORAGE_KEY) === "1" ? "setup" : "loading");
      }
    }
    checkExistingSession();
    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl]);

  useEffect(() => {
    if (phase !== "loading") return undefined;
    if (loadingDurationMs === 0) {
      storageSet(AUTH_INTRO_STORAGE_KEY, "1");
      setProgress(100);
      setPhase("setup");
      return undefined;
    }
    const startedAt = Date.now();
    const intervalId = window.setInterval(() => {
      const elapsed = Date.now() - startedAt;
      const nextProgress = Math.min(100, Math.round((elapsed / loadingDurationMs) * 100));
      setProgress(nextProgress);
      if (elapsed >= loadingDurationMs) {
        window.clearInterval(intervalId);
        storageSet(AUTH_INTRO_STORAGE_KEY, "1");
        setPhase("setup");
      }
    }, 250);
    return () => window.clearInterval(intervalId);
  }, [loadingDurationMs, phase]);

  function handleRegisterChange(event) {
    const { name, value } = event.target;
    setRegisterForm((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: "" }));
  }

  function handleLoginChange(event) {
    const { name, value } = event.target;
    setLoginForm((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: "" }));
  }

  function completeAuth(payload) {
    if (payload.token) {
      storageSet(AUTH_TOKEN_STORAGE_KEY, payload.token);
      setSessionToken(payload.token);
    }
    setProfile(payload.user || null);
    setMessage("");
    setFieldErrors({});
    setPhase("authenticated");
  }

  async function submitRegister(event) {
    event.preventDefault();
    const clientErrors = validateRegisterForm(registerForm);
    setFieldErrors(clientErrors);
    setMessage("");
    if (Object.keys(clientErrors).length) return;

    setBusy(true);
    try {
      const payload = await authFetch(apiBaseUrl, "/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          ...registerForm,
          metodo_pago: {
            subscription_status: "demo",
            brand: "demo",
            last4: "0000",
          },
        }),
      });
      completeAuth(payload);
    } catch (error) {
      setFieldErrors(normalizeFieldErrors(error.payload?.fields));
      setMessage(error.message || "No fue posible registrar la cuenta.");
    } finally {
      setBusy(false);
    }
  }

  async function submitLogin(event) {
    event.preventDefault();
    const clientErrors = validateLoginForm(loginForm);
    setFieldErrors(clientErrors);
    setMessage("");
    if (Object.keys(clientErrors).length) return;

    setBusy(true);
    try {
      const payload = await authFetch(apiBaseUrl, "/api/auth/login", {
        method: "POST",
        body: JSON.stringify(loginForm),
        timeoutMs: 60000,
        retryOnTimeout: true,
      });
      completeAuth(payload);
    } catch (error) {
      setFieldErrors(normalizeFieldErrors(error.payload?.fields));
      setMessage(error.message || "Credenciales invalidas.");
    } finally {
      setBusy(false);
    }
  }

  if (phase === "authenticated") {
    return null;
  }

  if (phase === "checking") {
    return null;
  }

  if (phase === "loading") {
    return (
      <section className="welcome-auth-gate is-loading" aria-live="polite">
        <div className="welcome-auth-loading">
          <div className="welcome-auth-logo-ring" aria-hidden="true">
            <img src={logoSrc} alt="" />
          </div>
          <div className="welcome-auth-loading-copy">
            <p>HABLA Observer IA</p>
            <h2>Cargando Harness Engineering Platform...</h2>
            <span>{progress}%</span>
          </div>
          <div className="welcome-auth-progress" aria-label="Progreso de carga">
            <i style={{ width: `${progress}%` }} />
          </div>
        </div>
      </section>
    );
  }

  if (phase === "unavailable") {
    return (
      <section className="welcome-auth-gate is-unavailable" aria-live="polite">
        <div className="welcome-auth-top-title" aria-hidden="true">HABLA Observer IA</div>
        <div className="welcome-auth-corner-orbit" aria-hidden="true"><span /><span /></div>
        <div className="welcome-auth-panel is-unavailable" role="dialog" aria-modal="true" aria-label="Autenticacion no disponible">
          <div className="welcome-auth-visual">
            <div className="welcome-auth-logo-ring is-compact" aria-hidden="true">
              <img src={logoSrc} alt="" />
            </div>
            <div>
              <p className="welcome-auth-eyebrow">HABLA Observer IA</p>
              <h2>Acceso local temporal</h2>
              <span>PostgreSQL pendiente de configuracion</span>
            </div>
          </div>
          <div className="welcome-auth-content">
            <p className="welcome-auth-message" role="alert">{message || "Servicio temporalmente no disponible."}</p>
            <div className="welcome-auth-demo-access">
              <strong>La aplicacion principal no fue bloqueada</strong>
              <span>El login real se activara cuando PostgreSQL quede configurado y disponible.</span>
            </div>
            <button type="button" className="welcome-auth-submit" onClick={() => setPhase("authenticated")}>
              Entrar al sistema local
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="welcome-auth-gate is-setup" aria-live="polite">
      <div className="welcome-auth-top-title" aria-hidden="true">HABLA Observer IA</div>
      <div className="welcome-auth-corner-orbit" aria-hidden="true"><span /><span /></div>
      <div className="welcome-auth-panel" role="dialog" aria-modal="true" aria-label="Acceso HABLA Observer IA">
        <div className="welcome-auth-visual">
          <div className="welcome-auth-logo-ring is-compact" aria-hidden="true">
            <img src={logoSrc} alt="" />
          </div>
          <div>
            <p className="welcome-auth-eyebrow">HABLA Observer IA</p>
            <h2>Acceso inicial</h2>
            <span>Tu descubrimiento, tu destino</span>
          </div>
        </div>

        <div className="welcome-auth-content">
          <div className="welcome-auth-tabs" role="tablist" aria-label="Modo de acceso">
            <button type="button" className={mode === "register" ? "active" : ""} onClick={() => { setMode("register"); setMessage(""); setFieldErrors({}); }}>
              Crear cuenta
            </button>
            <button type="button" className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setMessage(""); setFieldErrors({}); }}>
              Iniciar sesion
            </button>
          </div>

          {message ? <p className="welcome-auth-message" role="alert">{message}</p> : null}

          {mode === "register" ? (
            <form className="welcome-auth-form" onSubmit={submitRegister}>
              <label>
                <span>Nombre completo</span>
                <input name="usuario_nombre" value={registerForm.usuario_nombre} onChange={handleRegisterChange} autoComplete="name" required />
                {fieldErrors.usuario_nombre ? <small>{fieldErrors.usuario_nombre}</small> : null}
              </label>
              <label>
                <span>Email</span>
                <input name="usuario_email" type="email" value={registerForm.usuario_email} onChange={handleRegisterChange} autoComplete="email" required />
                {fieldErrors.usuario_email ? <small>{fieldErrors.usuario_email}</small> : null}
              </label>
              <label>
                <span>Telefono</span>
                <input name="usuario_telefono" value={registerForm.usuario_telefono} onChange={handleRegisterChange} autoComplete="tel" required />
                {fieldErrors.usuario_telefono ? <small>{fieldErrors.usuario_telefono}</small> : null}
              </label>
              <label>
                <span>Contrasena</span>
                <input name="usuario_password" type="password" value={registerForm.usuario_password} onChange={handleRegisterChange} autoComplete="new-password" required />
                {fieldErrors.usuario_password ? <small>{fieldErrors.usuario_password}</small> : null}
              </label>
              <label>
                <span>Confirmar contrasena</span>
                <input name="usuario_confirmar_password" type="password" value={registerForm.usuario_confirmar_password} onChange={handleRegisterChange} autoComplete="new-password" required />
                {fieldErrors.usuario_confirmar_password ? <small>{fieldErrors.usuario_confirmar_password}</small> : null}
              </label>
              <div className="welcome-auth-demo-access">
                <strong>Modo demo seguro</strong>
                <span>No solicita tarjeta, CVV ni datos bancarios reales.</span>
              </div>
              <button type="submit" className="welcome-auth-submit" disabled={busy}>
                {busy ? "Creando acceso..." : "Entrar a Harness Engineering"}
              </button>
            </form>
          ) : (
            <form className="welcome-auth-form" onSubmit={submitLogin}>
              <label>
                <span>Usuario o email</span>
                <input name="usuario_email" type="text" value={loginForm.usuario_email} onChange={handleLoginChange} autoComplete="username" required />
                {fieldErrors.usuario_email ? <small>{fieldErrors.usuario_email}</small> : null}
              </label>
              <label>
                <span>Contrasena</span>
                <input name="usuario_password" type="password" value={loginForm.usuario_password} onChange={handleLoginChange} autoComplete="current-password" required />
                {fieldErrors.usuario_password ? <small>{fieldErrors.usuario_password}</small> : null}
              </label>
              <div className="welcome-auth-demo-access">
                <strong>Acceso de validacion</strong>
                <span>Usuario: admin / Contrasena: admin</span>
              </div>
              <button type="submit" className="welcome-auth-submit" disabled={busy}>
                {busy ? "Validando..." : "Iniciar sesion"}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
