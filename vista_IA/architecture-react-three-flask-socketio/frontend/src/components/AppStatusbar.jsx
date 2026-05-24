export default function AppStatusbar({ graph, mapTool, flowTool }) {
  return (
    <footer className="statusbar">
      <span>Bloques: {graph.nodes.length}</span>
      <span>Conexiones: {graph.edges.length}</span>
      <span>Aislados: {graph.metadata?.isolatedCount ?? 0}</span>
      <span>Modo mapa: {mapTool}</span>
      <span>Modo flujo: {flowTool}</span>
    </footer>
  );
}
