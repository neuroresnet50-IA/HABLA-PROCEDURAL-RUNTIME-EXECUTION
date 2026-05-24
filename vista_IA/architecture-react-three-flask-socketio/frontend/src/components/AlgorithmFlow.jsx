import { useEffect, useMemo, useRef, useState } from "react";

const SHAPE_SIZES = {
  start: { width: 150, height: 56 },
  end: { width: 150, height: 56 },
  process: { width: 220, height: 82 },
  decision: { width: 166, height: 166 },
  io: { width: 212, height: 82 },
};

const MIN_SCALE = 0.22;
const MAX_SCALE = 2.8;
const SEQUENCE_GAP = 280;
const SEQUENCE_TOP = 180;
const SEQUENCE_HEADER_HEIGHT = 86;

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function getShapeSize(type) {
  return SHAPE_SIZES[type] || SHAPE_SIZES.process;
}

function getNodeBox(step) {
  const { width, height } = getShapeSize(step.type);
  return {
    left: step.x - width / 2,
    right: step.x + width / 2,
    top: step.y - height / 2,
    bottom: step.y + height / 2,
    width,
    height,
  };
}

function getAnchor(step, direction) {
  const box = getNodeBox(step);
  if (direction === "top") return { x: step.x, y: box.top };
  if (direction === "bottom") return { x: step.x, y: box.bottom };
  if (direction === "left") return { x: box.left, y: step.y };
  return { x: box.right, y: step.y };
}

function buildPath(source, target) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;

  if (Math.abs(dx) > Math.abs(dy)) {
    const midX = source.x + dx / 2;
    return {
      path: `M ${source.x} ${source.y} C ${midX} ${source.y}, ${midX} ${target.y}, ${target.x} ${target.y}`,
      labelX: midX,
      labelY: (source.y + target.y) / 2 - 14,
    };
  }

  const midY = source.y + dy / 2;
  return {
    path: `M ${source.x} ${source.y} C ${source.x} ${midY}, ${target.x} ${midY}, ${target.x} ${target.y}`,
    labelX: (source.x + target.x) / 2,
    labelY: midY - 14,
  };
}

function getEdgeGeometry(fromStep, toStep) {
  const dx = toStep.x - fromStep.x;
  const dy = toStep.y - fromStep.y;

  if (Math.abs(dx) > Math.abs(dy)) {
    const source = getAnchor(fromStep, dx > 0 ? "right" : "left");
    const target = getAnchor(toStep, dx > 0 ? "left" : "right");
    return buildPath(source, target);
  }

  const source = getAnchor(fromStep, dy > 0 ? "bottom" : "top");
  const target = getAnchor(toStep, dy > 0 ? "top" : "bottom");
  return buildPath(source, target);
}

function toWorldPoint(event, frame, viewport) {
  const rect = frame.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left - viewport.x) / viewport.scale,
    y: (event.clientY - rect.top - viewport.y) / viewport.scale,
  };
}

function getBounds(steps) {
  if (!steps.length) {
    return { minX: 0, minY: 0, width: 900, height: 900 };
  }

  const boxes = steps.map(getNodeBox);
  const minX = Math.min(...boxes.map((box) => box.left)) - 120;
  const maxX = Math.max(...boxes.map((box) => box.right)) + 120;
  const minY = Math.min(...boxes.map((box) => box.top)) - 120;
  const maxY = Math.max(...boxes.map((box) => box.bottom)) + 120;
  return {
    minX,
    minY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

function renderShape(step, isSelected, isPending) {
  const box = getNodeBox(step);
  const fill = step.color || (step.type === "decision" ? "#bfe7f2" : step.type === "start" || step.type === "end" ? "#74c89a" : "#ccf7cf");
  const stroke = isPending ? "#111" : isSelected ? "#0f172a" : step.color || (step.type === "decision" ? "#8fc9d8" : "#8dcf95");
  const commonProps = { fill, stroke, strokeWidth: isSelected || isPending ? 4 : 2.2 };

  if (step.type === "start" || step.type === "end") {
    return <rect x={box.left} y={box.top} width={box.width} height={box.height} rx={box.height / 2} ry={box.height / 2} {...commonProps} />;
  }

  if (step.type === "decision") {
    const points = [
      `${step.x},${box.top}`,
      `${box.right},${step.y}`,
      `${step.x},${box.bottom}`,
      `${box.left},${step.y}`,
    ].join(" ");
    return <polygon points={points} {...commonProps} />;
  }

  if (step.type === "io") {
    const skew = 18;
    const points = [
      `${box.left + skew},${box.top}`,
      `${box.right},${box.top}`,
      `${box.right - skew},${box.bottom}`,
      `${box.left},${box.bottom}`,
    ].join(" ");
    return <polygon points={points} {...commonProps} />;
  }

  return <rect x={box.left} y={box.top} width={box.width} height={box.height} rx={10} {...commonProps} />;
}

function renderText(step) {
  const lines = String(step.label || "").split("\n");
  const lineHeight = step.type === "decision" ? 18 : 20;
  const offset = ((lines.length - 1) * lineHeight) / 2;

  return (
    <text
      x={step.x}
      y={step.y - offset}
      textAnchor="middle"
      fontSize={14}
      fontWeight={500}
      fontFamily="'IBM Plex Mono', monospace"
      fill="#243b35"
    >
      {lines.map((line, index) => (
        <tspan key={`${step.id}-${index}`} x={step.x} dy={index === 0 ? 0 : lineHeight}>
          {line}
        </tspan>
      ))}
    </text>
  );
}

function issueColor(issue) {
  const severity = String(issue?.severity || "").toLowerCase();
  if (severity === "error") return "#ef4444";
  if (severity === "warning") return "#f59e0b";
  return "#38bdf8";
}

function renderIssueDot(step, issue, onIssueClick) {
  if (!issue) return null;
  const box = getNodeBox(step);
  const fill = issueColor(issue);
  return (
    <g
      className="issue-pulse issue-hotspot"
      role="button"
      tabIndex="0"
      onPointerDown={(event) => event.stopPropagation()}
      onClick={(event) => {
        event.stopPropagation();
        onIssueClick?.(issue, { step });
      }}
    >
      <circle cx={box.right - 14} cy={box.top + 14} r="12" fill={fill} opacity="0.24" />
      <circle cx={box.right - 14} cy={box.top + 14} r="8" fill={fill} />
      <text x={box.right - 14} y={box.top + 18} textAnchor="middle" fontSize="10" fontWeight="700" fill="#fff">
        {issue.count > 9 ? "9+" : issue.count}
      </text>
    </g>
  );
}

function describeAlgorithmSource(source) {
  if (source === "provided") return "definido por el nodo";
  if (source === "real_source") return "extraido del archivo real";
  if (source === "agent_live") return "trazado por el agente";
  return "editor visual";
}

function getTokenSet(block, transition) {
  const baseName = String(block?.nodeName || "").split("/").pop() || "";
  const withoutExtension = baseName.replace(/\.[^.]+$/, "");
  const pathBase = String(block?.nodePath || "").split("/").pop() || "";
  const values = [
    block?.nodeName,
    block?.nodePath,
    baseName,
    withoutExtension,
    pathBase,
    block?.layer,
    block?.layerLabel,
    transition?.label,
  ];

  return [...new Set(values
    .filter(Boolean)
    .map((value) => String(value).toLowerCase())
    .filter((value) => value.length > 2))];
}

function scoreBridgeSourceStep(step, targetBlock, transition) {
  const haystack = `${step.label || ""}\n${step.code || ""}`.toLowerCase();
  let score = 0;

  if (step.type === "process") score += 20;
  if (step.type === "decision") score += 16;
  if (step.type === "io") score += 12;
  if (step.type === "end") score -= 24;

  for (const token of getTokenSet(targetBlock, transition)) {
    if (haystack.includes(token)) score += 34;
  }

  if (targetBlock?.layer === "backend" && /(fetch|request|post|get|api|http|endpoint)/.test(haystack)) score += 28;
  if (targetBlock?.layer === "shared" && /(schema|contract|shared|validate|payload)/.test(haystack)) score += 20;
  if (targetBlock?.layer === "data" && /(save|persist|store|json|write|file|score|task)/.test(haystack)) score += 24;
  if (targetBlock?.layer === "style" && /(css|class|theme|style)/.test(haystack)) score += 14;
  if (/(import|invoke|call|bridge|socket|sync|render|load)/.test(haystack)) score += 12;

  score += (Number(step.y) || 0) / 18;
  return score;
}

function scoreBridgeTargetStep(step, sourceBlock, transition) {
  const haystack = `${step.label || ""}\n${step.code || ""}`.toLowerCase();
  let score = 0;

  if (step.type === "start") score += 36;
  if (step.type === "io") score += 22;
  if (step.type === "process") score += 18;
  if (step.type === "decision") score += 10;

  for (const token of getTokenSet(sourceBlock, transition)) {
    if (haystack.includes(token)) score += 26;
  }

  if (sourceBlock?.layer === "frontend" && /(start|load|render|click|input|submit)/.test(haystack)) score += 16;
  if (sourceBlock?.layer === "backend" && /(request|route|handle|parse|receive|load|open)/.test(haystack)) score += 18;
  if (sourceBlock?.layer === "data" && /(read|load|schema|json|parse)/.test(haystack)) score += 14;

  score -= (Number(step.y) || 0) / 20;
  return score;
}

function pickBridgeSourceStep(block, targetBlock, transition) {
  const steps = block?.algorithm?.steps || [];
  if (!steps.length) return null;

  return [...steps]
    .sort((left, right) => scoreBridgeSourceStep(right, targetBlock, transition) - scoreBridgeSourceStep(left, targetBlock, transition))
    [0];
}

function pickBridgeTargetStep(block, sourceBlock, transition) {
  const steps = block?.algorithm?.steps || [];
  if (!steps.length) return null;

  return [...steps]
    .sort((left, right) => scoreBridgeTargetStep(right, sourceBlock, transition) - scoreBridgeTargetStep(left, sourceBlock, transition))
    [0];
}

function buildSequenceLayout(sequenceBlocks, sequenceTransitions, activeSequenceNodeId, stepIssuesByNodeId, nodeIssuesById) {
  if (!sequenceBlocks?.length) {
    return {
      steps: [],
      edges: [],
      groups: [],
      bounds: getBounds([]),
    };
  }

  const groups = [];
  const contexts = [];
  const steps = [];
  const edges = [];
  let cursorX = 140;

  sequenceBlocks.forEach((block, index) => {
    const blockSteps = block?.algorithm?.steps || [];
    if (!blockSteps.length) return;

    const blockEdges = block?.algorithm?.edges || [];
    const localBounds = getBounds(blockSteps);
    const xOffset = cursorX - localBounds.minX;
    const yOffset = SEQUENCE_TOP - localBounds.minY;
    const stepIdMap = new Map();
    const translatedSteps = blockSteps.map((step) => {
      const translatedId = `${block.nodeId}::${step.id}`;
      stepIdMap.set(step.id, translatedId);
      return {
        ...step,
        id: translatedId,
        x: step.x + xOffset,
        y: step.y + yOffset,
        ownerNodeId: block.nodeId,
        issue: stepIssuesByNodeId?.[block.nodeId]?.[step.id] || null,
      };
    });

    const translatedBounds = {
      minX: localBounds.minX + xOffset,
      minY: localBounds.minY + yOffset,
      width: localBounds.width,
      height: localBounds.height,
    };

    const group = {
      nodeId: block.nodeId,
      nodeName: block.nodeName,
      layerLabel: block.layerLabel,
      color: block.color || "#60a5fa",
      index,
      active: block.nodeId === activeSequenceNodeId,
      source: block.algorithm?.source || "editor",
      issue: nodeIssuesById?.[block.nodeId] || null,
      x: translatedBounds.minX - 34,
      y: translatedBounds.minY - SEQUENCE_HEADER_HEIGHT,
      width: translatedBounds.width + 68,
      height: translatedBounds.height + SEQUENCE_HEADER_HEIGHT + 34,
    };

    groups.push(group);
    steps.push(...translatedSteps);

    edges.push(...blockEdges
      .map((edge, edgeIndex) => ({
        id: `${block.nodeId}::${edge.id || `${edge.from}-${edge.to}-${edgeIndex}`}`,
        from: stepIdMap.get(edge.from),
        to: stepIdMap.get(edge.to),
        label: edge.label || "",
        kind: "internal",
      }))
      .filter((edge) => edge.from && edge.to));

    contexts.push({
      block,
      group,
      stepIdMap,
      originalSteps: blockSteps,
      translatedSteps,
      translatedStepMap: new Map(translatedSteps.map((step) => [step.id, step])),
    });

    cursorX = translatedBounds.minX + translatedBounds.width + SEQUENCE_GAP;
  });

  sequenceTransitions?.forEach((transition) => {
    const sourceContext = contexts.find((context) => context.block.nodeId === transition.fromNodeId);
    const targetContext = contexts.find((context) => context.block.nodeId === transition.toNodeId);
    if (!sourceContext || !targetContext) return;

    const sourceStep = pickBridgeSourceStep(sourceContext.block, targetContext.block, transition) || sourceContext.originalSteps[sourceContext.originalSteps.length - 1];
    const targetStep = pickBridgeTargetStep(targetContext.block, sourceContext.block, transition) || targetContext.originalSteps[0];
    const from = sourceContext.stepIdMap.get(sourceStep?.id);
    const to = targetContext.stepIdMap.get(targetStep?.id);
    if (!from || !to) return;

    edges.push({
      id: `bridge-${transition.fromNodeId}-${transition.toNodeId}`,
      from,
      to,
      label: transition.label || "continua",
      kind: "bridge",
      type: transition.type || "sequence",
    });
  });

  const minX = Math.min(...groups.map((group) => group.x)) - 80;
  const minY = Math.min(...groups.map((group) => group.y)) - 80;
  const maxX = Math.max(...groups.map((group) => group.x + group.width)) + 80;
  const maxY = Math.max(...groups.map((group) => group.y + group.height)) + 80;

  return {
    steps,
    edges,
    groups,
    bounds: {
      minX,
      minY,
      width: maxX - minX,
      height: maxY - minY,
    },
  };
}

export default function AlgorithmFlow({
  algorithm,
  nodeName,
  nodeId = "",
  readOnly = false,
  selectedStepId,
  flowTool,
  sequenceMode = false,
  sequenceBlocks = [],
  sequenceTransitions = [],
  activeSequenceNodeId = null,
  sequenceLabel = "",
  stepIssuesByNodeId = {},
  nodeIssuesById = {},
  onSelectStep,
  onMoveStep,
  onAddStep,
  onAddStepEdge,
  onIssueClick,
}) {
  const frameRef = useRef(null);
  const pointerRef = useRef(null);
  const interactedRef = useRef(false);
  const [frameSize, setFrameSize] = useState({ width: 0, height: 0 });
  const [viewport, setViewport] = useState({ scale: 0.5, x: 0, y: 0 });
  const [pendingConnectionId, setPendingConnectionId] = useState(null);

  const steps = algorithm?.steps || [];
  const sequenceLayout = useMemo(
    () => (
      sequenceMode
        ? buildSequenceLayout(sequenceBlocks, sequenceTransitions, activeSequenceNodeId, stepIssuesByNodeId, nodeIssuesById)
        : null
    ),
    [activeSequenceNodeId, nodeIssuesById, sequenceBlocks, sequenceMode, sequenceTransitions, stepIssuesByNodeId]
  );
  const renderedSteps = sequenceMode ? sequenceLayout?.steps || [] : steps;
  const renderedEdges = sequenceMode ? sequenceLayout?.edges || [] : algorithm?.edges || [];
  const renderedGroups = sequenceMode ? sequenceLayout?.groups || [] : [];
  const stepMap = useMemo(() => new Map(renderedSteps.map((step) => [step.id, step])), [renderedSteps]);
  const bounds = useMemo(
    () => (sequenceMode ? sequenceLayout?.bounds || getBounds([]) : getBounds(steps)),
    [sequenceLayout, sequenceMode, steps]
  );

  useEffect(() => {
    interactedRef.current = false;
  }, [sequenceBlocks.length, sequenceMode]);

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

  const resetViewport = () => {
    if (!frameSize.width || !frameSize.height) return;
    const scale = clamp(
      Math.min(frameSize.width / bounds.width, frameSize.height / bounds.height) * 0.86,
      MIN_SCALE,
      0.84
    );

    setViewport({
      scale,
      x: (frameSize.width - bounds.width * scale) * 0.5 - bounds.minX * scale,
      y: (frameSize.height - bounds.height * scale) * 0.5 - bounds.minY * scale,
    });
  };

  useEffect(() => {
    if (!interactedRef.current) {
      resetViewport();
    }
  }, [algorithm, frameSize.width, frameSize.height, sequenceLayout]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!renderedSteps.length) {
    return <div className="algorithm-empty">Este programa todavia no tiene algoritmo interno.</div>;
  }

  const handleWheel = (event) => {
    event.preventDefault();
    const frame = frameRef.current;
    if (!frame) return;
    interactedRef.current = true;

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

    if (sequenceMode || readOnly) {
      interactedRef.current = true;
      pointerRef.current = {
        mode: "pan",
        pointerId: event.pointerId,
        startClientX: event.clientX,
        startClientY: event.clientY,
        originX: viewport.x,
        originY: viewport.y,
      };
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }

    if (flowTool.startsWith("add-")) {
      const type = flowTool.replace("add-", "");
      const point = toWorldPoint(event, frame, viewport);
      onAddStep(point, type);
      setPendingConnectionId(null);
      return;
    }

    if (flowTool === "connect") {
      setPendingConnectionId(null);
      return;
    }

    interactedRef.current = true;
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

  const handleStepPointerDown = (event, step) => {
    event.stopPropagation();
    const frame = frameRef.current;
    if (!frame) return;

    if (readOnly) {
      onSelectStep(step.id);
      return;
    }

    if (sequenceMode) return;

    if (flowTool === "connect") {
      if (!pendingConnectionId) {
        setPendingConnectionId(step.id);
        onSelectStep(step.id);
        return;
      }

      if (pendingConnectionId !== step.id) {
        onAddStepEdge(pendingConnectionId, step.id);
      }
      setPendingConnectionId(null);
      return;
    }

    if (flowTool.startsWith("add-")) return;

    interactedRef.current = true;
    pointerRef.current = {
      mode: "move-step",
      pointerId: event.pointerId,
      stepId: step.id,
      startClientX: event.clientX,
      startClientY: event.clientY,
      originX: step.x,
      originY: step.y,
    };
    onSelectStep(step.id);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event) => {
    const current = pointerRef.current;
    if (!current || current.pointerId !== event.pointerId) return;

    if (current.mode === "pan") {
      setViewport((viewportState) => ({
        ...viewportState,
        x: current.originX + event.clientX - current.startClientX,
        y: current.originY + event.clientY - current.startClientY,
      }));
      return;
    }

    if (current.mode === "move-step") {
      onMoveStep(current.stepId, {
        x: current.originX + (event.clientX - current.startClientX) / viewport.scale,
        y: current.originY + (event.clientY - current.startClientY) / viewport.scale,
      });
    }
  };

  const handlePointerUp = (event) => {
    const current = pointerRef.current;
    if (!current || current.pointerId !== event.pointerId) return;
    pointerRef.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  };

  return (
    <div className="algorithm-shell">
      <div className="algorithm-meta">
        <strong>{sequenceMode ? `Secuencia conectada de ${sequenceLabel || nodeName}` : algorithm.title || `Algoritmo interno de ${nodeName}`}</strong>
        <span>
          {sequenceMode
            ? `${sequenceBlocks.length} bloque(s) visibles unidos en cascada`
            : describeAlgorithmSource(algorithm.source)}
        </span>
      </div>

      <div className="algorithm-toolbar">
        <span>
          {sequenceMode
            ? "Navega el proyecto completo con pan y zoom. Cada bloque se une donde la logica invoca al siguiente."
            : readOnly
              ? "Modo de analisis: explora el flujo con pan y zoom. Este archivo importado no se edita desde aqui."
            : flowTool === "connect"
              ? pendingConnectionId
                ? "Selecciona el bloque destino para unir el flujo."
                : "Selecciona origen y destino para crear la flecha interna."
              : flowTool.startsWith("add-")
                ? "Click en el lienzo para crear un bloque nuevo."
                : "Arrastra bloques internos. Arrastra el fondo para mover la vista. Rueda para zoom."}
        </span>
        <button type="button" className="algorithm-reset" onClick={resetViewport}>
          Recentrar
        </button>
      </div>

      <div
        className="algorithm-board"
        ref={frameRef}
        onWheel={handleWheel}
        onPointerDown={handleBackgroundPointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onDoubleClick={resetViewport}
      >
        <svg
          className="algorithm-flow"
          viewBox={`${bounds.minX} ${bounds.minY} ${bounds.width} ${bounds.height}`}
          width={bounds.width}
          height={bounds.height}
          role="img"
          aria-label={`Algoritmo interno de ${nodeName}`}
          style={{
            transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})`,
            transformOrigin: "0 0",
          }}
        >
          <defs>
            <pattern id="flow-grid" width="36" height="36" patternUnits="userSpaceOnUse">
              <path d="M 36 0 L 0 0 0 36" fill="none" stroke="rgba(173, 173, 173, 0.14)" strokeWidth="1" />
            </pattern>
            <marker id="algorithm-arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#222" />
            </marker>
          </defs>

          <rect x={bounds.minX} y={bounds.minY} width={bounds.width} height={bounds.height} fill="#fcfcfc" />
          <rect x={bounds.minX} y={bounds.minY} width={bounds.width} height={bounds.height} fill="url(#flow-grid)" />

          {renderedGroups.map((group) => (
            <g key={`group-${group.nodeId}`} className="sequence-group">
              <rect
                x={group.x}
                y={group.y}
                width={group.width}
                height={group.height}
                rx={26}
                fill={group.active ? "rgba(219, 234, 254, 0.9)" : "rgba(255, 255, 255, 0.88)"}
                stroke={group.active ? group.color : "rgba(15, 23, 42, 0.16)"}
                strokeWidth={group.active ? 4 : 2.2}
              />
              <rect
                x={group.x + 18}
                y={group.y + 16}
                width={group.width - 36}
                height={48}
                rx={16}
                fill={group.active ? `${group.color}22` : "rgba(15, 23, 42, 0.06)"}
                stroke="none"
              />
              <text x={group.x + 34} y={group.y + 47} fontSize="18" fontWeight="700" fill="#0f172a">
                {`${group.index + 1}. ${group.nodeName}`}
              </text>
              <text x={group.x + 34} y={group.y + 72} fontSize="13" fill="#475569">
                {`${group.layerLabel || "Bloque"} · ${describeAlgorithmSource(group.source)}`}
              </text>
              {group.issue ? (
                <g
                  className="issue-pulse issue-hotspot"
                  role="button"
                  tabIndex="0"
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={(event) => {
                    event.stopPropagation();
                    onIssueClick?.(group.issue, { nodeId: group.nodeId, group });
                  }}
                >
                  <circle cx={group.x + group.width - 26} cy={group.y + 32} r="13" fill={issueColor(group.issue)} opacity="0.26" />
                  <circle cx={group.x + group.width - 26} cy={group.y + 32} r="9" fill={issueColor(group.issue)} />
                  <text x={group.x + group.width - 26} y={group.y + 36} textAnchor="middle" fontSize="10" fontWeight="700" fill="#fff">
                    {group.issue.count > 9 ? "9+" : group.issue.count}
                  </text>
                </g>
              ) : null}
            </g>
          ))}

          {renderedEdges.map((edge, index) => {
            const fromStep = stepMap.get(edge.from);
            const toStep = stepMap.get(edge.to);
            if (!fromStep || !toStep) return null;
            const geometry = getEdgeGeometry(fromStep, toStep);
            return (
              <g key={`${edge.from}-${edge.to}-${index}`}>
                <path
                  d={geometry.path}
                  fill="none"
                  stroke={edge.kind === "bridge" ? "#0f172a" : "#1f1f1f"}
                  strokeWidth={edge.kind === "bridge" ? "3.4" : "2.6"}
                  strokeDasharray={edge.kind === "bridge" && edge.type === "reference" ? "14 10" : undefined}
                  markerEnd="url(#algorithm-arrow)"
                />
                {edge.label ? (
                  <text
                    x={geometry.labelX}
                    y={geometry.labelY}
                    fontSize="14"
                    fontWeight={edge.kind === "bridge" ? "700" : "500"}
                    fill={edge.kind === "bridge" ? "#0f172a" : "#5b5b5b"}
                    textAnchor="middle"
                  >
                    {edge.label}
                  </text>
                ) : null}
              </g>
            );
          })}

          {renderedSteps.map((step) => {
            const isSelected = step.id === selectedStepId;
            const isPending = step.id === pendingConnectionId;
            const issue = sequenceMode
              ? step.issue || null
              : stepIssuesByNodeId?.[nodeId]?.[step.id] || null;
            return (
              <g key={step.id} onPointerDown={(event) => handleStepPointerDown(event, step)}>
                {renderShape(step, isSelected, isPending)}
                {renderText(step)}
                {renderIssueDot(step, issue, (clickedIssue, context) => {
                  const ownerNodeId = context?.step?.ownerNodeId || nodeId;
                  onIssueClick?.(clickedIssue, {
                    ...context,
                    nodeId: ownerNodeId,
                    stepId: context?.step?.id,
                    line: context?.step?.line,
                  });
                })}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
