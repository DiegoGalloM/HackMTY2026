"""
Núcleo financiero de Capital One Business.

    evento de negocio  ->  inventario / contabilidad  ->  diario  ->  mayor
    -> balanza -> estados financieros -> razones -> asistente

Módulos:
  common      dinero (Decimal), ids, reloj
  coa         plantillas del catálogo de cuentas por tipo de negocio
  repo        acceso a tablas, siempre acotado a un business_id
  accounting  partida doble: asientos, mayor, balanza, estados financieros
  inventory   existencias con costo promedio ponderado y bitácora de movimientos
  catalog     productos/servicios vendibles y su receta (BOM)
  sales       órdenes, QR (token opaco) y la tubería de venta pagada
  payments    proveedor de pagos (demo) que emite el evento autoritativo
  purchases   transacciones de la tarjeta: proveedor, normalización, clasificación
  analytics   razones financieras, salud de caja, tendencias, insights
  assistant   asistente híbrido: intención -> herramientas -> explicación
  demo        negocio de ejemplo coherente (panadería)
"""
