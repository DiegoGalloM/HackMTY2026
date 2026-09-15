# Demo para jueces — 4 minutos

## Antes de empezar

```bash
python dev.py            # backend (Snowflake si backend/.env lo tiene) + frontend
```

Primera vez con Snowflake: el backend aplica las migraciones 003/004 solo al
arrancar; la primera entrada a cada negocio demo lo siembra (~10 s) y queda
guardado, las siguientes entran al instante.

## Dos negocios de ejemplo

*Explorar la demo* abre un selector. Los dos usan el mismo motor: otro giro,
otro país y otro catálogo de cuentas.

| | Panadería La Espiga | Estética Carolina |
|---|---|---|
| Dueña / lugar | María Espinoza · Austin, TX | Carolina Ramírez · Monterrey, NL |
| Giro | `comida`, 1 persona | `belleza`, 2 personas |
| Usuario | `demo_panaderia` / `PanDeCadaDia2026` | `demo_estetica` / `BellezaConNumeros2026` |
| Qué demuestra | Productos con receta, inventario perecedero, compras al mayoreo con ticket; el proveedor sube precios y bajan los pasteles. | Servicios que consumen insumos (tinte = 2 tubos + oxidante), venta de producto al público, IVA 16 %, cifras en pesos; el proveedor se queda sin tinte y bajan las citas. |
| Preguntas que lucen | "¿Cuántos pasteles de chocolate puedo hacer?", "¿Por qué bajó mi utilidad?" | "¿Qué servicio me deja más ganancia?", "¿Cuándo se me acaba el tinte?" y luego "¿Cuándo se me acaba el esmalte?" (completa: el asistente no recuerda la pregunta anterior) |

Las dos cuentas también sirven en *Iniciar sesión*: se aprovisionan al
arrancar el backend (no hay que pulsar antes "Explorar la demo") y, como ya
tienen perfil, entran directo a Cuenta, nunca a la encuesta.
`POST /demo/session` acepta `{"business": "panaderia" | "estetica"}`; sin
cuerpo entra la panadería.

> Con Snowflake la primera siembra tarda unos segundos por negocio y corre en
> segundo plano: si entras muy rápido tras levantar el backend, espera a ver
> `Negocio demo listo: …` en el log.

Para que un celular escanee el QR: `python dev.py --host 0.0.0.0` y abrir la
app por la IP de la laptop (`http://192.168.x.x:5173`); el link del QR usa ese
mismo origen.

## Guion

1. **Contexto del negocio.** Landing → *Empezar* → *Explorar la demo*.
   Entra "Panadería La Espiga" (María, Austin, comida). La pantalla Cuenta ya
   muestra efectivo real, ventas y ganancia del mes, y el último movimiento.
   Todo eso sale del diario contable, no de mocks. La tarjeta de Cash Insight
   dice **"Según tus datos"**: cuando los datos del negocio disparan una lección
   (inventario atorado, insumos por agotarse, caja justa), gana sobre la de la
   encuesta. *ONE Education* muestra las de datos y, después, la de la encuesta
   de un tema distinto.

2. **Una compra entra sola.** *Compras* → *Simular compra con la tarjeta*.
   Entra "Restaurant Depot $152.60", clasificada como inventario y ya
   contabilizada (DR Inventario / CR Tarjeta). Vuelve a pulsar: "Amazon
   $129.99" cae en **¿Para qué fue esta compra?** Elige *Equipo o herramienta*:
   se publica la reclasificación y el negocio aprende (la siguiente compra en
   Amazon ya sale como equipo).

3. **Ticket → inventario.** En la compra de Restaurant Depot, *Agregar ticket*
   → *Aplicar al inventario*. Harina, huevo, mantequilla… suben en cantidad y
   costo promedio. Ábrelo en *Inventario* si quieres mostrar la bitácora.

4. **Vender con QR.** *Vender* → Pastel de chocolate ×1 + Café ×2 → *Generar
   QR*. Muestra que cada producto tiene receta ("22 disponibles" sale del
   inventario). Escanea con el celular (o *Abrir como cliente*): la página
   pública dice qué compra y cuánto, sólo un botón **Pagar**. Si no hay
   celular, *Simular pago*.

5. **Consecuencias automáticas.** La hoja cambia a *Pago recibido*: vendiste
   $X, ganancia estimada, inventario actualizado, impuesto apartado. *Ver
   resumen*: ventas del mes, caja, lo que necesita atención y el diario del
   periodo como tabla (Debe / Haber). *Ver mis libros* → Diario: el asiento
   `Venta #N (QR)` y su `Costo de venta`; Balanza: cuadra; Balance: Activos =
   Pasivos + Capital; *Indicadores*: las razones explicadas.

6. **Pregúntale a tu negocio.** Botón central *Análisis*: abre con un resumen
   de apertura (caja, ventas de la semana, puntos de atención como chips).
   - "¿Cómo van mis ventas esta semana?" (incluye la venta que acabas de hacer)
   - "¿Por qué bajó mi utilidad este mes?" (ventas ↓, insumos más caros, gastos fijos)
   - "¿Cuántos pasteles de chocolate puedo hacer?" (te limita el insumo X)
   - "¿Qué es el capital de trabajo?" (explicación + tu cifra real)
   Cada respuesta trae la evidencia y la fuente; con Cortex/Anthropic se
   redacta con IA, sin inventar números. **Cada pregunta va sola**: no hay
   conversación, así que se pregunta completo ("¿Cómo van mis ventas el mes
   pasado?") en vez de "¿y el mes pasado?".

7. **El mismo motor, otro negocio.** *Más → Cerrar sesión* → *Explorar la
   demo* → *Estética Carolina*. Cuenta saluda a Carolina con el insight de sus
   datos; la lección de belleza de su encuesta está en *ONE Education*
   ("¿Cuánto te deja realmente una cita?"); *Análisis* abre con el tinte por agotarse; pregunta "¿Cuándo se me
   acaba el tinte?" y después "¿Cuándo se me acaba el esmalte?".

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| "No se pudo conectar con el servidor" | `python dev.py` no está corriendo o el frontend apunta a otro `VITE_API_URL`. |
| La demo entra pero no hay datos | Snowflake tardó: recarga; la primera siembra toma ~10 s. |
| Snowflake caído | `USE_SNOWFLAKE=false` en `backend/.env`: todo sigue igual con sqlite en memoria (la demo se siembra en 1 s). |
| Reiniciar un negocio demo | `POST /business/{owner_id}/demo/seed?reset=true&business=panaderia|estetica` con el token de esa demo. |
| Usuarios de la demo | `demo_panaderia` / `PanDeCadaDia2026` y `demo_estetica` / `BellezaConNumeros2026` (también sirven en *Iniciar sesión*). |
