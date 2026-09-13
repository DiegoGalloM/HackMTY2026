import Screen from "../components/Screen";

/**
 * Tarjetas del análisis. Por ahora son placeholders con el mismo look que el
 * grid de accesos rápidos; cuando haya datos reales, cada una se reemplaza
 * por su gráfica/indicador sin tocar el layout.
 */
const panels = [
  { id: "Diario", label: "Diario" },
  { id: "Balance General", label: "Balance General" },
  { id: "Resultados", label: "Resultados" },
];

export default function Analisis() {
  return (
    <Screen title="Análisis Financiero">
      <div className="space-y-5 px-5">
        {panels.map((panel) => (
          <section
            key={panel.id}
            className="h-36 rounded-2xl bg-tile p-4 shadow-sm"
          >
            <p className="text-base">{panel.label}</p>
          </section>
        ))}
      </div>
    </Screen>
  );
}
