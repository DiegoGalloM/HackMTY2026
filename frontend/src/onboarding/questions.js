// frontend/src/onboarding/questions.js
export const CATEGORIES = [
  { id: "comida", label: "Comida y bebidas", icon: "🍔" },
  { id: "retail", label: "Tienda / Retail", icon: "🛍️" },
  { id: "servicios", label: "Servicios", icon: "🧰" },
  { id: "belleza", label: "Belleza y cuidado personal", icon: "💇" },
  { id: "construccion", label: "Construcción / Oficios", icon: "🔨" },
  { id: "transporte", label: "Transporte / Delivery", icon: "🚗" },
  { id: "otro", label: "Otro", icon: "✨" },
];

export const UNIVERSAL_QUESTIONS = [
  { id: "vende_producto_fisico", text: "¿Vendes productos físicos que compras o preparas para revender?" },
  { id: "guarda_inventario", text: "¿Guardas mercancía o materiales en algún lugar?" },
  { id: "compra_mayoreo", text: "¿Compras tus productos o materiales a un proveedor mayorista?" },
  { id: "se_ha_quedado_sin_stock", text: "¿Alguna vez se te ha acabado algo que necesitabas vender?" },
  { id: "compro_de_mas", text: "¿Alguna vez has comprado de más y se te ha echado a perder o no se ha vendido?" },
  { id: "vende_en_local_fijo", text: "¿Vendes en un local fijo?" },
];

export const CATEGORY_QUESTIONS = {
  comida: [
    { id: "ingredientes_perecederos", text: "¿Usas ingredientes perecederos (frutas, verduras, carnes, lácteos)?" },
    { id: "vende_bebidas", text: "¿Vendes bebidas preparadas o embotelladas?" },
    { id: "prepara_en_sitio", text: "¿Preparas la comida en el mismo lugar donde vendes?" },
  ],
  retail: [
    { id: "muchos_productos", text: "¿Manejas más de 20 productos distintos?" },
    { id: "productos_temporada", text: "¿Algunos productos son de temporada?" },
    { id: "revende_sin_transformar", text: "¿Revendes tal como compras, sin transformar?" },
  ],
  servicios: [
    { id: "usa_insumos", text: "¿Usas insumos que se gastan en cada servicio?" },
    { id: "cobra_por_hora", text: "¿Cobras por hora/visita más que por producto?" },
  ],
  belleza: [
    { id: "usa_insumos_belleza", text: "¿Usas productos que se consumen por servicio (tintes, cremas)?" },
    { id: "vende_retail", text: "¿Además de servicios, vendes producto al público?" },
  ],
  construccion: [
    { id: "material_por_proyecto", text: "¿Compras material específico para cada proyecto?" },
    { id: "herramienta_propia", text: "¿Usas herramienta propia ya comprada, no por trabajo?" },
  ],
  transporte: [
    { id: "vehiculo_propio", text: "¿Usas tu propio vehículo para el negocio?" },
    { id: "gasto_combustible", text: "¿Tu gasto principal es gasolina/mantenimiento?" },
  ],
  otro: [],
};

export const WEEKDAYS = [
  { id: "mon", label: "L" }, { id: "tue", label: "M" }, { id: "wed", label: "M" },
  { id: "thu", label: "J" }, { id: "fri", label: "V" }, { id: "sat", label: "S" }, { id: "sun", label: "D" },
];

export const EMPLOYEE_OPTIONS = [
  { id: "1", label: "Solo yo" }, { id: "2", label: "2" }, { id: "3-5", label: "3 a 5" },
];