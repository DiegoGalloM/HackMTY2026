# Descripciones públicas del proyecto

Textos listos para copiar donde se describa el proyecto fuera del repo. Todos
cumplen la misma regla (fases 1 y 8 de [`ROADMAP_PULIDO.md`](./ROADMAP_PULIDO.md)):
quien lea **sólo uno** tiene que entender que es una demo con dinero simulado y
que no es un producto de Capital One.

Estos textos no se publican solos: hay que pegarlos a mano en cada lugar (ver
[la lista del final](#dónde-pegarlos)).

> Antes de publicar, no afirmes que corre sobre Snowflake real hasta cerrar la
> Fase 9: hoy está verificado en modo sqlite/mock (ver `PROJECT_STATUS.md`).

---

## Aviso completo (español)

> Capital One Business fue construido en 36 horas para el reto de Capital One en
> HackMTY 2026. Es una demo: todas las transacciones son simuladas; no se procesa
> dinero real ni se conecta a cuentas bancarias reales. No es un producto de
> Capital One ni está afiliado, respaldado o patrocinado por Capital One, N.A. —
> el nombre y la identidad visual se usan únicamente para describir honestamente
> el reto para el que fue construido.

## Full notice (English)

> Capital One Business was built in 36 hours for the Capital One challenge at
> HackMTY 2026. It is a demo: every transaction is simulated; no real money is
> processed and no real bank accounts are connected. It is not a Capital One
> product and is not affiliated with, endorsed or sponsored by Capital One, N.A.
> — the name and visual identity are used only to describe the challenge it was
> built for.

---

## Una línea (bio, tagline, título de video)

- **ES:** Demo de HackMTY 2026 (dinero simulado): flujo de efectivo, inventario y
  contabilidad automática para microempresas, con un asistente que responde con
  los datos del negocio.
- **EN:** HackMTY 2026 demo (simulated money): cash flow, inventory and automatic
  bookkeeping for micro-businesses, with an assistant that answers from the
  business's own data.

## Devpost / resumen corto

**ES**

> Capital One Business es una demo construida en HackMTY 2026 para el reto de
> Capital One. El dueño de un micro-negocio vende con QR y compra con su tarjeta
> de negocio; la app lleva sola el inventario con recetas, la contabilidad de
> partida doble, los estados financieros y las razones, y un asistente responde
> preguntas como "¿por qué bajó mi utilidad?" con los números del motor, nunca
> inventados por el LLM. **Todo el dinero es simulado:** los pagos usan un
> proveedor de prueba y no hay conexión con bancos reales. No es un producto de
> Capital One ni está afiliado a Capital One, N.A.

**EN**

> Capital One Business is a demo built at HackMTY 2026 for the Capital One
> challenge. A micro-business owner sells with a QR code and buys with a business
> card; the app keeps inventory with recipes, double-entry books, financial
> statements and ratios on its own, and an assistant answers questions like "why
> did my profit drop?" with numbers from the engine, never invented by the LLM.
> **All money is simulated:** payments go through a test provider and nothing
> connects to real banks. It is not a Capital One product and is not affiliated
> with Capital One, N.A.

## Post de LinkedIn (base para adaptar)

> En HackMTY 2026 construimos, en 36 horas, **Capital One Business**: una demo
> para el reto de Capital One que le lleva a un micro-negocio el flujo de
> efectivo, el inventario y la contabilidad sin que tenga que saber de
> contabilidad. Vende con QR, compra con su tarjeta y la app arma sola los libros,
> los estados financieros y las lecciones de educación financiera según lo que
> pasa en su negocio.
>
> Para dejarlo claro desde el inicio: **es una demo con dinero simulado**. No
> procesa dinero real, no se conecta a cuentas bancarias y no es un producto de
> Capital One ni está afiliado a Capital One, N.A.; usamos el nombre para
> describir el reto para el que lo construimos.
>
> Repo: github.com/DiegoGalloM/HackMTY2026

## Presentación

- **Pie de cada diapositiva:** "Demo de HackMTY 2026 · dinero simulado · no
  afiliado a Capital One, N.A."
- **Diapositiva final:** el aviso completo en español o en inglés, y la nota de
  que las imágenes de la presentación fueron generadas con IA (ver "Créditos y
  transparencia" en el README).

---

## Dónde pegarlos

Hay que hacerlo a mano:

- [ ] Devpost: descripción del proyecto (resumen corto + aviso completo al final).
- [ ] LinkedIn: el post y, si se comparte el link del demo, revisar que la
      preview muestre la descripción nueva (sale de `og:description` en
      `frontend/index.html`, que ya dice "dinero simulado").
- [ ] Presentación: pie de diapositivas y diapositiva final.
- [ ] Descripción del video demo, si está publicado: la línea + el aviso completo.
