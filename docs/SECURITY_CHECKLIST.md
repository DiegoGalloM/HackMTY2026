# Checklist de seguridad de la API (OWASP API Security Top 10, 2023)

Pasada explícita de la Fase 7 de [`ROADMAP_PULIDO.md`](./ROADMAP_PULIDO.md),
hecha el 2026-09-15 en modo sqlite/mock. Cada punto dice cómo se cubre y **qué
test lo vigila en CI**: si alguien rompe una de estas garantías, el pipeline
falla.

El alcance es el de un demo público con dinero simulado: la meta es que no haya
huecos obvios para quien revise el repo o curiosee la API, no una auditoría de
producto financiero real.

Leyenda: ✅ cubierto y probado · 🟡 decisión consciente o limitación conocida ·
⏳ pendiente (fuera del alcance del modo mock).

## Resumen

| # | Riesgo | Estado |
|---|---|---|
| API1 | Broken Object Level Authorization | ✅ |
| API2 | Broken Authentication | ✅ |
| API3 | Broken Object Property Level Authorization | ✅ |
| API4 | Unrestricted Resource Consumption | ✅ (con 🟡) |
| API5 | Broken Function Level Authorization | ✅ |
| API6 | Unrestricted Access to Sensitive Business Flows | ✅ |
| API7 | Server Side Request Forgery | ✅ |
| API8 | Security Misconfiguration (incluye inyección y stack traces) | ✅ (con 🟡) |
| API9 | Improper Inventory Management | ✅ corregido en esta pasada |
| API10 | Unsafe Consumption of APIs | ✅ |

Los tres puntos que pidió el roadmap explícitamente:

- **Inyección:** API8.
- **Límites de tamaño de payload:** API4.
- **Stack traces en errores 500:** API8.

---

## API1 · Broken Object Level Authorization ✅

**Riesgo:** leer o escribir los datos de otro negocio cambiando un id.

**Cómo se cubre:**

- Toda ruta bajo `/business/{owner_id}` y `/business-profile/{owner_id}` exige
  que el token sea del dueño (`require_owner`). La exigencia está en el router,
  no endpoint por endpoint.
- Los servicios nacen atados a un `Repo` del negocio, que rechaza consultas sin
  `business_id`.
- El asistente no tiene ninguna herramienta que reciba otro negocio.

**Tests:**

- `test_finance_api.py::test_finance_routes_are_tenant_guarded`
- `test_owasp_api.py::test_api1_another_owner_cannot_write_into_my_business`
- `test_auth.py::test_profile_endpoints_reject_another_users_owner_id`
- `test_security_hardening.py::test_owner_id_cannot_be_supplied_as_a_query_parameter`
- `test_assistant.py::test_assistant_is_scoped_to_its_business`
- El caso dorado `pan-inyeccion-otro-negocio`

## API2 · Broken Authentication ✅

**Cómo se cubre:**

- JWT HMAC con lista blanca de algoritmos y secreto de 32 caracteres o más.
  Con `ENVIRONMENT=production`, `JWT_SECRET` es obligatorio.
- `exp` es obligatorio.
- bcrypt fuera del event loop.
- Contraseñas comunes rechazadas.
- Login con rate limit.
- Usuario inexistente y contraseña mala son indistinguibles.

**Tests:**

- `test_owasp_api.py::test_api2_forged_tokens_are_rejected`: `alg: none`,
  payload cambiado, firma alterada, sin `exp`.
- `test_auth.py`: token caducado, firmado con otro secreto, usuario borrado,
  header mal formado.
- `test_security_hardening.py`: política de contraseñas y algoritmo.
- `test_demo_hardening.py`: `JWT_SECRET` en producción y rate limit del login.

## API3 · Broken Object Property Level Authorization ✅

**Riesgo:** mandar campos que el cliente no debería controlar, o recibir campos
que no debería ver.

**Cómo se cubre:**

- Los modelos de entrada de Pydantic ignoran campos extra.
- Las respuestas usan vistas públicas: `UserPublic` y `_public_view` del pago.
- El audio de la encuesta nunca vuelve a salir por la API.

**Tests:**

- `test_owasp_api.py::test_api3_register_ignores_fields_the_client_must_not_set`:
  `user_id`, `password_hash` e `is_admin` inyectados.
- `test_owasp_api.py::test_api3_the_customer_cannot_change_status_or_amount_of_an_order`
- `test_auth.py::test_register_response_never_leaks_password`
- `test_demo_hardening.py::test_get_profile_never_returns_legacy_audio_left_in_the_row`

## API4 · Unrestricted Resource Consumption ✅ 🟡

**Cómo se cubre:**

- **Tope global al cuerpo:** 3 MB (`MAX_REQUEST_BODY_BYTES`) y 413 si se pasa,
  con o sin `Content-Length`. Agregado en esta pasada.
- **Límites por campo:** perfil, respuestas, audio, pregunta del asistente (500)
  y líneas de una orden (50).
- **Listados acotados:** `limit` de órdenes ≤ 500.
- **Rate limit por IP** en todas las rutas públicas con trabajo real, y caché de
  30 s en `/health/ready`.

**Tests:**

- `test_owasp_api.py::test_api4_*`: cuerpo grande, cuerpo por partes, cuerpo
  normal, `limit` y largo de la pregunta.
- `test_security_hardening.py::test_profile_fields_are_bounded`
- `test_demo_hardening.py`: rate limiting.

**🟡 Decisiones:**

- `LoginRequest` no tiene longitudes a propósito, para que un usuario con forma
  inválida responda 401 y no 422. El tope global del cuerpo cubre el abuso por
  tamaño.
- El rate limit vive en memoria y es por proceso: con varios workers se
  multiplica.

## API5 · Broken Function Level Authorization ✅

**Cómo se cubre:** una lista explícita de rutas públicas. Todas las demás
exigen token.

**Test:** `test_owasp_api.py::test_api5_every_non_public_route_requires_a_token`
recorre todas las rutas de la app, así que **una ruta nueva sin autenticación
rompe CI**.

## API6 · Unrestricted Access to Sensitive Business Flows ✅

**Cómo se cubre:**

- El pago por QR es idempotente: pagar dos veces no duplica asientos ni mueve
  inventario de nuevo.
- Sólo un evento de pago `SUCCEEDED` cambia libros e inventario.
- `/demo/session`, que siembra un negocio, tiene rate limit.

**Tests:**

- `test_finance_api.py::test_full_qr_sale_flow_reaches_books_analytics_and_assistant`
  (segundo pago)
- `test_demo_hardening.py::test_every_public_route_has_a_rate_limit`

## API7 · Server Side Request Forgery ✅

**Cómo se cubre:** el backend no descarga URLs que mande el cliente. Las únicas
llamadas salientes van a destinos fijos por configuración: Nessie, Anthropic y
Snowflake.

**Test:** `test_owasp_api.py::test_api7_no_endpoint_accepts_a_url_to_fetch`
revisa que ningún parámetro ni campo de entrada parezca una URL.

## API8 · Security Misconfiguration ✅ 🟡

**Inyección SQL:**

- Todo valor va parametrizado (`:nombre`).
- Los `f-string` de SQL sólo insertan nombres de tabla o columna definidos en
  el código y marcadores de parámetros. Se revisaron uno por uno los que arman
  `WHERE` dinámicos: `accounting.ledger`, `purchases.spending` y `sales._in_query`.
- `test_owasp_api.py::test_api8_sql_injection_attempts_are_plain_data` manda
  cuatro payloads por path, query, stats, token de pago y cuerpo, y comprueba
  que no se borra ni filtra nada.
- `test_assistant_golden.py::test_questions_never_touch_the_database_schema`
  cubre SQL escrito en la pregunta del asistente.

**Stack traces en 500:**

- Un error no controlado responde `{"detail":"internal_error","error_id":…}`.
- Los 422 no repiten lo que mandó el cliente.
- Tests: `test_owasp_api.py::test_api8_a_real_route_that_crashes_leaks_no_internals`,
  `test_error_visibility.py` y `test_security_hardening.py::test_validation_errors_never_echo_the_password`.

**Headers y CORS:**

- Todas las respuestas llevan `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` y
  `Cache-Control: no-store`. Agregados en esta pasada.
- CORS sólo responde a los orígenes configurados y nunca con credenciales.
- Tests: `test_api8_security_headers_are_on_every_response` y
  `test_api8_cors_only_answers_configured_origins_and_never_with_credentials`.

**Datos hacia terceros:** Sentry opcional con depuración verificada (Fase 6).

**🟡 Decisiones:**

- `/docs` (Swagger) queda público: es parte de enseñar el proyecto y no expone
  nada que las rutas no expongan.
- La API responde JSON y no manda `Content-Security-Policy`. El frontend
  estático en Render no tiene headers propios configurados.

## API9 · Improper Inventory Management ✅ corregido en esta pasada

**Hallazgo:** las rutas de la plantilla original, `/accounts/...` y
`POST /accounts/{id}/transactions/simulate` (passthrough a Nessie), eran
**públicas, sin token ni rate limit, y el frontend no las usa**. En modo mock,
`simulate` agregaba transacciones a una lista en memoria sin tope. Con Nessie
real, crearía compras usando la API key del equipo.

**Corrección:**

- Esas rutas responden 404 con `ENVIRONMENT=production`, que `render.yaml` ya
  declara.
- `ENABLE_LEGACY_NESSIE_ROUTES=true` las fuerza si alguna vez hacen falta.
- `NewPurchase` quedó acotado.

**Tests:** `test_owasp_api.py::test_api9_*`.

## API10 · Unsafe Consumption of APIs ✅

**Cómo se cubre:**

- **Salida del LLM:** toda cifra que escriba (montos con o sin centavos,
  porcentajes, cantidades, "un millón") tiene que existir en los hechos del
  motor, o se descarta la redacción. La guardia se fortaleció en esta pasada:
  antes sólo revisaba montos con formato `$x.xx`.
- **Nessie:** respuestas normalizadas a modelos Pydantic, y sus errores se
  reportan sin la key.

**Tests:**

- `test_assistant_golden.py`: 45 preguntas doradas, cada una con una batería de
  LLM tramposo.
- `test_error_visibility.py::test_real_nessie_down_is_degraded_and_never_leaks_the_key`

---

## Pendientes fuera de esta pasada

- ⏳ **Rol de Snowflake:** `render.yaml` usa `ACCOUNTADMIN`. Para un servicio
  público conviene un rol de mínimo privilegio. Queda para la Fase 9, con la
  cuenta real.
- 🟡 **Geolocalización:** la encuesta manda las coordenadas del GPS a
  `nominatim.openstreetmap.org` para obtener la ciudad, sin avisarlo
  explícitamente. Es un tercero, pero no guarda nada del lado del proyecto. Un
  aviso en ese paso sería lo honesto.
- 🟡 **`frontend/src/onboarding/Onboarding.jsx`:** copia vieja de la encuesta
  que nadie importa. No se sirve, pero confunde al revisar el repo.
