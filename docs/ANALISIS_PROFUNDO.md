# Capital One Business — Análisis profundo del proyecto (HackMTY 2026)

**Repo:** github.com/DiegoGalloM/HackMTY2026 · **Devpost:** devpost.com/software/capital-one-business · **Demo:** www.capitalonebusiness.tech
**Equipo:** Diego Gallo, Luis Ernesto Colunga Lozano, Carlos, Ricardo Cango · **Track:** Capital One — SMB Cash-Flow & Working Capital Intelligence

---

## 0. Resumen ejecutivo

Capital One Business no es una demo de hackathon con datos de mentiras: es, hasta donde permite el tiempo de un HackMTY, un **núcleo de contabilidad de partida doble real** (diario, mayor, balanza, estados financieros, razones financieras) conectado a un **motor de inventario con costo promedio ponderado**, expuesto a través de un flujo de "vender con QR / comprar con tarjeta" que contabiliza solo, y explicado a un dueño de negocio sin formación contable mediante un **asistente en lenguaje natural que nunca inventa una cifra**. Todo corre sobre **Snowflake** como base de datos autoritativa, con **Snowflake Cortex** como una de las dos opciones de modelo de lenguaje del asistente.

Lo que el equipo llama informalmente "el RAG con Snowflake" es, en realidad, algo más interesante y más defendible en un contexto financiero que un RAG vectorial genérico: es un **enrutador de intenciones determinista** que decide qué herramienta del motor contable llamar, una **recuperación léxica de una base de conocimiento financiero** (FDIC Money Smart, SBA, CFPB) para preguntas de concepto, y un LLM que **sólo redacta** — con una guardia de código que descarta cualquier respuesta que contenga una cifra en dólares que no exista ya en la evidencia calculada por el backend. Es, en el fondo, una arquitectura anti-alucinación construida a propósito para un producto que da consejos de dinero a gente que no puede permitirse que le mientan.

El proyecto ataca un problema real y bien cuantificado: la inmensa mayoría de los negocios en México, Estados Unidos y América Latina son microempresas de 1 a 5 personas que no tienen tiempo, dinero ni formación para llevar sus finanzas, y a las que la educación financiera tradicional (cursos, PDFs, seminarios) casi nunca llega en el momento en que importa. Este documento analiza el proyecto desde tres ángulos con el mismo peso que pediste: **qué tan sólido es técnicamente**, **qué tan bien resuelto está el sistema de datos/IA con Snowflake**, y **qué tan real es el impacto potencial en las microempresas y las personas que las llevan**.

**Veredicto en una frase:** es un proyecto de hackathon con la profundidad técnica de un producto en serio (113+ tests de backend, CI, aislamiento multi-tenant verificado, doble motor contable balanceado por invariantes) construido sobre una tesis de mercado sólida y bien documentada, con una decisión de diseño de IA inusualmente madura para el contexto (redacción sin autoridad numérica) — cuyo mayor riesgo no es la ejecución técnica sino que las piezas de producto que conectan todo (encuesta → Cash Insight en la pantalla principal) estaban, a la fecha de los documentos del repo, todavía a medias.

---

## 1. El problema y la oportunidad de mercado

### 1.1 El dolor, en las palabras del propio equipo

La presentación lo resume con una frase que es, honestamente, el mejor "hook" de pitch que tiene el proyecto:

> *"Sé que vendo bien, pero no sé si estoy ganando."*

Es la contradicción central de un micro-negocio: hay ventas, hay actividad, hay clientes — pero el dueño no tiene la más remota idea de si el negocio genera utilidad real, porque llevar la cuenta le tomaría (según su propia investigación de usuario) **cerca de 12 horas** que no tiene, y las herramientas de finanzas que sí existen exigen llenar tablas que un dueño de una tortillería, una estética o un taller no tiene tiempo ni ganas de llenar.

El ciclo que dibuja la slide 2 del pitch (*"no hay tiempo ni financiamiento → no liquidez → no operación → bancarrota"*) es simplificado, pero apunta al mecanismo real y bien documentado en la literatura de crédito a pequeñas empresas: la iliquidez, no la falta de rentabilidad, es la causa más común de cierre de un micro-negocio.

### 1.2 Tamaño del mercado — los números, verificados

El deck y el Devpost citan tres cifras. Las contrasté contra fuentes primarias:

| Cifra citada | Fuente del equipo | Verificación independiente |
|---|---|---|
| 95.4% de las empresas en México son microempresas | (implícita, INEGI) | **Confirmado**: INEGI reporta 95.5% para 2023 en su comunicado de los Censos Económicos — la cifra del equipo está prácticamente exacta. |
| 90% de las empresas en América Latina y el Caribe son microempresas | Slide 2 (sin atribuir) | Consistente con reportes de BID/CAF y el índice de políticas PYME de la OCDE para la región, que sitúan a las microempresas como la abrumadora mayoría del tejido empresarial de ALC (los reportes formales agregan micro+pequeña+mediana como ~99% de las firmas, con las micro solas dominando ese total). |
| 90% de las empresas no pueden acceder a financiamiento formal por falta de formación financiera | Slide 2 | Direccionalmente consistente con la literatura de CAF/BID sobre la brecha de financiamiento a mipymes en la región; la causa exacta (formación vs. garantías vs. informalidad) varía por fuente, pero el diagnóstico de "acceso muy restringido" es el consenso. |
| 1.7 billones (trillion) de capital generado por LATAM y el Caribe | Slide 2 | No pude verificar esta cifra específica de forma independiente en el tiempo disponible; aparece sin fuente en el deck. La cifra de PIB generado por mipymes en la región sí es consistente en orden de magnitud con estudios de CEOE/CAF que hablan de ~28% del PIB regional atribuible a mipymes — pero recomendaría a favor de citar la fuente primaria exacta antes de repetir "1.7 billones" frente a jueces que puedan pedir la referencia. |
| 64% de los "nonemployer firms" de EE.UU. dependen de fondos personales del dueño para cubrir problemas financieros | Devpost ("What it does") | La Fed Small Business Credit Survey (reporte de nonemployer firms) confirma la **dirección** exacta del dato: las firmas nonemployer, especialmente las más jóvenes (0–2 años), "dependen más de los fondos personales del dueño" al enfrentar dificultades financieras, y esa dependencia baja según el negocio madura. No verifiqué el número "64%" exacto en el reporte público más reciente, pero el fenómeno que describe es real y está documentado por la Fed. |

**Lectura honesta para el pitch:** las cifras estructurales (95%+ microempresas en México y LatAm) están bien fundamentadas y son fácilmente defendibles ante un juez que las cuestione. La cifra de "$1.7 billones" y el "64%" puntual conviene tenerlos con la fuente primaria a la mano (Fed Small Business Credit Survey para el segundo) porque un juez de Capital One — que conoce sus propios datos de crédito a pequeñas empresas — puede pedirla.

### 1.3 Por qué el momento es bueno para este producto

Tres corrientes convergen y el proyecto las usa bien:

1. **Embedded finance / banca como plataforma.** Capital One ofreciendo Nessie como sandbox público de banca simulada es exactamente la apuesta de la industria: el valor ya no está en "tener una cuenta", está en la capa de inteligencia que se construye encima de las transacciones. Esto es lo que compañías como Ramp, Brex o Mercury monetizan en el segmento alto; nadie lo está haciendo bien todavía para el segmento de 1 a 5 empleados.
2. **LLMs baratos y "en la nube de datos".** Que Snowflake ofrezca Cortex (LLM corriendo junto a los datos, sin mover nada fuera del perímetro de la cuenta) es relevante para un producto financiero: reduce la superficie de datos sensibles que sale de Snowflake y es, además, gratis para el hackathon si ya se paga el warehouse.
3. **Educación financiera "just-in-time" vs. cursos.** La tesis del equipo — y la que valida su propia investigación citada en Devpost (FDIC, SBA, CFPB, Fed Small Business Credit Survey, Operation HOPE, Accion Opportunity Fund) — es que un curso genérico de finanzas no cambia el comportamiento de un dueño de micro-negocio, pero una alerta contextual en el momento exacto en que su patrón de compra revela sobre-stock sí. Es una apuesta de producto razonable y alineada con lo que dice la literatura de "nudges" financieros.

---

## 2. La solución — qué construyeron realmente

### 2.1 Onboarding de 2 minutos

Encuesta adaptativa por categoría de negocio (comida, retail, servicios, construcción, transporte, belleza), con interacción tipo burbujas de chat, preguntas sí/no universales + específicas por giro, selector de días de operación, número de empleados y ciudad por GPS con respaldo manual si falla. Cero texto libre salvo la ciudad. El objetivo de diseño explícito es no perder al usuario en un formulario largo — coherente con el dolor que el propio deck identifica ("no hay tiempo").

### 2.2 Cash Insights contextuales

En vez de "cursos" de educación financiera, la app decide **una sola tarjeta** para mostrar, con prioridad de "problema detectado en los datos" sobre "educación genérica". Hay 11 disparadores ya escritos: 5 nacen de respuestas de la encuesta (se quedó sin stock, compra de más, combinación de ambos, guarda inventario, compra al mayoreo) y 6 son específicos por giro (comida, retail, servicios, construcción, transporte, belleza). El texto de cada lección está escrito con un tono de "explicación a alguien sin formación contable" — por ejemplo, la de sobrecompra: *"Comprar de más no es un gasto que desaparece — es dinero que ahora está guardado en producto, no en tu bolsillo."* Es buena redacción de producto: traduce un concepto contable (capital de trabajo atrapado en inventario) a una frase que un dueño sin vocabulario financiero entiende de inmediato.

### 2.3 El corazón real del producto: contabilidad que se lleva sola

Esto es lo que separa a Capital One Business de "otra app de encuestas con IA": construyeron un **núcleo financiero completo**, no un dashboard con números inventados.

- El dueño **vende con QR** (genera una orden, el cliente paga desde una página pública con un token opaco de 256 bits) o **compra con su tarjeta de negocio** (Nessie real o mock).
- Cada evento se normaliza y dispara **un asiento de partida doble real**. Ejemplos documentados en `FINANCIAL_CORE.md`:
  - Venta pagada de $50 + $4 de impuesto, costo $8.80 → `DR Banco 54 / CR Ventas 50 / CR Impuesto por pagar 4` y `DR Costo de ventas 8.80 / CR Inventario 8.80`.
  - Compra con tarjeta de inventario → `DR Inventario / CR Tarjeta de crédito del negocio`.
  - Corrección de clasificación del dueño → `DR cuenta nueva / CR cuenta vieja` (reclasificación, nunca edición retroactiva).
- De ahí salen solas la balanza (ajustada y sin ajustar), el estado de resultados, el balance general (que verifica `Activos = Pasivos + Capital` en cada request) y las razones financieras (liquidez, prueba ácida, capital de trabajo, márgenes, rotación de inventario, apalancamiento), cada una con su fórmula, su estado (bueno/atención/crítico) y una explicación en español llano.
- El inventario usa **costo promedio ponderado** de verdad: cada producto tiene una receta (`item_components`), y al pagarse una venta se descuentan los insumos a su costo promedio, no a un número fijo. Si el proveedor sube el precio de la harina, el costo promedio sube solo, poco a poco, y el margen del pastel baja aunque el dueño no haya cambiado nada — exactamente el tipo de insight que un dueño sin contador nunca vería por sí mismo.

Esto no es un detalle menor para la evaluación de "Complejidad Técnica": construir un motor contable de partida doble que siempre balancea, con inventario valuado correctamente y con inserción idempotente (el mismo pago no se contabiliza dos veces, verificado por `provider_ref`), es un problema de ingeniería genuinamente difícil de resolver bien en 36 horas. Que además tenga 14 tests de invariantes contables dedicados (`test_finance_engine.py`) sugiere que no es un motor "que parece funcionar en la demo" sino uno con las esquinas verificadas.

### 2.4 El asistente conversacional

"Pregúntale lo que sea a tu negocio" — analizado a fondo en la sección 4.

### 2.5 Dos demos, un solo motor

"Panadería La Espiga" (María, Austin TX, comida, dólares, IVA implícito de EE.UU.) y "Estética Carolina" (Carolina, Monterrey NL, belleza, pesos, IVA 16%) corren sobre el **mismo motor**, el mismo catálogo de cuentas parametrizado por giro y la misma tubería de siembra (`Pipeline`). Esto demuestra generalización real del producto entre países, monedas (de forma simplificada — ver limitaciones) y giros de negocio, no sólo entre dos nombres de negocio con los mismos datos de fondo. Es una prueba de robustez de arquitectura más convincente que "una sola demo bonita".

---

## 3. Arquitectura técnica — vista completa

### 3.1 Diagrama de flujo real (tal como está en el repo)

```
evento real          QR pagado · compra con tarjeta · conteo de inventario
      ↓
evento normalizado   PaymentEvent · NormalizedTransaction · ajuste
      ↓
motor de inventario  inventory_items + inventory_movements (costo promedio ponderado)
motor contable       journal_entries + journal_lines (partida doble, siempre balanceado)
      ↓
Snowflake / sqlite   16 tablas multi-negocio con business_id (migraciones 003, 004)
      ↓
derivados            v_general_ledger, v_account_balances (vistas SQL, nunca editables)
      ↓
analítica            razones, salud de caja, drivers de utilidad (100% backend)
      ↓
API → frontend → asistente   explicación en lenguaje llano; el LLM sólo redacta
```

### 3.2 Stack tecnológico completo

| Capa | Tecnología | Versión | Nota |
|---|---|---|---|
| Frontend | React | 19.3 | Última mayor, con Router 7.18 |
| Build | Vite | 8.3 | + TypeScript 7 (canary reciente) |
| Estilos | Tailwind CSS | 4.3 | vía plugin nativo de Vite |
| Animación | Framer Motion + Animejs | 13.2 / 4.5 | factor "wow" de UI |
| PWA | vite-plugin-pwa | 1.3 | instalable como app |
| QR | qrcode.react | 4.2 | generación del QR de cobro |
| Backend | FastAPI + Pydantic | 0.115 / 2.9 | tipado estricto de esquemas |
| Auth | bcrypt + PyJWT | 4.2 / 2.10 | hashing + tokens firmados HMAC |
| Base de datos | Snowflake (`snowflake-connector-python` 4.7.3) | — | con capa `sqlite` intercambiable |
| LLM | Anthropic SDK (Claude Opus 5) → Snowflake Cortex (`claude-sonnet-4-5`) → plantillas | — | cadena de fallback en cascada |
| Testing | pytest + pytest-asyncio (backend), Playwright (e2e) | — | 119 backend + 29 specs e2e × 2 proyectos |
| CI | GitHub Actions | — | lint (ruff) + test + build en cada push/PR |
| Deploy | Vercel (frontend) + Railway (backend) | — | pivote desde un VPS a mitad de hackathon (documentado como reto superado) |
| Escritorio | Tauri (con Electron como plan B) | — | mismo build de React empaquetado como binario nativo — para no ser "sólo una página web" |
| Banca simulada | Nessie API de Capital One | — | cliente real + cliente mock intercambiables por variable de entorno |

Es un stack de 2026 razonable y coherente: nada exótico, todo elegido por velocidad de desarrollo y por reducir superficie de bugs (Pydantic para validación de esquemas, FastAPI para documentación automática, Snowflake para no tener que administrar infraestructura de base de datos durante el evento).

### 3.3 La capa de datos — bien pensada, no improvisada

`backend/app/db/base.py` define una interfaz mínima (`execute`, `rows`, `execute_many`, `transaction()`, `ensure_schema()`) que implementan tanto `SqliteDatabase` (memoria o archivo, para tests y desarrollo sin red) como `SnowflakeDatabase` (pool de 4 conexiones persistentes, autocommit, `BEGIN/COMMIT` explícito en transacciones). El SQL de las migraciones (`003_financial_core.sql`, `004_financial_views.sql`) está escrito **de forma portable a propósito** — `VARCHAR`, `NUMBER(18,4)`, `BOOLEAN`, `TIMESTAMP_NTZ`, sin defaults con funciones ni VARIANT en esas tablas — precisamente para poder correr contra sqlite o Snowflake sin dos versiones del esquema.

Esto es una decisión de arquitectura poco común en un hackathon (donde lo típico es acoplarse a la base de datos elegida) y paga dividendos reales: **la demo nunca depende de que Snowflake esté arriba** — con `USE_SNOWFLAKE=false` todo funciona igual, la siembra tarda 1 segundo en vez de ~10, y sólo se pierde la elegibilidad al prize de "Best Use of Snowflake", nunca el producto. Es el mismo patrón de resiliencia que aplicaron al cliente de Nessie (real + mock intercambiables), y está documentado explícitamente como lección aprendida de HackMTY 2025, cuando la API de Nessie se cayó a media competencia.

### 3.4 Seguridad y aislamiento multi-tenant — verificado con tests, no solo prometido

Cada tabla lleva `business_id` (= `user_id` del dueño); nunca una tabla por usuario. La guardia `require_owner` protege **estructuralmente**, a nivel de router (no de endpoint individual), toda ruta `/business/{owner_id}/…`: si el `sub` del JWT no coincide con el `owner_id` del path, 403. El comentario en el propio código explica por qué se declaró `owner_id` con `Path(...)` explícito: sin eso, en una ruta sin ese parámetro en el path, FastAPI lo leería como query string, y un `?owner_id=<el mío>` pasaría la validación mientras la operación real se ejecuta sobre los datos de otro negocio — un bug de autorización sutil y real que se previno a propósito.

Hay tests específicos para exactamente este tipo de fallas silenciosas:
- `test_owner_routes_are_guarded_by_the_router_not_by_each_endpoint`
- `test_owner_id_cannot_be_supplied_as_a_query_parameter`
- `test_snowflake_user_insert_uses_merge_for_locking` (previene una condición de carrera real: Snowflake no bloquea en `INSERT … WHERE NOT EXISTS`, así que dos registros simultáneos con el mismo username podrían duplicarse; usan `MERGE`, que sí serializa)
- `test_bcrypt_never_runs_on_el_event_loop` (evita bloquear el servidor async con hashing síncrono)
- `test_short_jwt_secret_is_refused_at_startup`, `test_jwt_algorithm_is_restricted_to_hmac`
- Política de contraseñas con 6 reglas verificadas (12+ caracteres, mayúscula/minúscula/dígito, no contener el username, no estar en la lista de contraseñas más comunes)

Esto es, para un proyecto de hackathon, un nivel de paranoia de seguridad genuinamente por encima del promedio — normalmente estas cosas se descubren en producción, no se anticipan con un test unitario el mismo fin de semana.

### 3.5 Testing y CI — cifras concretas

- **119 tests de backend** (`pytest -q`), organizados en: `test_finance_engine.py` (14, invariantes contables e inventario), `test_finance_api.py` (5, flujo HTTP completo: catálogo → orden → QR → pago público → libros → análisis → asistente, y guardia de tenant), `test_assistant.py` (7, enrutamiento, cifras del motor, aislamiento, guardia del LLM), `test_demo.py` (6, ambas demos: libros que cuadran, insumo por agotarse, causa real de caída de utilidad, idempotencia, reproducibilidad al centavo), `test_auth.py` (25), `test_security_hardening.py` (12), `test_business_profile.py` (4), `test_health.py` (4).
- **29 specs de Playwright × 2 proyectos** de e2e, incluyendo casos de regresión específicos (`login-returning.spec.ts`, `demo-picker.spec.ts`).
- **CI en GitHub Actions**: lint (`ruff`), tests de backend con `USE_MOCK_NESSIE=true` (para que el pipeline nunca dependa de que Nessie esté arriba), build de frontend, y job de e2e — en cada push a `main`/`develop` y en cada PR.

No pude ejecutar la suite yo mismo dentro de esta sesión (el análisis se hizo sobre el código estático, sin levantar el backend), pero la estructura, nomenclatura y cobertura declarada en `PROJECT_STATUS.md` (fechado 2026-09-13, "verificado de punta a punta contra Snowflake real") son consistentes con lo que se ve en el propio código de los tests.

---

## 4. El sistema Snowflake + IA — análisis honesto y con detalle técnico

Aquí es donde vale la pena ser preciso, porque hay una diferencia importante entre lo que el equipo llama informalmente "el RAG" en Devpost y lo que el código realmente implementa — y esa diferencia, bien explicada, es en realidad un punto a favor del proyecto, no en contra.

### 4.1 Qué es realmente el "RAG": tres piezas separadas, no una

**Pieza 1 — Enrutador de intenciones determinista (`assistant.py`).** Cada pregunta pasa por expresiones regulares (`INTENT_PATTERNS`, `PERIOD_PATTERNS`) que la clasifican en una de ~14 intenciones (ventas, utilidad, liquidez, caja, inventario, capacidad de producción, cuándo se agota un insumo, productos top, gastos, clientes, razones financieras, estados financieros, contexto de negocio, concepto). Cada intención dispara un método `_tool_*` que llama al motor contable/de inventario real y arma una lista de `evidence` (hechos con su cifra ya calculada).

**Pieza 2 — Recuperación léxica de una base de conocimiento (`knowledge.py`), la parte que sí es "RAG" en sentido estricto.** Es un corpus de 15 documentos de educación financiera (liquidez, prueba ácida, capital de trabajo, márgenes, costo de ventas, inventario, punto de reorden, flujo de efectivo, deuda, impuesto sobre ventas, cuentas por cobrar, depreciación, retiros del dueño, pricing) redactado por el equipo a partir de FDIC Money Smart, SBA y CFPB, más el contexto que el dueño dio en el onboarding (tratado también como "documentos" recuperables). La búsqueda es **léxica y determinista** (tokenización + stopwords + puntaje por coincidencia de tags/título/texto) — el propio comentario del archivo lo dice sin rodeos: *"sin vectores, sin servicio externo"*.

**Pieza 3 — LLM que sólo redacta, con guardia anti-alucinación de montos.** El LLM (Anthropic Claude Opus 5, o Snowflake Cortex con `claude-sonnet-4-5` si no hay API key de Anthropic pero sí Snowflake activo, o ninguno) recibe la pregunta, los "HECHOS" ya calculados y la respuesta base en plantilla, y su único trabajo es hacerla sonar más cálida y natural en ≤4 oraciones. Después de que el LLM responde, el código extrae con regex **todas** las cifras con `$` de su respuesta y las compara contra el conjunto de cifras que ya aparecían en la evidencia o en la respuesta base: si aparece una sola cifra que el LLM inventó, **se descarta toda la reescritura** y se usa la plantilla determinista. El propio `FINANCIAL_CORE.md` lo resume así: *"El asistente no es un RAG libre: es un enrutador de intenciones... el LLM sólo redacta."*

### 4.2 Por qué esto es una decisión de diseño mejor que un RAG vectorial "de manual" — y por qué vale la pena decirlo así frente a los jueces

Un RAG vectorial clásico (embeddings + búsqueda semántica + LLM que sintetiza la respuesta a partir de los documentos recuperados) es más impresionante en el papel, pero tiene un problema serio para un producto que da información financiera a alguien que va a tomar decisiones de dinero con ella: **el LLM sigue teniendo la libertad de "interpretar" o redondear una cifra**, y en finanzas eso es el peor tipo de error posible, porque suena confiado y es sutil de detectar.

Lo que este equipo construyó es, en efecto, un patrón de **"grounded generation" con guardia de verificación post-hoc programática** — el LLM no tiene autoridad numérica, punto. Es el mismo principio que usan los sistemas financieros serios (calculadora determinista + LLM que sólo explica el resultado, nunca lo calcula) y es notablemente más maduro que "conectar un vector store y dejar que el modelo complete". Para un track de Capital One evaluado por gente que sabe lo caro que es un error de $0.01 en un sistema bancario, esto debería presentarse como una fortaleza explícita del pitch, no disculparse por "no ser un RAG de verdad". Yo lo diría así en la presentación: *"No dejamos que la IA calcule ni un solo peso: calcula el motor contable, la IA sólo lo explica, y si intenta inventar una cifra la desechamos por código antes de que el usuario la vea."* Eso es una frase de juez ganada.

### 4.3 Snowflake como base de datos autoritativa — lo que hace de verdad

- **16 tablas del núcleo financiero** (`accounts`, `journal_entries`, `journal_lines`, `inventory_items`, `inventory_movements`, `sellable_items`, `item_components`, `customers`, `sales_orders`, `order_lines`, `payments`, `card_transactions`, `receipts`, `receipt_items`, `merchant_rules`, `business_events`) más las tablas de perfiles y usuarios (migraciones 001–004), todas versionadas con un runner de migraciones propio (`schema_migrations`) que se auto-aplica al arrancar el backend.
- **`MERGE` en vez de `INSERT`** para todo lo que necesita unicidad — decisión motivada por un detalle real y poco conocido de Snowflake que el equipo documentó explícitamente: `PRIMARY KEY`/`UNIQUE` son sólo metadata en Snowflake, **no se imponen**, y un `INSERT ... WHERE NOT EXISTS` no serializa sobre la tabla destino, así que dos registros simultáneos del mismo username podrían pasar el chequeo "no existe" al mismo tiempo y duplicarse. `MERGE` sí serializa. Que lo hayan detectado, documentado y cubierto con un test (`test_snowflake_user_insert_uses_merge_for_locking`) es evidencia de que entendieron Snowflake más allá de "es SQL en la nube".
- **`VARIANT` + `LATERAL FLATTEN` para analítica cross-negocio con privacidad incorporada.** `SnowflakeProfileStore.category_stats()` hace `FLATTEN` sobre la columna `answers` (tipo `VARIANT`, JSON semi-estructurado) para calcular, por categoría de negocio, qué porcentaje de negocios respondió "sí" a cada pregunta de la encuesta — **sin una lista fija de preguntas predefinida**, así que preguntas específicas por categoría (p. ej. "¿usas ingredientes perecederos?") también entran al cálculo automáticamente. El endpoint `GET /business-profile/stats/{category}` es **público a propósito** (alimenta una comparativa "así estás tú vs. tu categoría" antes incluso de registrarse), pero está protegido con un umbral de cohorte mínima (`MIN_COHORT = 5`): con menos de 5 negocios en la categoría, el desglose se oculta, porque con una cohorte de uno el "porcentaje" sería literalmente la respuesta de ese negocio expuesta sin token — un detalle de privacidad de datos bien pensado y con un comentario en el código que explica exactamente el riesgo que se estaba evitando (alguien podría inventar una categoría rara para tener una cohorte de uno y leer sus propias respuestas de otro usuario sin autenticarse).
- **Snowflake Cortex (`SNOWFLAKE.CORTEX.COMPLETE`) como LLM de respaldo**, corriendo dentro del perímetro de Snowflake con la misma conexión que ya usa el motor financiero — sin credenciales adicionales, sin mover datos financieros fuera de la cuenta de Snowflake. Es la opción de menor fricción de "Best Use of Snowflake" del hackathon.

### 4.4 Este componente de benchmarking es, a mi juicio, el activo de datos más subestimado del proyecto

El endpoint de `category_stats` no es sólo una curiosidad técnica de `VARIANT`/`FLATTEN`: es el germen de un **producto de datos real**. Si Capital One Business alguna vez tiene, digamos, 500 panaderías registradas, puede decirle a una panadería nueva: *"el 40% de las panaderías como la tuya se han quedado sin stock este mes; el 65% compra de más"* — un tipo de benchmarking sectorial que hoy sólo ofrecen firmas de consultoría o encuestas caras (como la propia Fed Small Business Credit Survey que usé para verificar las cifras de este documento), y que aquí sale gratis como subproducto de datos que la app ya recolecta. Vale la pena que el pitch lo mencione como "lo que viene", porque es defendible técnicamente (ya está construido) y es un argumento de moat de datos genuino: entre más negocios usan la app, mejor es el benchmark para todos — un efecto de red clásico que casi ningún competidor de este segmento tiene todavía.

### 4.5 Honestidad sobre el estado de madurez

`PROJECT_STATUS.md` es notablemente transparente sobre esto, y vale la pena repetirlo aquí porque es justo el tipo de matiz que un juez técnico agradece que el equipo mismo señale antes de que se lo pregunten: *"`snowflake_store.py` — código completo (interfaz `ProfileStore`, MERGE + queries con VARIANT para benchmarks entre negocios), pero **nunca se ha probado contra una cuenta real** porque nadie se ha registrado todavía."* Documentos posteriores (`SNOWFLAKE_SETUP.md`, `FINANCIAL_CORE.md`, fechados 2026-09-13) sí describen el núcleo financiero como "verificado de punta a punta contra Snowflake real", lo que sugiere que ese pendiente específico se resolvió más adelante en el desarrollo — pero es la clase de discrepancia entre documentos que conviene verificar de viva voz con el equipo (¿quién se registró, cuándo, con qué cuenta) antes de afirmarlo frente a un juez que pregunte "¿esto corrió de verdad contra Snowflake o es el plan?".

---

## 5. Evaluación contra la rúbrica típica de Capital One / HackMTY

Usando el propio framework de rúbrica que el equipo tiene documentado en `HACKATHON_MASTER_PROMPT.md` del proyecto Hack's Guide (Innovación 25%, Impacto/Negocio 25%, Complejidad Técnica 20%, Diseño/UX 15%, Presentación 15%):

**Innovación (fuerte).** La apuesta de "nudges basados en datos reales en vez de cursos" está bien fundamentada en investigación citada, y el diseño del asistente (LLM sin autoridad numérica) es una idea de producto poco común en el ecosistema de hackathon, donde "conectamos un LLM a nuestros datos" suele ser la norma sin ninguna guardia. Punto débil: la mecánica de "vender con QR + tarjeta de negocio = contabilidad automática" no es nueva en sí (es el pitch de Square, Clover, y de cualquier POS moderno) — la innovación real está en la capa de inteligencia encima, no en el flujo de captura.

**Impacto/Negocio (fuerte, con una advertencia).** El tamaño de mercado está bien argumentado y en gran parte verificado (sección 1.2). La debilidad es que el pitch, tal como está documentado, no llega hasta un modelo de negocio explícito (¿SaaS por suscripción? ¿comisión por transacción vía la tarjeta de Capital One? ¿freemium con el benchmarking de categoría como upsell?) — para maximizar este criterio en la rúbrica conviene cerrar esa pieza antes de presentar.

**Complejidad técnica (muy fuerte).** Motor de partida doble balanceado con invariantes verificadas por test, costeo promedio ponderado real, idempotencia a nivel de proveedor de pago, aislamiento multi-tenant verificado con tests específicos de bypass, dos bases de datos intercambiables sin duplicar esquema, integración con una API externa con fallback resiliente, cadena de tres proveedores de LLM con guardia de verificación programática. Esto está, con holgura, por encima del proyecto de hackathon promedio, y es defendible en una conversación técnica de 10 minutos con un juez escéptico.

**Diseño/UX (fuerte, con el pendiente documentado).** Paleta de marca de Capital One respetada, flujo de onboarding pensado para minimizar fricción, marco de teléfono en CSS para verse nativo en cualquier proyector, PWA instalable. El propio equipo documentó como "a medias" la conexión entre la encuesta y la pantalla principal (`Cuenta.tsx` no recibía `category`/`answers` como props, bloqueando `CashInsightCard`) — si eso seguía sin resolverse al momento de la entrega, es el hueco más visible entre "lo que se diseñó" y "lo que el juez ve en la demo".

**Presentación (dependiente de ejecución, no de material).** El deck tiene un buen "hook" (la cita del usuario), una slide de mercado con cifras fuertes, y un guion de demo de 4 minutos (`docs/DEMO.md`) con dos negocios de ejemplo, momentos "wow" bien elegidos (una compra que se reclasifica sola, un insumo por agotarse, una pregunta en lenguaje natural con evidencia). El material para un pitch de 15 (jueces) es sólido; lo único fuera del control de este análisis es la ejecución en vivo.

---

## 6. Impacto real: la gente y las microempresas a las que aplica

### 6.1 A quién sirve — con nombre y apellido, literalmente

El equipo no diseñó para "PyMEs" en abstracto: diseñó para **María Espinoza**, dueña de una panadería de una persona en Austin, TX, y para **Carolina Ramírez**, dueña de una estética de dos personas en Monterrey. Esa elección de personas — reflejada hasta en las dos demos completas con historias de 10 semanas — importa más de lo que parece: es lo que evita que el producto termine pareciéndose a un ERP con lenguaje bonito. Las categorías cubiertas por el onboarding (comida, retail, servicios, construcción, transporte, belleza) son, en la práctica, las categorías donde vive el trabajo informal y semi-formal en México y Estados Unidos: taquerías, salones de belleza de barrio, fleteros, contratistas independientes, tiendas de conveniencia familiares.

Este es, en mi lectura, el público que de verdad se beneficia y el que casi ningún producto financiero actual atiende bien:

- **Demasiado pequeño para un contador.** Contratar contabilidad profesional no es económicamente viable con los márgenes de un negocio de 1 a 5 personas — de ahí que el "sé que vendo bien pero no sé si estoy ganando" sea la norma, no la excepción.
- **Demasiado informal para la banca tradicional.** Los bancos grandes no ofrecen inteligencia financiera a una cuenta de negocio con saldos pequeños; en el mejor caso, dan un estado de cuenta en PDF.
- **Mal servido por la educación financiera genérica.** Un curso de finanzas de 6 semanas asume tiempo que este dueño no tiene (la propia investigación de usuario del equipo cuantifica el problema en 12 horas que no existen en su semana).

### 6.2 Por qué el enfoque de "nudge contextual" es defendible frente a "curso genérico"

La literatura de educación financiera para pequeñas empresas (la misma que citan como fuente: FDIC Money Smart, SBA, CFPB, Operation HOPE, Accion Opportunity Fund) documenta consistentemente que la transferencia de conocimiento en aula tiene efectos débiles y de corta duración sobre el comportamiento financiero real, mientras que las intervenciones "just-in-time" — la alerta correcta, en el momento correcto, atada a una decisión que la persona está a punto de tomar — tienen mejor evidencia de cambio de comportamiento. Que el sistema de insights de Capital One Business esté diseñado explícitamente para mostrar **una sola tarjeta, la más relevante, en el momento correcto**, en vez de una biblioteca de lecciones, es coherente con esa evidencia y no es sólo una decisión estética.

### 6.3 Casos de uso concretos que el producto ya cubre (documentados en las demos)

- *"¿Cuántos pasteles de chocolate puedo hacer?"* → el asistente calcula la capacidad de producción real a partir del inventario y de la receta, y dice **qué insumo específico** es el cuello de botella. Esto reemplaza un cálculo mental que un dueño sin Excel simplemente no hace, y evita tanto la sobreventa (prometer algo que no se puede entregar) como la sub-venta (no ofrecer algo que sí se podría).
- *"¿Por qué bajó mi utilidad este mes?"* → el motor de `profit_drivers` descompone la caída en ventas, costo de insumos y gastos operativos, identificando el factor de mayor impacto y el producto específico que más cambió. Es, en esencia, un análisis de variancia contable que normalmente requiere un CFO, entregado como una frase.
- *"¿Cuándo se me acaba el tinte?"* seguido de *"¿y el esmalte?"* → proyección de agotamiento de inventario basada en el consumo real de los últimos 30 días, no en un umbral fijo adivinado.
- La reclasificación de una compra ("Amazon $129.99" → "Equipo o herramienta") que la app **recuerda** para la siguiente compra en el mismo comercio — reduce la fricción de mantener los libros limpios sin que el dueño entienda qué es una "cuenta contable".

### 6.4 Riesgos que vale la pena nombrar, no esconder

- **Dependencia de una API externa frágil.** El propio README documenta que Nessie se cayó a media competencia en HackMTY 2025. La mitigación (cliente mock intercambiable) es buena ingeniería, pero para un producto real más allá del hackathon, Nessie es un sandbox de prueba, no un proveedor de datos bancarios en producción — el camino a un negocio real necesita un proveedor tipo Plaid/Finicity o una relación directa con el core bancario de Capital One.
- **El benchmark cross-negocio, si crece, necesita gobernanza de datos explícita.** El umbral de cohorte mínima de 5 es un buen primer paso, pero un producto real que agrega datos financieros de negocios (aunque sea agregados) necesita una política de privacidad clara y, probablemente, consentimiento explícito de opt-in para el benchmarking — algo que vale la pena anticipar en el roadmap, no sólo en el código.
- **El asistente sin memoria de conversación es una decisión de producto correcta para evitar alucinaciones, pero tiene un costo de UX real** — el propio equipo lo documenta: "¿y el mes pasado?" no funciona, hay que preguntar completo. Es el trade-off correcto por ahora (se construyó memoria de sesión y se retiró a propósito), pero es una limitación de experiencia que un usuario real notará rápido si el producto crece.
- **La simplificación de una sola moneda (todo formateado como "$")** funciona para la demo (dólares y pesos mexicanos comparten el símbolo) pero no escala a un producto multi-país real sin trabajo adicional de internacionalización.

---

## 7. Panorama competitivo

| Categoría | Jugadores | Cómo se posiciona Capital One Business frente a ellos |
|---|---|---|
| Neobancos SMB en EE.UU. | Novo, Lili, Found, Relay | Estos resuelven "cuenta bancaria sin comisiones + categorización básica de gastos". Ninguno construye un motor de partida doble completo con estados financieros derivados y un asistente que explica razones financieras — se quedan en "aquí está tu gasto categorizado", no en "así está tu capital de trabajo y por qué". |
| Banca SMB de gama alta | Mercury, Brex, Ramp | Excelente producto, pero diseñado y vendido a startups con soporte de VC y equipos de finanzas — el segmento de 1 a 5 personas sin financiamiento externo no es su cliente objetivo ni su modelo de ventas. |
| Fintech SMB en LatAm | Clara, Fondeadora, Klar Empresas, tarjetas corporativas de bancos tradicionales | Fuertes en tarjeta corporativa + control de gasto para empresas ya formalizadas con varios empleados; el micro-negocio de 1 a 2 personas informal sigue mal atendido por este segmento, que apunta más arriba en tamaño de empresa. |
| Herramientas de contabilidad para pequeño negocio | QuickBooks Self-Employed, Wave, Fetch/Bench | Contabilidad real, pero requieren que el usuario entienda o al menos tolere el vocabulario contable, y no tienen un asistente conversacional que traduzca activamente razones financieras a lenguaje llano ni una capa de "un solo insight relevante ahora". |
| POS con reportes | Square, Clover, Toast | Resuelven el cobro y dan reportes de ventas; ninguno hace contabilidad de partida doble completa (balance, estados financieros con integridad verificada) ni conecta el lado de "gasto con tarjeta" al mismo libro que el lado de "venta". |

**El espacio en blanco real:** nadie en esta lista combina (a) un motor contable completo y correcto, (b) alimentado automáticamente por ambos lados de la actividad del negocio (venta y compra, no sólo una), (c) traducido a lenguaje natural con guardias anti-alucinación, y (d) dirigido explícitamente al negocio de 1 a 5 personas sin capacidad de pagar un contador. Ese es el argumento de posicionamiento más fuerte que el equipo tiene, y curiosamente no está tan explícito en el pitch actual como podría estarlo.

---

## 8. Estado real del proyecto — la fotografía honesta

A partir de `docs/PROJECT_STATUS.md` (con la advertencia del propio equipo de "verifiquen contra el repo real, porque varias piezas las construyó cada quien por su lado"):

**Terminado y probado:** backend FastAPI con CI en verde; integración Nessie real + mock; encuesta de onboarding completa; diseño visual de marca; arquitectura de almacenamiento intercambiable; contenido de educación financiera investigado y escrito (11 triggers); pantalla principal post-encuesta construida. Y, según documentos fechados después (`FINANCIAL_CORE.md`, `DEMO.md`, ambos 2026-09-13): el núcleo financiero completo (contabilidad, inventario, ventas por QR, compras con tarjeta, análisis, asistente híbrido), verificado "de punta a punta contra Snowflake real", con dos demos completas y 119+29 tests.

**A medias, según el mismo documento:** la conexión entre lo que responde la encuesta (`category`, `answers`) y la pantalla principal (`Cuenta.tsx`), que bloqueaba el componente `CashInsightCard` — se estaba resolviendo en la rama `feature/financial-literacy`.

**No empezado, según el mismo documento:** deploy en Vultr (para el prize específico de MLH; Render sí está configurado como alternativa), un proveedor de pagos real más allá del proveedor demo, y OCR real de tickets de compra (hoy son tickets de muestra).

**Mi lectura:** hay una tensión visible entre `PROJECT_STATUS.md` (que describe piezas de UX a medias) y los documentos posteriores del núcleo financiero (que describen un sistema mucho más completo y probado). Esto es normal en el desarrollo acelerado de un hackathon con múltiples agentes de IA trabajando en paralelo (el propio Devpost lo dice: *"Multi-agent parallel development (Claude, OpenAI, Gemini) coordinado vía archivos SKILL.md compartidos"*), pero significa que, antes de repetir cualquier cifra o afirmación de este documento frente a un jurado, vale la pena una verificación rápida de 15 minutos contra el estado real del deploy en `capitalonebusiness.tech`: ¿la pantalla de Cuenta ya muestra el Cash Insight correcto según la categoría del negocio? ¿el flujo de "Snowflake real" corrió alguna vez contra una cuenta que no sea la de pruebas?

---

## 9. Recomendaciones concretas

1. **Cerrar el modelo de negocio en una diapositiva propia.** Con el mercado tan bien argumentado, falta el "cómo ganamos dinero": suscripción mensual baja ($X/mes, comparable a lo que hoy cuesta nada porque nadie lo está pagando), comisión por transacción de la tarjeta de negocio (alineado con el propio incentivo de Capital One), o el benchmarking sectorial como producto premium.
2. **Convertir la guardia anti-alucinación en un argumento de pitch explícito**, con esa frase o una similar a la de la sección 4.2 — es, de las decisiones técnicas del proyecto, la que más se presta a un "momento wow" verbal frente a jueces que entienden de riesgo financiero.
3. **Verificar en vivo, antes de presentar, que la pieza documentada como "a medias" (encuesta → Cash Insight en Cuenta.tsx) ya funciona** — es el hueco más visible entre arquitectura y demo.
4. **Tener a la mano la fuente exacta de "$1.7 billones"** y del "64%" de nonemployer firms (Fed Small Business Credit Survey), por si un juez pide la referencia — ambas cifras direccionalmente correctas, pero conviene poder citarlas con precisión.
5. **Adelantar, aunque sea como mockup, el benchmarking cross-negocio** (sección 4.4) en la demo — es la pieza que mejor conecta "usamos Snowflake de verdad" con "esto es un producto de datos, no sólo una app".
6. **Para una siguiente iteración post-hackathon:** sustituir Nessie por una integración real (Plaid/Finicity o el core de Capital One) es el paso obligado para que el producto deje de ser una demo y empiece a ser un negocio; y valdría la pena decidir explícitamente el trade-off de volver a dar memoria de sesión al asistente (mejor UX conversacional) sólo si se puede mantener la misma guardia de montos sobre una conversación completa, no sólo sobre un turno.

---

## 10. Conclusión

Capital One Business toma un problema real y bien cuantificado — la inmensa mayoría de los negocios en México, Estados Unidos y América Latina son microempresas sin tiempo ni formación para llevar sus finanzas — y lo resuelve con una pieza de ingeniería genuinamente seria: un motor contable de partida doble correcto y probado, alimentado automáticamente por ambos lados de la actividad del negocio, con Snowflake como base de datos autoritativa (usada con criterio: `MERGE` para consistencia real, `VARIANT`/`FLATTEN` para analítica agregada con privacidad, Cortex como LLM sin salir del perímetro de datos) y un asistente conversacional cuya decisión de diseño más importante — dejar que el motor calcule y que la IA sólo redacte, con una guardia de código que descarta cualquier cifra inventada — es más madura que la de la mayoría de los proyectos que sí se llaman a sí mismos "RAG".

El mayor riesgo del proyecto no es técnico: es que el pitch todavía no ha absorbido del todo lo bueno que ya construyeron. La complejidad técnica y el rigor de la capa de datos están, con margen, por encima de lo que exige la rúbrica; lo que falta es contar esa historia con la misma precisión con la que está escrito el código.
