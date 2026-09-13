# Demo para jueces — 4 minutos

## Antes de empezar

```bash
python dev.py            # backend (Snowflake si backend/.env lo tiene) + frontend
```

Primera vez con Snowflake: el backend aplica las migraciones 003/004 solo al
arrancar; la primera entrada a la demo siembra la panadería (~10 s) y queda
guardada, las siguientes entran al instante.

Para que un celular escanee el QR: `python dev.py --host 0.0.0.0` y abrir la
app por la IP de la laptop (`http://192.168.x.x:5173`); el link del QR usa ese
mismo origen.

## Guion

1. **Contexto del negocio.** Landing → *Empezar* → *Explorar la demo*.
   Entra "Panadería La Espiga" (María, Austin, comida). La pantalla Cuenta ya
   muestra efectivo real, ventas y ganancia del mes, y el último movimiento.
   Todo eso sale del diario contable, no de mocks.

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
   $X, ganancia estimada, inventario actualizado, impuesto apartado. Ve a
   *Análisis*: ventas del mes, caja, indicadores. *Ver mis libros* → Diario:
   el asiento `Venta #N (QR)` y su `Costo de venta`; Balanza: cuadra; Balance:
   Activos = Pasivos + Capital.

6. **Pregúntale a tu negocio.** *Asistente* →
   - "¿Cómo van mis ventas esta semana?" (incluye la venta que acabas de hacer)
   - "¿Por qué bajó mi utilidad este mes?" (ventas ↓, insumos más caros, gastos fijos)
   - "¿Cuántos pasteles de chocolate puedo hacer?" (te limita el insumo X)
   - "¿Qué es el capital de trabajo?" (explicación + tu cifra real)
   Cada respuesta trae la evidencia y la fuente; con Cortex/Anthropic se
   redacta con IA, sin inventar números.

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| "No se pudo conectar con el servidor" | `python dev.py` no está corriendo o el frontend apunta a otro `VITE_API_URL`. |
| La demo entra pero no hay datos | Snowflake tardó: recarga; la primera siembra toma ~10 s. |
| Snowflake caído | `USE_SNOWFLAKE=false` en `backend/.env`: todo sigue igual con sqlite en memoria (la demo se siembra en 1 s). |
| Reiniciar la panadería | `POST /business/{owner_id}/demo/seed?reset=true` con el token de la demo. |
| Usuario de la demo | `demo_panaderia` / `PanDeCadaDia2026` (también sirve en *Iniciar sesión*). |
