// frontend/src/financial-literacy/insights.js
export const TRIGGERS = [
  {
    id: "stockout_y_sobrecompra",
    match: (p) => p.answers?.se_ha_quedado_sin_stock && p.answers?.compro_de_mas,
    title: "No necesitas más inventario; necesitas mejor inventario",
    body: "Que se te acabe algo Y te sobre otra cosa al mismo tiempo no es falta de dinero para comprar — es que estás comprando lo que no se vende y poco de lo que sí. El problema es de mezcla, no de cantidad.",
    action: "Separar lo que se vende rápido de lo que no",
  },
  {
    id: "stockout",
    match: (p) => p.answers?.se_ha_quedado_sin_stock,
    title: "Cuándo volver a pedir",
    body: "Que se te acabe algo que sí vendes es dinero que dejaste de ganar. La regla simple: vuelve a pedir cuando lo que te queda alcance para cubrir tu demanda promedio mientras llega el nuevo pedido, más un colchón pequeño por si tarda más de lo normal.",
    action: "Calcular mi punto de reorden",
  },
  {
    id: "sobrecompra",
    match: (p) => p.answers?.compro_de_mas,
    title: "Tu efectivo también se queda atrapado en una caja",
    body: "Comprar de más no es un gasto que desaparece — es dinero que ahora está guardado en producto, no en tu bolsillo. Si algo lleva semanas sin moverse, ese dinero está congelado, no perdido, pero tampoco lo puedes usar.",
    action: "Ver qué se está moviendo lento",
  },
  {
    id: "guarda_inventario",
    match: (p) => p.answers?.guarda_inventario,
    title: "¿Cuánto cash tienes sentado en inventario?",
    body: "Todo lo que tienes guardado sin vender es dinero que ya gastaste pero que aún no regresa a tu bolsillo. Vale la pena tener una idea de cuánto vale ese inventario y cuánto tarda normalmente en venderse.",
    action: "Ver el valor de mi inventario",
  },
  {
    id: "compra_mayoreo",
    match: (p) => p.answers?.compra_mayoreo,
    title: "¿El descuento al mayoreo realmente te ahorra dinero?",
    body: "Comprar más barato por unidad suena bien, pero si ese pedido grande te deja sin efectivo por semanas, el 'ahorro' puede costarte más caro que comprar en cantidades más chicas y seguido.",
    action: "Comparar mi ahorro real",
  },
  {
    id: "categoria_comida",
    match: (p) => p.category === "comida",
    title: "¿Cuánto ganas realmente por cada platillo?",
    body: "Vender mucho no siempre significa ganar mucho. Resta el costo de tus ingredientes y empaque al precio de venta — ese es tu margen real por producto, y a veces sorprende.",
    action: "Calcular mi margen por platillo",
  },
  {
    id: "categoria_retail",
    match: (p) => p.category === "retail",
    title: "Margen × qué tan rápido se vende",
    body: "No basta con ganar bien por producto si ese producto tarda meses en venderse. Un margen más chico que rota rápido casi siempre te deja más dinero en la mano que uno grande que se queda en el estante.",
    action: "Ver qué tan rápido rota mi inventario",
  },
  {
    id: "categoria_servicios",
    match: (p) => p.category === "servicios",
    title: "Una venta no es dinero hasta que te pagan",
    body: "Si cobras después de trabajar, ese trabajo ya hecho es dinero que todavía no tienes. Pedir un anticipo o cobrar más seguido cambia mucho tu flujo de efectivo, aunque factures lo mismo al mes.",
    action: "Revisar cómo y cuándo cobro",
  },
  {
    id: "categoria_construccion",
    match: (p) => p.category === "construccion",
    title: "No financies tú el proyecto de tu cliente",
    body: "Comprar materiales antes de que te paguen es prestarle dinero a tu cliente sin querer. Pedir un anticipo para materiales y cobrar por avances te protege de quedarte sin efectivo a mitad de obra.",
    action: "Ver cómo estructurar mis cobros",
  },
  {
    id: "categoria_transporte",
    match: (p) => p.category === "transporte",
    title: "Cada kilómetro tiene un costo que no ves hoy",
    body: "La gasolina se nota, pero el mantenimiento y las reparaciones futuras también son parte del costo de cada viaje — solo que llegan después. Apartar un poco por kilómetro te evita un shock cuando el vehículo falle.",
    action: "Calcular mi costo por kilómetro",
  },
  {
    id: "categoria_belleza",
    match: (p) => p.category === "belleza",
    title: "¿Cuánto te deja realmente una cita?",
    body: "Al precio del servicio réstale los productos que usaste y el tiempo que te tomó. Dos servicios del mismo precio pueden dejarte ganancias muy distintas si uno usa más producto o toma más tiempo.",
    action: "Calcular mi ganancia por servicio",
  },
];

// Triggers de la encuesta que tratan el MISMO tema que un insight de datos del
// backend (GET /analytics/insights). Si ese insight ya está en pantalla, repetir
// la lección de la encuesta sería mostrar dos veces la misma idea.
const COVERED_BY_DATA = {
  data_stockout: ["stockout_y_sobrecompra", "stockout"],
  data_overstock: ["stockout_y_sobrecompra", "sobrecompra", "guarda_inventario"],
  data_low_margin: ["categoria_comida", "categoria_retail", "categoria_belleza"],
};

/**
 * La lección que dispara SÓLO la encuesta (categoría + respuestas), saltando
 * los temas que ya cubren los insights de datos que se muestran.
 *
 * @param {any} profile
 * @param {Array<{ id: string }>} [dataInsights]
 */
export function pickSurveyTrigger(profile, dataInsights = []) {
  if (!profile) return null;
  const covered = new Set(dataInsights.flatMap((insight) => COVERED_BY_DATA[insight.id] ?? []));
  const trigger = TRIGGERS.find((t) => !covered.has(t.id) && t.match(profile));
  return trigger ? { ...trigger, source: "survey" } : null;
}

/**
 * UNA sola lección para Cuenta. Un trigger de datos reales tiene prioridad
 * sobre uno de sólo-encuesta: lo que el negocio está viviendo (se le acaba un
 * insumo, la caja no alcanza) pesa más que lo que respondió al registrarse.
 * Sin datos todavía (cuenta nueva, backend caído), decide la encuesta.
 *
 * @param {any} profile
 * @param {Array<{ id: string }>} [dataInsights]
 */
export function pickBestTrigger(profile, dataInsights = []) {
  if (dataInsights.length > 0) return { ...dataInsights[0], source: "data" };
  return pickSurveyTrigger(profile);
}