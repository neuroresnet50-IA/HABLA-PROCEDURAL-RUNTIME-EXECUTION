from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import Flask, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - surfaced through /api/health and 503 responses.
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^[0-9+()\-\s.]{7,32}$")
AUTH_SCHEMA_LOCK = threading.Lock()
AUTH_SCHEMA_READY = False
AUTH_SESSION_HOURS = int(os.environ.get("HABLA_AUTH_SESSION_HOURS", "24"))
AUTH_PLATFORM_NAME = "Harness Engineering Platform"
AUTH_ALLOWED_PAYMENT_FIELDS = {
    "payment_token",
    "last4",
    "brand",
    "exp_month",
    "exp_year",
    "subscription_status",
}
AUTH_FORBIDDEN_PAYMENT_FIELDS = {
    "card",
    "card_number",
    "number",
    "pan",
    "cvv",
    "cvc",
    "security_code",
}


class AuthDatabaseUnavailable(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _public_user(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": str(row.get("id") or ""),
        "fullName": row.get("full_name") or "",
        "email": row.get("email") or "",
        "phone": row.get("phone") or "",
        "role": row.get("role") or "user",
        "status": row.get("status") or "active",
        "createdAt": _iso(row.get("created_at")),
        "updatedAt": _iso(row.get("updated_at")),
    }


def _public_profile(row: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "companyName": (row or {}).get("company_name") or "",
        "developerLevel": (row or {}).get("developer_level") or "initial",
        "harnessAccessLevel": (row or {}).get("harness_access_level") or "demo",
    }


def _public_payment(row: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "last4": (row or {}).get("last4") or "0000",
        "brand": (row or {}).get("brand") or "demo",
        "expMonth": (row or {}).get("exp_month"),
        "expYear": (row or {}).get("exp_year"),
        "subscriptionStatus": (row or {}).get("subscription_status") or "demo",
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _json_error(error: str, message: str, status: int):
    return jsonify({"ok": False, "error": error, "message": message}), status


def _database_configured() -> bool:
    if os.environ.get("DATABASE_URL"):
        return True
    required = ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER")
    return all(str(os.environ.get(name) or "").strip() for name in required)


def _connect_db():
    if psycopg is None:
        raise AuthDatabaseUnavailable(
            "postgres_driver_missing",
            "El driver PostgreSQL psycopg no esta instalado en este entorno.",
        )
    if not _database_configured():
        raise AuthDatabaseUnavailable(
            "postgres_not_configured",
            "PostgreSQL no esta configurado. Define DATABASE_URL o POSTGRES_HOST, POSTGRES_DB y POSTGRES_USER.",
        )

    connect_timeout = int(os.environ.get("POSTGRES_CONNECT_TIMEOUT", "4"))
    if os.environ.get("DATABASE_URL"):
        return psycopg.connect(
            os.environ["DATABASE_URL"],
            connect_timeout=connect_timeout,
            row_factory=dict_row,
        )

    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        connect_timeout=connect_timeout,
        row_factory=dict_row,
    )


def _ensure_schema(conn) -> None:
    global AUTH_SCHEMA_READY
    if AUTH_SCHEMA_READY:
        return
    with AUTH_SCHEMA_LOCK:
        if AUTH_SCHEMA_READY:
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    company_name TEXT,
                    developer_level TEXT,
                    harness_access_level TEXT,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_methods (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    payment_token TEXT,
                    last4 TEXT,
                    brand TEXT,
                    exp_month INTEGER,
                    exp_year INTEGER,
                    subscription_status TEXT DEFAULT 'demo',
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS sessions_token_hash_idx ON sessions(token_hash)")
            cur.execute("CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS user_profiles_user_id_idx ON user_profiles(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS payment_methods_user_id_idx ON payment_methods(user_id)")
        conn.commit()
        AUTH_SCHEMA_READY = True


def _open_auth_connection():
    conn = _connect_db()
    _ensure_schema(conn)
    return conn


def _normalize_email(value: Any) -> str:
    return str(value or "").strip().lower()


def _clean_text(value: Any, max_length: int) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())[:max_length]


def _validate_registration(payload: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    errors: dict[str, str] = {}
    full_name = _clean_text(payload.get("usuario_nombre") or payload.get("fullName") or payload.get("full_name"), 120)
    email = _normalize_email(payload.get("usuario_email") or payload.get("email"))
    phone = _clean_text(payload.get("usuario_telefono") or payload.get("phone"), 32)
    password = str(payload.get("usuario_password") or payload.get("password") or "")
    confirm_password = str(payload.get("usuario_confirmar_password") or payload.get("confirmPassword") or "")

    if len(full_name) < 2:
        errors["usuario_nombre"] = "El nombre es obligatorio."
    if not EMAIL_PATTERN.match(email) or len(email) > 254:
        errors["usuario_email"] = "Ingresa un email valido."
    if not PHONE_PATTERN.match(phone):
        errors["usuario_telefono"] = "Ingresa un telefono valido."
    if len(password) < 8:
        errors["usuario_password"] = "La contrasena debe tener minimo 8 caracteres."
    if password != confirm_password:
        errors["usuario_confirmar_password"] = "Las contrasenas no coinciden."

    return errors, {"full_name": full_name, "email": email, "phone": phone, "password": password}


def _validate_login(payload: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    errors: dict[str, str] = {}
    email = _normalize_email(payload.get("usuario_email") or payload.get("email"))
    password = str(payload.get("usuario_password") or payload.get("password") or "")
    if not EMAIL_PATTERN.match(email):
        errors["usuario_email"] = "Ingresa un email valido."
    if not password:
        errors["usuario_password"] = "La contrasena es obligatoria."
    return errors, {"email": email, "password": password}


def _sanitize_payment_method(raw_payment: Any) -> tuple[dict[str, Any], dict[str, str]]:
    if raw_payment is None:
        raw_payment = {}
    if not isinstance(raw_payment, dict):
        return {}, {"metodo_pago": "El metodo de pago debe ser un objeto seguro."}

    lowered_keys = {str(key).strip().lower() for key in raw_payment}
    forbidden = sorted(lowered_keys & AUTH_FORBIDDEN_PAYMENT_FIELDS)
    if forbidden:
        return {}, {"metodo_pago": "No envies numero completo de tarjeta, CVV ni datos bancarios sensibles."}

    payment = {key: raw_payment.get(key) for key in AUTH_ALLOWED_PAYMENT_FIELDS if key in raw_payment}
    payment_token = _clean_text(payment.get("payment_token") or f"demo_{secrets.token_urlsafe(18)}", 128)
    last4 = re.sub(r"\D", "", str(payment.get("last4") or "0000"))[-4:] or "0000"
    brand = _clean_text(payment.get("brand") or "demo", 32)
    subscription_status = _clean_text(payment.get("subscription_status") or "demo", 32)
    exp_month = _safe_int(payment.get("exp_month"))
    exp_year = _safe_int(payment.get("exp_year"))
    return {
        "payment_token": payment_token,
        "last4": last4,
        "brand": brand,
        "exp_month": exp_month,
        "exp_year": exp_year,
        "subscription_status": subscription_status if subscription_status in {"active", "demo", "trial"} else "demo",
    }, {}


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _token_hash(token: str, secret_key: str) -> str:
    return hmac.new(str(secret_key).encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def _extract_token() -> str:
    auth_header = str(request.headers.get("Authorization") or "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return str(request.cookies.get("habla_session") or "").strip()


def _create_session(conn, user_id: str, secret_key: str) -> dict[str, Any]:
    token = secrets.token_urlsafe(40)
    now = _utc_now()
    expires_at = now + timedelta(hours=AUTH_SESSION_HOURS)
    token_hash = _token_hash(token, secret_key)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (str(uuid.uuid4()), user_id, token_hash, expires_at, now),
        )
    return {"token": token, "expiresAt": expires_at.isoformat()}


def _load_auth_context(conn, token: str, secret_key: str) -> dict[str, Any] | None:
    if not token:
        return None
    token_hash = _token_hash(token, secret_key)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                users.id,
                users.full_name,
                users.email,
                users.phone,
                users.role,
                users.status,
                users.created_at,
                users.updated_at,
                sessions.expires_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = %s AND sessions.expires_at > %s
            """,
            (token_hash, _utc_now()),
        )
        user = cur.fetchone()
        if not user:
            return None
        cur.execute(
            """
            SELECT company_name, developer_level, harness_access_level
            FROM user_profiles
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user["id"],),
        )
        profile = cur.fetchone()
        cur.execute(
            """
            SELECT last4, brand, exp_month, exp_year, subscription_status
            FROM payment_methods
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user["id"],),
        )
        payment = cur.fetchone()
    subscription_status = (payment or {}).get("subscription_status") or "demo"
    account_active = (user.get("status") or "active") == "active"
    access_allowed = bool(account_active and subscription_status in {"active", "demo", "trial"})
    return {
        "user": _public_user(user),
        "profile": _public_profile(profile),
        "payment": _public_payment(payment),
        "access": {
            "platform": AUTH_PLATFORM_NAME,
            "allowed": access_allowed,
            "reason": "access_granted" if access_allowed else "account_or_subscription_inactive",
            "subscriptionStatus": subscription_status,
        },
        "session": {"expiresAt": _iso(user.get("expires_at"))},
    }


def _require_auth(conn, secret_key: str) -> tuple[dict[str, Any] | None, Any | None]:
    context = _load_auth_context(conn, _extract_token(), secret_key)
    if context is None:
        return None, _json_error("unauthorized", "Tu sesion expiro o no es valida. Inicia sesion nuevamente.", 401)
    return context, None


def register_auth_routes(app: Flask, *, secret_key: str) -> None:
    @app.get("/api/health")
    def auth_health():
        database_status = {
            "configured": _database_configured(),
            "driver": "psycopg" if psycopg is not None else "missing",
            "ready": False,
        }
        if database_status["configured"] and psycopg is not None:
            try:
                with _open_auth_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1 AS ok")
                        database_status["ready"] = bool(cur.fetchone())
            except Exception as error:
                database_status["error"] = str(error)
        return jsonify({"ok": True, "service": "HABLA Observer IA", "auth": {"postgres": database_status}})

    @app.post("/api/auth/register")
    def auth_register():
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return _json_error("invalid_payload", "El cuerpo debe ser JSON.", 400)
        errors, clean_user = _validate_registration(payload)
        payment, payment_errors = _sanitize_payment_method(payload.get("metodo_pago") or payload.get("paymentMethod"))
        errors.update(payment_errors)
        if errors:
            return jsonify({"ok": False, "error": "validation_failed", "fields": errors}), 400

        now = _utc_now()
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(clean_user["password"], method="pbkdf2:sha256:260000")
        try:
            with _open_auth_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO users (id, full_name, email, phone, password_hash, role, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, 'user', 'active', %s, %s)
                        """,
                        (
                            user_id,
                            clean_user["full_name"],
                            clean_user["email"],
                            clean_user["phone"],
                            password_hash,
                            now,
                            now,
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO user_profiles (
                            id, user_id, company_name, developer_level, harness_access_level, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            user_id,
                            _clean_text(payload.get("companyName"), 120),
                            _clean_text(payload.get("developerLevel") or "initial", 64),
                            "demo",
                            now,
                            now,
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO payment_methods (
                            id, user_id, payment_token, last4, brand, exp_month, exp_year, subscription_status, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            user_id,
                            payment["payment_token"],
                            payment["last4"],
                            payment["brand"],
                            payment["exp_month"],
                            payment["exp_year"],
                            payment["subscription_status"],
                            now,
                            now,
                        ),
                    )
                    session = _create_session(conn, user_id, secret_key)
                conn.commit()
                context = _load_auth_context(conn, session["token"], secret_key)
        except AuthDatabaseUnavailable as error:
            return _json_error(error.code, str(error), 503)
        except Exception as error:
            if "duplicate" in str(error).lower() or "unique" in str(error).lower():
                return _json_error("email_already_registered", "Ese email ya esta registrado.", 409)
            return _json_error("registration_failed", "No fue posible crear la cuenta en este momento.", 500)

        return jsonify({"ok": True, "token": session["token"], "session": session, **(context or {})}), 201

    @app.post("/api/auth/login")
    def auth_login():
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return _json_error("invalid_payload", "El cuerpo debe ser JSON.", 400)
        errors, clean_login = _validate_login(payload)
        if errors:
            return jsonify({"ok": False, "error": "validation_failed", "fields": errors}), 400

        try:
            with _open_auth_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, password_hash, status FROM users WHERE email = %s",
                        (clean_login["email"],),
                    )
                    user = cur.fetchone()
                    if not user or not check_password_hash(user["password_hash"], clean_login["password"]):
                        return _json_error("invalid_credentials", "Credenciales invalidas.", 401)
                    if (user.get("status") or "active") != "active":
                        return _json_error("account_inactive", "La cuenta no esta activa.", 403)
                    session = _create_session(conn, user["id"], secret_key)
                conn.commit()
                context = _load_auth_context(conn, session["token"], secret_key)
        except AuthDatabaseUnavailable as error:
            return _json_error(error.code, str(error), 503)
        except Exception:
            return _json_error("login_failed", "No fue posible iniciar sesion en este momento.", 500)

        return jsonify({"ok": True, "token": session["token"], "session": session, **(context or {})})

    @app.post("/api/auth/logout")
    def auth_logout():
        token = _extract_token()
        if not token:
            return jsonify({"ok": True})
        try:
            with _open_auth_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM sessions WHERE token_hash = %s", (_token_hash(token, secret_key),))
                conn.commit()
        except AuthDatabaseUnavailable as error:
            return _json_error(error.code, str(error), 503)
        except Exception:
            return _json_error("logout_failed", "No fue posible cerrar la sesion.", 500)
        return jsonify({"ok": True})

    @app.get("/api/auth/me")
    def auth_me():
        token = _extract_token()
        if not token:
            return _json_error("unauthorized", "Tu sesion expiro o no es valida. Inicia sesion nuevamente.", 401)
        try:
            with _open_auth_connection() as conn:
                context = _load_auth_context(conn, token, secret_key)
                if context is None:
                    return _json_error("unauthorized", "Tu sesion expiro o no es valida. Inicia sesion nuevamente.", 401)
        except AuthDatabaseUnavailable as error:
            return _json_error(error.code, str(error), 503)
        except Exception:
            return _json_error("session_check_failed", "No fue posible validar la sesion.", 500)
        return jsonify({"ok": True, "authenticated": True, **(context or {})})

    @app.get("/api/user/profile")
    def user_profile():
        token = _extract_token()
        if not token:
            return _json_error("unauthorized", "Tu sesion expiro o no es valida. Inicia sesion nuevamente.", 401)
        try:
            with _open_auth_connection() as conn:
                context = _load_auth_context(conn, token, secret_key)
                if context is None:
                    return _json_error("unauthorized", "Tu sesion expiro o no es valida. Inicia sesion nuevamente.", 401)
        except AuthDatabaseUnavailable as error:
            return _json_error(error.code, str(error), 503)
        except Exception:
            return _json_error("profile_failed", "No fue posible cargar el perfil.", 500)
        return jsonify({"ok": True, **(context or {})})

    @app.post("/api/payment/demo-token")
    def payment_demo_token():
        token = _extract_token()
        if not token:
            return _json_error("unauthorized", "Tu sesion expiro o no es valida. Inicia sesion nuevamente.", 401)
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return _json_error("invalid_payload", "El cuerpo debe ser JSON.", 400)
        payment, payment_errors = _sanitize_payment_method(payload.get("metodo_pago") or payload)
        if payment_errors:
            return jsonify({"ok": False, "error": "validation_failed", "fields": payment_errors}), 400

        now = _utc_now()
        try:
            with _open_auth_connection() as conn:
                context = _load_auth_context(conn, token, secret_key)
                if context is None:
                    return _json_error("unauthorized", "Tu sesion expiro o no es valida. Inicia sesion nuevamente.", 401)
                user_id = context["user"]["id"]
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO payment_methods (
                            id, user_id, payment_token, last4, brand, exp_month, exp_year, subscription_status, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            user_id,
                            payment["payment_token"],
                            payment["last4"],
                            payment["brand"],
                            payment["exp_month"],
                            payment["exp_year"],
                            payment["subscription_status"],
                            now,
                            now,
                        ),
                    )
                conn.commit()
                updated_context = _load_auth_context(conn, token, secret_key)
        except AuthDatabaseUnavailable as error:
            return _json_error(error.code, str(error), 503)
        except Exception:
            return _json_error("payment_demo_failed", "No fue posible activar el modo demo.", 500)

        return jsonify({"ok": True, **(updated_context or {})})
