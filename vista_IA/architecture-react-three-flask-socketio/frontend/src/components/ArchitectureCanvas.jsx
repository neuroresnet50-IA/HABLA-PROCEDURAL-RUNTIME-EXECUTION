import { useEffect, useMemo, useRef, useState } from "react";

const NODE_WIDTH = 254;
const NODE_HEIGHT = 118;
const MIN_SCALE = 0.22;
const MAX_SCALE = 1.8;

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function getNodeColor(node) {
  return node.color || "#60a5fa";
}

function getNodeRect(node) {
  const x = Number(node.position?.x) || 0;
  const y = Number(node.position?.y) || 0;
  return {
    x,
    y,
    left: x - NODE_WIDTH / 2,
    top: y - NODE_HEIGHT / 2,
    right: x + NODE_WIDTH / 2,
    bottom: y + NODE_HEIGHT / 2,
  };
}

function getAnchor(rect, direction) {
  if (direction === "left") return { x: rect.left, y: rect.y };
  if (direction === "right") return { x: rect.right, y: rect.y };
  if (direction === "top") return { x: rect.x, y: rect.top };
  return { x: rect.x, y: rect.bottom };
}

function chooseDirection(sourceRect, targetRect) {
  const dx = targetRect.x - sourceRect.x;
  const dy = targetRect.y - sourceRect.y;

  if (Math.abs(dx) > Math.abs(dy)) {
    return dx >= 0
      ? { from: "right", to: "left" }
      : { from: "left", to: "right" };
  }

  return dy >= 0
    ? { from: "bottom", to: "top" }
    : { from: "top", to: "bottom" };
}

function buildEdgePath(sourceNode, targetNode) {
  const sourceRect = getNodeRect(sourceNode);
  const targetRect = getNodeRect(targetNode);
  const directions = chooseDirection(sourceRect, targetRect);
  const source = getAnchor(sourceRect, directions.from);
  const target = getAnchor(targetRect, directions.to);
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const bend = Math.max(96, Math.min(220, Math.abs(dx) * 0.35 + Math.abs(dy) * 0.2));

  let c1 = { x: source.x, y: source.y };
  let c2 = { x: target.x, y: target.y };

  if (directions.from === "right") {
    c1 = { x: source.x + bend, y: source.y };
    c2 = { x: target.x - bend, y: target.y };
  } else if (directions.from === "left") {
    c1 = { x: source.x - bend, y: source.y };
    c2 = { x: target.x + bend, y: target.y };
  } else if (directions.from === "bottom") {
    c1 = { x: source.x, y: source.y + bend };
    c2 = { x: target.x, y: target.y - bend };
  } else {
    c1 = { x: source.x, y: source.y - bend };
    c2 = { x: target.x, y: target.y + bend };
  }

  return {
    path: `M ${source.x} ${source.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${target.x} ${target.y}`,
    labelX: (source.x + target.x) * 0.5,
    labelY: (source.y + target.y) * 0.5 - 14,
  };
}

function getBounds(nodes) {
  if (!nodes.length) {
    return { minX: 0, minY: 0, width: 1800, height: 1200 };
  }

  const rects = nodes.map(getNodeRect);
  const minX = Math.min(...rects.map((rect) => rect.left)) - 260;
  const maxX = Math.max(...rects.map((rect) => rect.right)) + 260;
  const minY = Math.min(...rects.map((rect) => rect.top)) - 220;
  const maxY = Math.max(...rects.map((rect) => rect.bottom)) + 220;

  return {
    minX,
    minY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

function buildFitViewport(bounds, frameSize) {
  const scale = clamp(
    Math.min(frameSize.width / bounds.width, frameSize.height / bounds.height) * 0.9,
    MIN_SCALE,
    0.78
  );

  return {
    scale,
    x: (frameSize.width - bounds.width * scale) * 0.5 - bounds.minX * scale,
    y: (frameSize.height - bounds.height * scale) * 0.5 - bounds.minY * scale,
  };
}

function toScreenRect(rect, viewport) {
  return {
    left: rect.left * viewport.scale + viewport.x,
    top: rect.top * viewport.scale + viewport.y,
    right: rect.right * viewport.scale + viewport.x,
    bottom: rect.bottom * viewport.scale + viewport.y,
  };
}

function isRectOutsideFrame(rect, frameSize, viewport, margin = 40) {
  const screenRect = toScreenRect(rect, viewport);
  return (
    screenRect.right < margin
    || screenRect.left > frameSize.width - margin
    || screenRect.bottom < margin
    || screenRect.top > frameSize.height - margin
  );
}

function areBoundsOffscreen(bounds, frameSize, viewport) {
  return isRectOutsideFrame(
    {
      left: bounds.minX,
      top: bounds.minY,
      right: bounds.minX + bounds.width,
      bottom: bounds.minY + bounds.height,
    },
    frameSize,
    viewport,
    120
  );
}

function buildNodeFocusViewport(node, frameSize, viewport) {
  const scale = clamp(viewport.scale || 0.6, MIN_SCALE, MAX_SCALE);
  const rect = getNodeRect(node);
  return {
    scale,
    x: frameSize.width * 0.5 - rect.x * scale,
    y: frameSize.height * 0.5 - rect.y * scale,
  };
}

function issueColor(issue) {
  const severity = String(issue?.severity || "").toLowerCase();
  if (severity === "error") return "#ef4444";
  if (severity === "warning") return "#f59e0b";
  return "#38bdf8";
}

function getLayerFrames(nodes, layerOrder) {
  const grouped = new Map();
  for (const node of nodes) {
    const layer = node.layer || "script";
    if (!grouped.has(layer)) grouped.set(layer, []);
    grouped.get(layer).push(node);
  }

  const known = layerOrder.filter((layer) => grouped.has(layer));
  const custom = [...grouped.keys()].filter((layer) => !known.includes(layer)).sort();
  const ordered = [...known, ...custom];

  return ordered.map((layer) => {
    const layerNodes = grouped.get(layer) || [];
    const rects = layerNodes.map(getNodeRect);
    const minX = Math.min(...rects.map((rect) => rect.left)) - 72;
    const maxX = Math.max(...rects.map((rect) => rect.right)) + 72;
    const minY = Math.min(...rects.map((rect) => rect.top)) - 72;
    const maxY = Math.max(...rects.map((rect) => rect.bottom)) + 72;
    return {
      layer,
      label: layerNodes[0]?.layerLabel || layer.replace(/-/g, " ").toUpperCase(),
      color: getNodeColor(layerNodes[0] || { color: "#60a5fa" }),
      left: minX,
      top: minY,
      width: maxX - minX,
      height: maxY - minY,
    };
  });
}

function getSceneFrames(nodes) {
  const grouped = new Map();
  for (const node of nodes) {
    if (!node.workspaceScene) continue;
    if (!grouped.has(node.workspaceScene)) grouped.set(node.workspaceScene, []);
    grouped.get(node.workspaceScene).push(node);
  }

  return [...grouped.entries()].map(([sceneKey, sceneNodes]) => {
    const rects = sceneNodes.map(getNodeRect);
    const minX = Math.min(...rects.map((rect) => rect.left)) - 132;
    const maxX = Math.max(...rects.map((rect) => rect.right)) + 132;
    const minY = Math.min(...rects.map((rect) => rect.top)) - 132;
    const maxY = Math.max(...rects.map((rect) => rect.bottom)) + 132;
    return {
      sceneKey,
      label: sceneNodes[0]?.workspaceSceneLabel || sceneKey,
      color: getNodeColor(sceneNodes[0] || { color: "#60a5fa" }),
      left: minX,
      top: minY,
      width: maxX - minX,
      height: maxY - minY,
    };
  });
}

function toWorldPoint(event, frame, viewport) {
  const rect = frame.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left - viewport.x) / viewport.scale,
    y: (event.clientY - rect.top - viewport.y) / viewport.scale,
  };
}

export default function ArchitectureCanvas({
  graph,
  selectedNodeId,
  selectedEdgeId,
  mapTool,
  edgeType,
  layerOrder,
  nodeIssuesById = {},
  onSelectNode,
  onSelectEdge,
  onAddNode,
  onMoveNode,
  onAddEdge,
  onIssueClick,
}) {
  const frameRef = useRef(null);
  const pointerRef = useRef(null);
  const hasInteractedRef = useRef(false);
  const [frameSize, setFrameSize] = useState({ width: 0, height: 0 });
  const [viewport, setViewport] = useState({ scale: 0.6, x: 0, y: 0 });
  const [pendingConnectionId, setPendingConnectionId] = useState(null);

  const nodeMap = useMemo(() => new Map(graph.nodes.map((node) => [node.id, node])), [graph.nodes]);
  const bounds = useMemo(() => getBounds(graph.nodes), [graph.nodes]);
  const layerFrames = useMemo(() => getLayerFrames(graph.nodes, layerOrder), [graph.nodes, layerOrder]);
  const sceneFrames = useMemo(() => getSceneFrames(graph.nodes), [graph.nodes]);
  const selectedNode = useMemo(
    () => graph.nodes.find((node) => node.id === selectedNodeId) || null,
    [graph.nodes, selectedNodeId]
  );

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return undefined;

    const updateSize = () => {
      setFrameSize({
        width: frame.clientWidth || 0,
        height: frame.clientHeight || 0,
      });
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(frame);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!frameSize.width || !frameSize.height || hasInteractedRef.current) return;
    setViewport(buildFitViewport(bounds, frameSize));
  }, [bounds, frameSize.height, frameSize.width]);

  useEffect(() => {
    if (!frameSize.width || !frameSize.height || !hasInteractedRef.current) return;
    setViewport((current) => (
      areBoundsOffscreen(bounds, frameSize, current)
        ? buildFitViewport(bounds, frameSize)
        : current
    ));
  }, [bounds, frameSize.height, frameSize.width, graph.metadata?.updatedAt]);

  useEffect(() => {
    if (!selectedNode || !frameSize.width || !frameSize.height) return;
    setViewport((current) => (
      isRectOutsideFrame(getNodeRect(selectedNode), frameSize, current, 72)
        ? buildNodeFocusViewport(selectedNode, frameSize, current)
        : current
    ));
  }, [frameSize.height, frameSize.width, graph.metadata?.updatedAt, selectedNode]);

  const handleWheel = (event) => {
    event.preventDefault();
    const frame = frameRef.current;
    if (!frame) return;
    hasInteractedRef.current = true;

    const rect = frame.getBoundingClientRect();
    const pointerX = event.clientX - rect.left;
    const pointerY = event.clientY - rect.top;
    const factor = event.deltaY > 0 ? 0.92 : 1.08;

    setViewport((current) => {
      const nextScale = clamp(current.scale * factor, MIN_SCALE, MAX_SCALE);
      const worldX = (pointerX - current.x) / current.scale;
      const worldY = (pointerY - current.y) / current.scale;
      return {
        scale: nextScale,
        x: pointerX - worldX * nextScale,
        y: pointerY - worldY * nextScale,
      };
    });
  };

  const handleBackgroundPointerDown = (event) => {
    const frame = frameRef.current;
    if (!frame || event.button !== 0) return;

    if (mapTool === "add-node") {
      const world = toWorldPoint(event, frame, viewport);
      onAddNode(world);
      setPendingConnectionId(null);
      return;
    }

    if (mapTool === "connect") {
      setPendingConnectionId(null);
      return;
    }

    hasInteractedRef.current = true;
    pointerRef.current = {
      mode: "pan",
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      originX: viewport.x,
      originY: viewport.y,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handleNodePointerDown = (event, node) => {
    event.stopPropagation();
    const frame = frameRef.current;
    if (!frame) return;

    if (mapTool === "connect") {
      if (!pendingConnectionId) {
        setPendingConnectionId(node.id);
        onSelectNode(node.id);
        return;
      }

      if (pendingConnectionId !== node.id) {
        onAddEdge(pendingConnectionId, node.id, edgeType);
      }
      setPendingConnectionId(null);
      return;
    }

    if (mapTool === "add-node") return;

    hasInteractedRef.current = true;
    pointerRef.current = {
      mode: "move-node",
      pointerId: event.pointerId,
      nodeId: node.id,
      startClientX: event.clientX,
      startClientY: event.clientY,
      originX: Number(node.position?.x) || 0,
      originY: Number(node.position?.y) || 0,
    };
    onSelectNode(node.id);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event) => {
    const current = pointerRef.current;
    if (!current || current.pointerId !== event.pointerId) return;

    const deltaX = (event.clientX - current.startClientX) / viewport.scale;
    const deltaY = (event.clientY - current.startClientY) / viewport.scale;

    if (current.mode === "pan") {
      setViewport((viewportState) => ({
        ...viewportState,
        x: current.originX + event.clientX - current.startClientX,
        y: current.originY + event.clientY - current.startClientY,
      }));
      return;
    }

    if (current.mode === "move-node") {
      onMoveNode(current.nodeId, {
        x: current.originX + deltaX,
        y: current.originY + deltaY,
      });
    }
  };

  const handlePointerUp = (event) => {
    const current = pointerRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    pointerRef.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  };

  const edgeMarkerId = "architecture-arrow";
  const svgViewBox = `0 0 ${Math.max(1, frameSize.width || 1)} ${Math.max(1, frameSize.height || 1)}`;

  return (
    <div className="architecture-stage">
      <div className="architecture-hint">
        {mapTool === "add-node" && "Click en el lienzo para crear un bloque nuevo."}
        {mapTool === "connect" && (pendingConnectionId ? "Selecciona el bloque destino." : "Selecciona origen y destino para crear la flecha.")}
        {mapTool === "select" && "Arrastra bloques para reordenar. Arrastra el fondo para mover el mapa. Rueda para zoom."}
      </div>

      <div
        className="architecture-canvas"
        ref={frameRef}
        onWheel={handleWheel}
        onPointerDown={handleBackgroundPointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        <svg
          className="architecture-svg"
          viewBox={svgViewBox}
          preserveAspectRatio="none"
        >
          <defs>
            <pattern id="architecture-grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(77, 94, 120, 0.18)" strokeWidth="1" />
            </pattern>
            <marker id={edgeMarkerId} markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
              <path d="M 0 0 L 12 6 L 0 12 z" fill="#98a8c6" />
            </marker>
          </defs>

          <rect x="0" y="0" width={Math.max(1, frameSize.width || 1)} height={Math.max(1, frameSize.height || 1)} fill="#07101c" />

          <g transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`}>
            <rect x={bounds.minX} y={bounds.minY} width={bounds.width} height={bounds.height} fill="#07101c" />
            <rect x={bounds.minX} y={bounds.minY} width={bounds.width} height={bounds.height} fill="url(#architecture-grid)" />

            {sceneFrames.map((frame) => (
              <g key={frame.sceneKey}>
                <rect
                  x={frame.left}
                  y={frame.top}
                  width={frame.width}
                  height={frame.height}
                  rx="42"
                  fill={`${frame.color}08`}
                  stroke={`${frame.color}66`}
                  strokeWidth="2"
                  strokeDasharray="18 10"
                />
                <text x={frame.left + 18} y={frame.top + 28} className="architecture-scene-label">
                  {frame.label}
                </text>
              </g>
            ))}

            {layerFrames.map((frame) => (
              <g key={frame.layer}>
                <rect
                  x={frame.left}
                  y={frame.top}
                  width={frame.width}
                  height={frame.height}
                  rx="28"
                  fill={`${frame.color}10`}
                  stroke={frame.color}
                  strokeWidth="2"
                  strokeDasharray="10 8"
                />
                <text x={frame.left + frame.width / 2} y={frame.top - 18} textAnchor="middle" className="architecture-layer-label">
                  {String(frame.label).toUpperCase()}
                </text>
              </g>
            ))}

            {graph.edges.map((edge) => {
            const sourceNode = nodeMap.get(edge.from);
            const targetNode = nodeMap.get(edge.to);
            if (!sourceNode || !targetNode) return null;
            const geometry = buildEdgePath(sourceNode, targetNode);
            const isSelected = edge.id === selectedEdgeId;
            return (
              <g key={edge.id} onClick={(event) => {
                event.stopPropagation();
                onSelectEdge(edge.id);
              }}>
                <path
                  d={geometry.path}
                  fill="none"
                  stroke={isSelected ? "#f8fafc" : "#98a8c6"}
                  strokeWidth={isSelected ? 4 : 3}
                  strokeDasharray={edge.dashed ? "10 8" : undefined}
                  markerEnd={`url(#${edgeMarkerId})`}
                />
                <text x={geometry.labelX} y={geometry.labelY} textAnchor="middle" className="architecture-edge-label">
                  {edge.label}
                </text>
              </g>
            );
            })}

            {graph.nodes.map((node) => {
            const rect = getNodeRect(node);
            const isSelected = node.id === selectedNodeId;
            const isPending = node.id === pendingConnectionId;
            const color = getNodeColor(node);
            const normalizedStatus = String(node.status || "generated").toLowerCase();
            const issue = nodeIssuesById[node.id];
            const issueDotColor = issueColor(issue);
            return (
              <g
                key={node.id}
                className={`architecture-node is-${normalizedStatus}`}
                transform={`translate(${rect.left} ${rect.top})`}
                onPointerDown={(event) => handleNodePointerDown(event, node)}
              >
                <rect
                  width={NODE_WIDTH}
                  height={NODE_HEIGHT}
                  rx="22"
                  fill="#08111e"
                  stroke={isPending ? "#f8fafc" : color}
                  strokeWidth={isSelected || isPending ? 4 : 2.5}
                />
                <rect x="16" y="16" width="54" height="28" rx="8" fill={`${color}33`} stroke={`${color}aa`} />
                <text x="43" y="35" textAnchor="middle" className="architecture-badge">
                  {(node.codeLanguage || node.name.split(".").at(-1) || "FILE").slice(0, 4).toUpperCase()}
                </text>
                <text x="86" y="34" className="architecture-node-title">
                  {node.name}
                </text>
                <text x="24" y="62" className="architecture-node-path">
                  {node.path}
                </text>
                <text x="24" y="86" className="architecture-node-status" fill={color}>
                  {node.layerLabel || node.layer}
                </text>
                <text x="24" y="103" className="architecture-node-meta">
                  {node.status} · {node.lines} lineas
                </text>
                {issue ? (
                  <g
                    className="issue-pulse issue-hotspot"
                    role="button"
                    tabIndex="0"
                    onPointerDown={(event) => event.stopPropagation()}
                    onClick={(event) => {
                      event.stopPropagation();
                      onIssueClick?.(issue, { node });
                    }}
                  >
                    <circle cx={NODE_WIDTH - 22} cy={22} r="11" fill={issueDotColor} opacity="0.28" />
                    <circle cx={NODE_WIDTH - 22} cy={22} r="7" fill={issueDotColor} />
                    <text x={NODE_WIDTH - 22} y={27} textAnchor="middle" className="architecture-issue-count">
                      {issue.count > 9 ? "9+" : issue.count}
                    </text>
                  </g>
                ) : null}
              </g>
            );
            })}
          </g>
        </svg>
      </div>
    </div>
  );
}
