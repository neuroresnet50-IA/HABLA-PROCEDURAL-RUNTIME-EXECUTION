#!/usr/bin/env node

import process from "node:process";

import { parseAst } from "../../frontend/node_modules/rolldown/dist/parse-ast-index.mjs";

const ROUTE_METHODS = new Map([
  ["get", "GET"],
  ["post", "POST"],
  ["put", "PUT"],
  ["patch", "PATCH"],
  ["delete", "DELETE"],
  ["all", "ALL"],
  ["use", "USE"],
]);

const EVENT_METHODS = new Set(["on", "once", "addEventListener"]);

const POSITION_BANDS = {
  topLevel: { x: 90, y: 90, step: 54 },
  nested: { x: 210, y: 90, step: 42 },
  role: { x: 240, y: 90, step: 36 },
};

function slugify(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "graph";
}

function positionOffset(position, dx, dy) {
  if (!position || typeof position.x !== "number" || typeof position.y !== "number") {
    return null;
  }
  return {
    x: position.x + dx,
    y: position.y + dy,
  };
}

function positionFor(parentNode, bandName, ordinal) {
  const band = POSITION_BANDS[bandName];
  if (!band) {
    return null;
  }
  return positionOffset(parentNode.position, band.x, band.y + ordinal * band.step);
}

function buildSymbolNode(parentNode, symbolId, symbolName, nodeType, description, language, lineStart, lineEnd, parentId, options = {}) {
  const metadata = options.metadata ?? {};
  return {
    id: symbolId,
    nodeType,
    name: symbolName,
    projectId: parentNode.projectId,
    sceneId: parentNode.sceneId,
    canonicalPath: `${parentNode.canonicalPath}::${symbolName}`,
    sourcePath: parentNode.sourcePath,
    language,
    layer: parentNode.layer,
    originType: parentNode.originType,
    parentId,
    entryPoint: Boolean(options.entryPoint),
    readOnly: Boolean(parentNode.readOnly),
    position: options.position ?? null,
    description,
    metadata: {
      lineStart,
      lineEnd,
      symbolName,
      symbolKind: nodeType,
      sourceNodeId: parentNode.id,
      ...metadata,
    },
  };
}

function buildEdge(parentNode, edgeId, edgeType, sourceId, targetId, options = {}) {
  return {
    id: edgeId,
    edgeType,
    from: sourceId,
    to: targetId,
    projectId: parentNode.projectId,
    sceneId: parentNode.sceneId,
    originType: options.originType ?? parentNode.originType,
    label: edgeType,
    confidence: typeof options.confidence === "number" ? options.confidence : 1,
    metadata: options.metadata ?? {},
  };
}

function buildIssue(parentNode, issueType, message, options = {}) {
  return {
    id: options.id ?? `issue:semantic:javascript:${parentNode.id}:${issueType}:${options.lineStart ?? "0"}`,
    issueType,
    severity: options.severity ?? "error",
    status: "open",
    projectId: parentNode.projectId,
    sceneId: parentNode.sceneId,
    nodeId: parentNode.id,
    edgeId: "",
    stepId: "",
    sourcePath: parentNode.sourcePath,
    lineStart: options.lineStart ?? null,
    lineEnd: options.lineEnd ?? options.lineStart ?? null,
    message,
    evidence: options.evidence ?? [],
    suggestedAction: options.suggestedAction ?? "",
    metadata: {
      adapter: "javascript",
      sourceNodeId: parentNode.id,
      ...(options.metadata ?? {}),
    },
  };
}

function lineIndexFor(code) {
  const lineStarts = [0];
  for (let index = 0; index < code.length; index += 1) {
    if (code[index] === "\n") {
      lineStarts.push(index + 1);
    }
  }
  return {
    lineFor(offset) {
      if (typeof offset !== "number" || Number.isNaN(offset) || offset < 0) {
        return null;
      }
      let low = 0;
      let high = lineStarts.length - 1;
      while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        if (lineStarts[mid] <= offset) {
          low = mid + 1;
        } else {
          high = mid - 1;
        }
      }
      return high + 1;
    },
  };
}

function nodeLineRange(node, lineIndex) {
  const startOffset = typeof node?.start === "number" ? node.start : null;
  const endOffset = typeof node?.end === "number" ? node.end : startOffset;
  const lineStart = lineIndex.lineFor(startOffset);
  const safeEnd = typeof endOffset === "number" ? Math.max(endOffset - 1, startOffset ?? endOffset) : startOffset;
  const lineEnd = lineIndex.lineFor(safeEnd);
  return {
    lineStart,
    lineEnd: lineEnd ?? lineStart,
  };
}

function moduleBaseName(parentNode) {
  const source = String(parentNode.name || parentNode.canonicalPath || parentNode.id || "module");
  const basename = source.split("/").pop() || source;
  return basename.replace(/\.[^.]+$/, "") || "module";
}

function parserLanguageFor(language) {
  switch (String(language || "").toLowerCase()) {
    case "javascript":
      return "js";
    case "jsx":
      return "jsx";
    case "typescript":
      return "ts";
    case "tsx":
      return "tsx";
    default:
      return "jsx";
  }
}

function parserLanguageCandidates(language) {
  const primary = parserLanguageFor(language);
  if (primary === "js") {
    return ["js", "jsx"];
  }
  if (primary === "ts") {
    return ["ts", "tsx"];
  }
  return [primary];
}

function createScope(parent, overrides = {}) {
  return {
    parent,
    ownerSymbolId: overrides.ownerSymbolId ?? parent?.ownerSymbolId ?? null,
    ownerQualifiedName: overrides.ownerQualifiedName ?? parent?.ownerQualifiedName ?? "",
    className: overrides.className ?? parent?.className ?? "",
    bindings: new Map(),
  };
}

function defineBinding(scope, name, value) {
  if (name) {
    scope.bindings.set(name, value ?? null);
  }
}

function resolveBinding(scope, name) {
  let current = scope;
  while (current) {
    if (current.bindings.has(name)) {
      return current.bindings.get(name) ?? null;
    }
    current = current.parent;
  }
  return null;
}

function collectPatternIdentifiers(pattern, names = []) {
  if (!pattern || typeof pattern !== "object") {
    return names;
  }
  switch (pattern.type) {
    case "Identifier":
      names.push(pattern.name);
      break;
    case "AssignmentPattern":
      collectPatternIdentifiers(pattern.left, names);
      break;
    case "RestElement":
      collectPatternIdentifiers(pattern.argument, names);
      break;
    case "ArrayPattern":
      for (const item of pattern.elements || []) {
        collectPatternIdentifiers(item, names);
      }
      break;
    case "ObjectPattern":
      for (const property of pattern.properties || []) {
        if (property?.type === "Property") {
          collectPatternIdentifiers(property.value, names);
        } else if (property?.type === "RestElement") {
          collectPatternIdentifiers(property.argument, names);
        }
      }
      break;
    default:
      break;
  }
  return names;
}

function isFunctionLike(node) {
  return node?.type === "FunctionDeclaration" || node?.type === "FunctionExpression" || node?.type === "ArrowFunctionExpression";
}

function unwrapDeclaration(node) {
  if (!node || typeof node !== "object") {
    return node;
  }
  if (node.type === "ExportNamedDeclaration" || node.type === "ExportDefaultDeclaration") {
    return node.declaration || node;
  }
  return node;
}

function propertyName(node) {
  if (!node || typeof node !== "object") {
    return "";
  }
  if (node.type === "Identifier" || node.type === "JSXIdentifier") {
    return node.name || "";
  }
  if (node.type === "PrivateIdentifier") {
    return `#${node.name || ""}`;
  }
  if (node.type === "Literal" && typeof node.value === "string") {
    return node.value;
  }
  return "";
}

function memberName(node) {
  if (!node || typeof node !== "object") {
    return "";
  }
  if (node.type === "Identifier" || node.type === "JSXIdentifier") {
    return node.name || "";
  }
  if (node.type === "ThisExpression") {
    return "this";
  }
  if (node.type === "Super") {
    return "super";
  }
  if (node.type === "PrivateIdentifier") {
    return `#${node.name || ""}`;
  }
  if (node.type === "MemberExpression") {
    const objectName = memberName(node.object);
    const nextName = node.computed ? propertyName(node.property) : propertyName(node.property);
    if (!objectName) {
      return nextName;
    }
    if (!nextName) {
      return objectName;
    }
    return `${objectName}.${nextName}`;
  }
  return "";
}

function literalText(node) {
  if (!node || typeof node !== "object") {
    return null;
  }
  if (node.type === "Literal" && typeof node.value === "string") {
    return node.value;
  }
  if (node.type === "TemplateLiteral" && (node.expressions || []).length === 0) {
    return (node.quasis || []).map((part) => part.value?.cooked ?? "").join("");
  }
  return null;
}

function openingElementName(node) {
  if (!node || typeof node !== "object") {
    return "";
  }
  if (node.type === "JSXIdentifier") {
    return node.name || "";
  }
  if (node.type === "JSXMemberExpression") {
    const objectName = openingElementName(node.object);
    const property = openingElementName(node.property);
    return objectName && property ? `${objectName}.${property}` : property || objectName;
  }
  if (node.type === "JSXNamespacedName") {
    return `${openingElementName(node.namespace)}:${openingElementName(node.name)}`;
  }
  return "";
}

function normalizeJsxEventName(rawName) {
  if (!rawName.startsWith("on") || rawName.length <= 2) {
    return rawName;
  }
  return rawName.slice(2, 3).toLowerCase() + rawName.slice(3);
}

function isComponentLikeName(name) {
  return typeof name === "string" && /^[A-Z]/.test(name);
}

function walkNode(node, visitor, parent = null) {
  if (!node || typeof node !== "object") {
    return;
  }
  if (Array.isArray(node)) {
    for (const entry of node) {
      walkNode(entry, visitor, parent);
    }
    return;
  }
  const shouldContinue = visitor.enter ? visitor.enter(node, parent) : true;
  if (shouldContinue === false) {
    return;
  }
  for (const [key, value] of Object.entries(node)) {
    if (key === "parent" || value == null) {
      continue;
    }
    if (typeof value === "object") {
      walkNode(value, visitor, node);
    }
  }
}

function analyzeJavaScriptNode(parentNode) {
  const code = String(parentNode.code || "");
  if (!code.trim()) {
    return {
      version: "1.0",
      nodes: [],
      edges: [],
      issues: [],
      metadata: { nodeCount: 0, edgeCount: 0, issueCount: 0, adapterCount: 0 },
      adapters: [],
    };
  }

  const language = String(parentNode.language || "javascript");
  const parserLanguages = parserLanguageCandidates(language);
  const lineIndex = lineIndexFor(code);
  const semanticNodes = [];
  const semanticEdges = [];
  const semanticIssues = [];
  const adapters = [];
  const declarationRecords = new WeakMap();
  const symbolNodesById = new Map();
  const moduleName = moduleBaseName(parentNode);
  const deferredCalls = [];
  const deferredRoleLinks = [];
  const deferredRenders = [];
  const importBindings = [];
  const state = {
    symbolOrdinal: 0,
    roleOrdinal: 0,
    inlineOrdinal: 0,
    callEdgeIds: new Set(),
  };

  let program;
  let parseError = null;
  let parserLanguage = parserLanguages[0];
  for (const candidate of parserLanguages) {
    try {
      program = parseAst(code, { lang: candidate }, parentNode.canonicalPath || parentNode.sourcePath || `${moduleName}.${candidate}`);
      parserLanguage = candidate;
      parseError = null;
      break;
    } catch (error) {
      parseError = error;
    }
  }

  if (!program) {
    const message = parseError instanceof Error ? parseError.message : "Fallo de parseo desconocido";
    semanticIssues.push(
      buildIssue(parentNode, "parse_failure", "El adaptador semantico JS/TS no pudo parsear el archivo.", {
        evidence: ["rolldown.parseAst", message],
        suggestedAction: "Corrige la sintaxis del modulo para habilitar la extraccion canonica.",
        metadata: { parser: "rolldown-ast", attemptedParsers: parserLanguages, rawMessage: message },
      }),
    );
    adapters.push({
      language,
      parser: "rolldown-ast",
      status: "parse_failed",
      sourceNodeId: parentNode.id,
      limitations: ["syntax_error"],
    });
    return {
      version: "1.0",
      nodes: semanticNodes,
      edges: semanticEdges,
      issues: semanticIssues,
      metadata: {
        nodeCount: semanticNodes.length,
        edgeCount: semanticEdges.length,
        issueCount: semanticIssues.length,
        adapterCount: adapters.length,
      },
      adapters,
    };
  }

  function addEdge(edge) {
    if (!semanticEdges.some((current) => current.id === edge.id)) {
      semanticEdges.push(edge);
    }
  }

  function markExport(symbolId, exportName, isDefault = false) {
    const symbolNode = symbolNodesById.get(symbolId);
    if (!symbolNode) {
      return;
    }
    const metadata = symbolNode.metadata ?? {};
    const exportNames = Array.isArray(metadata.exportNames) ? [...metadata.exportNames] : [];
    if (exportName && !exportNames.includes(exportName)) {
      exportNames.push(exportName);
    }
    symbolNode.metadata = {
      ...metadata,
      exportNames,
      exported: exportNames.length > 0 || isDefault,
      defaultExport: Boolean(metadata.defaultExport || isDefault),
    };
  }

  function importBindingValue(specifier, localName, importedName, mode) {
    return {
      kind: "import",
      specifier,
      localName,
      importedName,
      mode,
      sourceNodeId: parentNode.id,
      lineStart: null,
    };
  }

  function registerImportBinding(scope, importDeclaration) {
    const specifier = literalText(importDeclaration.source) || "";
    const { lineStart } = nodeLineRange(importDeclaration, lineIndex);
    if (!specifier) {
      return;
    }
    if (importDeclaration.importKind === "type" || importDeclaration.phase === "type") {
      return;
    }
    for (const specifierNode of importDeclaration.specifiers || []) {
      const localName = propertyName(specifierNode.local);
      if (!localName) {
        continue;
      }
      let importedName = localName;
      let mode = "named";
      if (specifierNode.type === "ImportDefaultSpecifier") {
        importedName = "default";
        mode = "default";
      } else if (specifierNode.type === "ImportNamespaceSpecifier") {
        importedName = "*";
        mode = "namespace";
      } else if (specifierNode.type === "ImportSpecifier") {
        importedName = propertyName(specifierNode.imported) || localName;
      } else {
        continue;
      }
      const value = importBindingValue(specifier, localName, importedName, mode);
      defineBinding(scope, localName, value);
      importBindings.push({
        specifier,
        localName,
        importedName,
        mode,
        lineStart,
      });
    }
  }

  function registerSymbol({
    bindingName,
    qualifiedName,
    nodeType,
    description,
    node,
    scope,
    parentId,
    relationType,
    entryPoint = false,
    metadata = {},
    className = "",
  }) {
    const { lineStart, lineEnd } = nodeLineRange(node, lineIndex);
    const symbolId = `${parentNode.id}::${nodeType}:${slugify(qualifiedName)}:${lineStart ?? 0}`;
    const parentRelation = relationType === "contains" ? "topLevel" : "nested";
    const symbolNode = buildSymbolNode(
      parentNode,
      symbolId,
      qualifiedName,
      nodeType,
      description,
      language,
      lineStart,
      lineEnd,
      parentId,
      {
        entryPoint,
        position: positionFor(parentNode, parentRelation, state.symbolOrdinal),
        metadata: {
          ...metadata,
          bindingName,
          topLevel: parentId === parentNode.id,
        },
      },
    );
    state.symbolOrdinal += 1;
    semanticNodes.push(symbolNode);
    symbolNodesById.set(symbolId, symbolNode);
    addEdge(
      buildEdge(
        parentNode,
        `edge:${parentId}->${symbolId}:${relationType}`,
        relationType,
        parentId,
        symbolId,
      ),
    );
    const record = {
      id: symbolId,
      bindingName,
      qualifiedName,
      className,
      nodeType,
      astNode: node,
    };
    declarationRecords.set(node, record);
    defineBinding(scope, bindingName, symbolId);
    if (qualifiedName !== bindingName) {
      defineBinding(scope, qualifiedName, symbolId);
    }
    return record;
  }

  function registerRouteOrEvent({
    ownerParentId,
    ownerName,
    callNode,
    nodeType,
    displayName,
    metadata,
  }) {
    const { lineStart, lineEnd } = nodeLineRange(callNode, lineIndex);
    const roleId = `${parentNode.id}::${nodeType}:${slugify(displayName || ownerName)}:${lineStart ?? 0}:${state.roleOrdinal + 1}`;
    state.roleOrdinal += 1;
    const roleNode = buildSymbolNode(
      parentNode,
      roleId,
      displayName,
      nodeType,
      nodeType === "route" ? "Ruta HTTP inferida desde el modulo JS/TS." : "Handler de evento inferido desde el modulo JS/TS.",
      language,
      lineStart,
      lineEnd,
      ownerParentId,
      {
        position: positionFor(parentNode, "role", state.roleOrdinal - 1),
        metadata,
      },
    );
    semanticNodes.push(roleNode);
    addEdge(
      buildEdge(
        parentNode,
        `edge:${ownerParentId}->${roleId}:contains`,
        "contains",
        ownerParentId,
        roleId,
      ),
    );
    return roleId;
  }

  function resolveSymbolReference(expression, scope) {
    if (!expression || typeof expression !== "object") {
      return null;
    }
    if (expression.type === "Identifier") {
      return resolveBinding(scope, expression.name || "");
    }
    if (expression.type === "MemberExpression") {
      const fullName = memberName(expression);
      if (!fullName) {
        return null;
      }
      const direct = resolveBinding(scope, fullName);
      if (direct) {
        return direct;
      }
      if (fullName.startsWith("this.")) {
        const suffix = fullName.slice(5);
        const classScoped = resolveBinding(scope, `${scope.className}.${suffix}`);
        if (classScoped) {
          return classScoped;
        }
      }
      const objectReference = resolveSymbolReference(expression.object, scope);
      if (
        objectReference
        && typeof objectReference === "object"
        && objectReference.kind === "import"
        && objectReference.mode === "namespace"
      ) {
        const importedName = propertyName(expression.property);
        if (!importedName) {
          return null;
        }
        return {
          ...objectReference,
          importedName,
          namespaceMember: true,
        };
      }
    }
    return null;
  }

  function recordDeferredEdge(edgeType, sourceId, targetReference, node, metadata = {}) {
    if (!sourceId || !targetReference || typeof targetReference !== "object" || targetReference.kind !== "import") {
      return;
    }
    const { lineStart } = nodeLineRange(node, lineIndex);
    const collection = edgeType === "renders" ? deferredRenders : edgeType === "calls" ? deferredCalls : deferredRoleLinks;
    collection.push({
      edgeType,
      sourceId,
      sourceNodeId: parentNode.id,
      specifier: targetReference.specifier,
      importedName: targetReference.importedName,
      localName: targetReference.localName,
      mode: targetReference.mode,
      lineStart,
      metadata,
    });
  }

  function addCallEdge(sourceId, targetId, callNode, metadata = {}) {
    if (!sourceId || !targetId || sourceId === targetId) {
      return;
    }
    const { lineStart } = nodeLineRange(callNode, lineIndex);
    const edgeId = `edge:${sourceId}->${targetId}:calls:${lineStart ?? 0}`;
    if (state.callEdgeIds.has(edgeId)) {
      return;
    }
    state.callEdgeIds.add(edgeId);
    addEdge(
      buildEdge(
        parentNode,
        edgeId,
        "calls",
        sourceId,
        targetId,
        {
          originType: "inference",
          confidence: 0.92,
          metadata,
        },
      ),
    );
  }

  function createInlineFunction(baseName, node, scope, ownerParentId, relationType) {
    const ownerPrefix = scope.ownerQualifiedName || moduleName;
    const inlineName = `${ownerPrefix}.${baseName}${state.inlineOrdinal + 1}`;
    state.inlineOrdinal += 1;
    const record = registerSymbol({
      bindingName: inlineName.split(".").pop() || inlineName,
      qualifiedName: inlineName,
      nodeType: "function",
      description: `Callback inline inferido en ${ownerPrefix}.`,
      node,
      scope,
      parentId: ownerParentId,
      relationType,
      metadata: {
        inline: true,
        ownerSymbolId: scope.ownerSymbolId,
      },
      className: scope.className,
    });
    analyzeFunctionLike(node, record, scope);
    return record.id;
  }

  function predeclareBlock(body, scope) {
    for (const originalStatement of body || []) {
      if (originalStatement?.type === "ImportDeclaration") {
        registerImportBinding(scope, originalStatement);
        continue;
      }
      const statement = unwrapDeclaration(originalStatement);
      if (!statement || typeof statement !== "object") {
        continue;
      }

      if (statement.type === "FunctionDeclaration" && statement.id?.name) {
        registerSymbol({
          bindingName: statement.id.name,
          qualifiedName: scope.ownerQualifiedName ? `${scope.ownerQualifiedName}.${statement.id.name}` : statement.id.name,
          nodeType: "function",
          description: scope.ownerSymbolId
            ? `Funcion local \`${statement.id.name}\` extraida desde \`${scope.ownerQualifiedName}\`.`
            : `Funcion top-level \`${statement.id.name}\` extraida del modulo JS/TS.`,
          node: statement,
          scope,
          parentId: scope.ownerSymbolId || parentNode.id,
          relationType: scope.ownerSymbolId ? "defines" : "contains",
          entryPoint: !scope.ownerSymbolId && ["main", "run", "bootstrap", "start", "initializeApp", "App"].includes(statement.id.name),
          className: scope.className,
        });
        continue;
      }

      if (statement.type === "VariableDeclaration") {
        for (const declaration of statement.declarations || []) {
          for (const name of collectPatternIdentifiers(declaration.id)) {
            defineBinding(scope, name, null);
          }
          if (declaration.id?.type !== "Identifier" || !isFunctionLike(declaration.init)) {
            continue;
          }
          registerSymbol({
            bindingName: declaration.id.name,
            qualifiedName: scope.ownerQualifiedName ? `${scope.ownerQualifiedName}.${declaration.id.name}` : declaration.id.name,
            nodeType: "function",
            description: scope.ownerSymbolId
              ? `Funcion local \`${declaration.id.name}\` extraida desde \`${scope.ownerQualifiedName}\`.`
              : `Funcion top-level \`${declaration.id.name}\` extraida del modulo JS/TS.`,
            node: declaration.init,
            scope,
            parentId: scope.ownerSymbolId || parentNode.id,
            relationType: scope.ownerSymbolId ? "defines" : "contains",
            entryPoint: !scope.ownerSymbolId && ["main", "run", "bootstrap", "start", "initializeApp", "App"].includes(declaration.id.name),
            className: scope.className,
          });
        }
        continue;
      }

      if (statement.type === "ClassDeclaration" && statement.id?.name) {
        const classRecord = registerSymbol({
          bindingName: statement.id.name,
          qualifiedName: scope.ownerQualifiedName ? `${scope.ownerQualifiedName}.${statement.id.name}` : statement.id.name,
          nodeType: "class",
          description: `Clase \`${statement.id.name}\` extraida del modulo JS/TS.`,
          node: statement,
          scope,
          parentId: scope.ownerSymbolId || parentNode.id,
          relationType: scope.ownerSymbolId ? "defines" : "contains",
          className: statement.id.name,
        });
        const classScope = createScope(scope, {
          ownerSymbolId: classRecord.id,
          ownerQualifiedName: classRecord.qualifiedName,
          className: statement.id.name,
        });
        for (const member of statement.body?.body || []) {
          if (member?.type !== "MethodDefinition") {
            continue;
          }
          const methodName = propertyName(member.key);
          if (!methodName || !isFunctionLike(member.value)) {
            continue;
          }
          const qualifiedName = `${classRecord.qualifiedName}.${methodName}`;
          const methodRecord = registerSymbol({
            bindingName: methodName,
            qualifiedName,
            nodeType: "method",
            description: `Metodo \`${methodName}\` de la clase \`${classRecord.qualifiedName}\`.`,
            node: member.value,
            scope: classScope,
            parentId: classRecord.id,
            relationType: "defines",
            className: classRecord.qualifiedName,
          });
          defineBinding(classScope, `${classRecord.qualifiedName}.${methodName}`, methodRecord.id);
          defineBinding(classScope, `this.${methodName}`, methodRecord.id);
        }
      }
    }
  }

  function analyzeFunctionLike(functionNode, record, parentScope) {
    const functionScope = createScope(parentScope, {
      ownerSymbolId: record.id,
      ownerQualifiedName: record.qualifiedName,
      className: record.className || parentScope.className,
    });

    for (const param of functionNode.params || []) {
      for (const name of collectPatternIdentifiers(param)) {
        defineBinding(functionScope, name, null);
      }
    }

    if (record.className) {
      let current = parentScope;
      while (current) {
        for (const [bindingName, bindingValue] of current.bindings.entries()) {
          if (bindingName.startsWith("this.") || bindingName.startsWith(`${record.className}.`)) {
            defineBinding(functionScope, bindingName, bindingValue);
          }
        }
        current = current.parent;
      }
    }

    if (functionNode.body?.type === "BlockStatement") {
      analyzeBlock(functionNode.body.body || [], functionScope);
      return;
    }
    analyzeExpression(functionNode.body, functionScope);
  }

  function linkRoleToHandler(roleId, edgeType, handlerExpression, scope, ownerParentId, baseName, metadata) {
    let handlerReference = resolveSymbolReference(handlerExpression, scope);
    if (!handlerReference && isFunctionLike(handlerExpression)) {
      const handlerId = createInlineFunction(baseName, handlerExpression, scope, ownerParentId, "defines");
      addEdge(
        buildEdge(
          parentNode,
          `edge:${roleId}->${handlerId}:${edgeType}`,
          edgeType,
          roleId,
          handlerId,
          {
            originType: "inference",
            confidence: 0.95,
            metadata,
          },
        ),
      );
      return;
    }
    if (!handlerReference) {
      return;
    }
    if (typeof handlerReference === "object" && handlerReference.kind === "import") {
      recordDeferredEdge(edgeType, roleId, handlerReference, handlerExpression, metadata);
      return;
    }
    const handlerId = typeof handlerReference === "string" ? handlerReference : null;
    if (!handlerId) {
      return;
    }
    addEdge(
      buildEdge(
        parentNode,
        `edge:${roleId}->${handlerId}:${edgeType}`,
        edgeType,
        roleId,
        handlerId,
        {
          originType: "inference",
          confidence: 0.95,
          metadata,
        },
      ),
    );
  }

  function handlerArgument(callExpression, startIndex) {
    for (const argument of callExpression.arguments.slice(startIndex)) {
      if (!argument || typeof argument !== "object") {
        continue;
      }
      if (argument.type === "Identifier" || argument.type === "MemberExpression" || isFunctionLike(argument)) {
        return argument;
      }
    }
    return null;
  }

  function handleRoleCall(callExpression, scope) {
    if (callExpression.callee?.type !== "MemberExpression") {
      return false;
    }

    const calleeObject = memberName(callExpression.callee.object);
    const calleeProperty = propertyName(callExpression.callee.property).toLowerCase();
    const roleParentId = scope.ownerSymbolId || parentNode.id;
    const ownerName = scope.ownerQualifiedName || moduleName;

    if (["app", "router", "server"].includes(calleeObject) && ROUTE_METHODS.has(calleeProperty)) {
      const method = ROUTE_METHODS.get(calleeProperty);
      const routePath = literalText(callExpression.arguments[0]) || "";
      const handler = handlerArgument(callExpression, routePath ? 1 : 0);
      const routeId = registerRouteOrEvent({
        ownerParentId: roleParentId,
        ownerName,
        callNode: callExpression,
        nodeType: "route",
        displayName: `${method} ${routePath}`.trim(),
        metadata: {
          methods: [method],
          path: routePath,
          handlerName: handler?.type === "Identifier" ? handler.name : "",
        },
      });
      if (handler) {
        linkRoleToHandler(
          routeId,
          "routes_to",
          handler,
          scope,
          roleParentId,
          `${method.toLowerCase()}RouteHandler`,
          { methods: [method], path: routePath },
        );
      }
      return true;
    }

    if (EVENT_METHODS.has(calleeProperty)) {
      const eventName = literalText(callExpression.arguments[0]) || "";
      if (!eventName) {
        return false;
      }
      const handler = handlerArgument(callExpression, 1);
      const eventId = registerRouteOrEvent({
        ownerParentId: roleParentId,
        ownerName,
        callNode: callExpression,
        nodeType: "event_handler",
        displayName: eventName,
        metadata: {
          eventName,
          handlerName: handler?.type === "Identifier" ? handler.name : "",
          emitter: calleeObject || "unknown",
        },
      });
      if (handler) {
        linkRoleToHandler(
          eventId,
          "handles",
          handler,
          scope,
          roleParentId,
          `${slugify(eventName)}Handler`,
          { eventName, emitter: calleeObject || "unknown" },
        );
      }
      return true;
    }

    return false;
  }

  function handleJsxOpeningElement(openingElement, scope) {
    const elementName = openingElementName(openingElement.name) || "element";
    const roleParentId = scope.ownerSymbolId || parentNode.id;
    const componentReferenceName = elementName.split(".")[0] || elementName;

    if (isComponentLikeName(componentReferenceName)) {
      const targetReference = resolveSymbolReference(
        openingElement.name.type === "JSXIdentifier"
          ? { type: "Identifier", name: openingElement.name.name }
          : openingElement.name.type === "JSXMemberExpression"
            ? {
                type: "MemberExpression",
                object: openingElement.name.object,
                property: openingElement.name.property,
                computed: false,
              }
            : null,
        scope,
      );
      if (typeof targetReference === "string") {
        addEdge(
          buildEdge(
            parentNode,
            `edge:${roleParentId}->${targetReference}:renders:${nodeLineRange(openingElement, lineIndex).lineStart ?? 0}`,
            "renders",
            roleParentId,
            targetReference,
            {
              originType: "inference",
              confidence: 0.91,
              metadata: { componentName: elementName },
            },
          ),
        );
      } else if (targetReference && typeof targetReference === "object" && targetReference.kind === "import") {
        recordDeferredEdge("renders", roleParentId, targetReference, openingElement, { componentName: elementName });
      }
    }

    for (const attribute of openingElement.attributes || []) {
      if (attribute?.type !== "JSXAttribute") {
        continue;
      }
      const rawName = propertyName(attribute.name);
      if (!rawName.startsWith("on") || rawName.length <= 2) {
        continue;
      }
      const eventName = normalizeJsxEventName(rawName);
      const expression = attribute.value?.type === "JSXExpressionContainer" ? attribute.value.expression : null;
      const eventId = registerRouteOrEvent({
        ownerParentId: roleParentId,
        ownerName: scope.ownerQualifiedName || moduleName,
        callNode: attribute,
        nodeType: "event_handler",
        displayName: `${eventName}@${elementName}`,
        metadata: {
          eventName,
          elementName,
          handlerName: expression?.type === "Identifier" ? expression.name : "",
        },
      });
      if (!expression) {
        continue;
      }
      linkRoleToHandler(
        eventId,
        "handles",
        expression,
        scope,
        roleParentId,
        `${eventName}JsxHandler`,
        { eventName, elementName },
      );
    }
  }

  function analyzeExpression(node, scope) {
    if (!node || typeof node !== "object") {
      return;
    }
    walkNode(node, {
      enter(current, parent) {
        if (current !== node && isFunctionLike(current)) {
          return false;
        }
        if (current.type === "ClassDeclaration" || current.type === "ClassExpression") {
          return false;
        }
        if (current.type === "CallExpression") {
          if (handleRoleCall(current, scope)) {
            return false;
          }
          const sourceId = scope.ownerSymbolId;
          const targetReference = sourceId ? resolveSymbolReference(current.callee, scope) : null;
          if (sourceId && typeof targetReference === "string") {
            addCallEdge(sourceId, targetReference, current, {
              callee: memberName(current.callee) || current.callee?.name || "",
            });
          } else if (sourceId && targetReference && typeof targetReference === "object" && targetReference.kind === "import") {
            recordDeferredEdge("calls", sourceId, targetReference, current, {
              callee: memberName(current.callee) || current.callee?.name || "",
            });
          }
        }
        if (current.type === "JSXOpeningElement") {
          handleJsxOpeningElement(current, scope);
          return false;
        }
        if (current !== node && current.type === "VariableDeclaration") {
          return false;
        }
        if (current !== node && current.type === "FunctionDeclaration") {
          return false;
        }
        if (current !== node && current.type === "ClassDeclaration") {
          return false;
        }
        return true;
      },
    });
  }

  function collectExports(body, scope) {
    for (const statement of body || []) {
      if (!statement || typeof statement !== "object") {
        continue;
      }

      if (statement.type === "ExportNamedDeclaration") {
        if (statement.declaration?.type === "FunctionDeclaration" || statement.declaration?.type === "ClassDeclaration") {
          const exportedName = statement.declaration.id?.name || "";
          const record = declarationRecords.get(statement.declaration);
          if (record && exportedName) {
            markExport(record.id, exportedName, false);
          }
        } else if (statement.declaration?.type === "VariableDeclaration") {
          for (const declaration of statement.declaration.declarations || []) {
            const exportedName = declaration.id?.type === "Identifier" ? declaration.id.name : "";
            const record = declarationRecords.get(declaration.init);
            if (record && exportedName) {
              markExport(record.id, exportedName, false);
            }
          }
        }

        for (const specifier of statement.specifiers || []) {
          const localName = propertyName(specifier.local);
          const exportedName = propertyName(specifier.exported) || localName;
          const reference = resolveBinding(scope, localName);
          if (typeof reference === "string" && exportedName) {
            markExport(reference, exportedName, false);
          }
        }
        continue;
      }

      if (statement.type === "ExportDefaultDeclaration") {
        const declaration = statement.declaration;
        if (!declaration || typeof declaration !== "object") {
          continue;
        }
        if (declaration.type === "Identifier") {
          const reference = resolveBinding(scope, declaration.name || "");
          if (typeof reference === "string") {
            markExport(reference, "default", true);
          }
          continue;
        }
        const record = declarationRecords.get(declaration);
        if (record) {
          markExport(record.id, "default", true);
        }
      }
    }
  }

  function analyzeStatement(statement, scope) {
    if (!statement || typeof statement !== "object") {
      return;
    }

    const unwrapped = unwrapDeclaration(statement);
    if (!unwrapped || typeof unwrapped !== "object") {
      return;
    }

    if (unwrapped.type === "FunctionDeclaration") {
      const record = declarationRecords.get(unwrapped);
      if (record) {
        analyzeFunctionLike(unwrapped, record, scope);
      }
      return;
    }

    if (unwrapped.type === "ClassDeclaration") {
      for (const member of unwrapped.body?.body || []) {
        if (member?.type !== "MethodDefinition" || !isFunctionLike(member.value)) {
          continue;
        }
        const record = declarationRecords.get(member.value);
        if (record) {
          analyzeFunctionLike(member.value, record, scope);
        }
      }
      return;
    }

    if (unwrapped.type === "VariableDeclaration") {
      for (const declaration of unwrapped.declarations || []) {
        if (declaration.id?.type === "Identifier" && isFunctionLike(declaration.init)) {
          const record = declarationRecords.get(declaration.init);
          if (record) {
            analyzeFunctionLike(declaration.init, record, scope);
          }
          continue;
        }
        analyzeExpression(declaration.init, scope);
      }
      return;
    }

    if (unwrapped.type === "BlockStatement") {
      analyzeBlock(unwrapped.body || [], createScope(scope));
      return;
    }

    analyzeExpression(unwrapped, scope);
  }

  function analyzeBlock(body, scope) {
    predeclareBlock(body, scope);
    for (const statement of body || []) {
      analyzeStatement(statement, scope);
    }
  }

  const moduleScope = createScope(null, {
    ownerSymbolId: null,
    ownerQualifiedName: "",
    className: "",
  });
  analyzeBlock(program.body || [], moduleScope);
  collectExports(program.body || [], moduleScope);

  adapters.push({
    language,
    parser: `rolldown-ast:${parserLanguage}`,
    status: "ok",
    sourceNodeId: parentNode.id,
    limitations: [
      "default exports anonimos sin binding local no se promueven todavia",
      "callbacks anonimos fuera de rutas/eventos no crean nodos dedicados",
    ],
    nodeCount: semanticNodes.length,
    imports: importBindings,
    deferredCalls,
    deferredRoleLinks,
    deferredRenders,
  });

  return {
    version: "1.0",
    nodes: semanticNodes,
    edges: semanticEdges,
    issues: semanticIssues,
    metadata: {
      nodeCount: semanticNodes.length,
      edgeCount: semanticEdges.length,
      issueCount: semanticIssues.length,
      adapterCount: adapters.length,
    },
    adapters,
  };
}

async function readPayload() {
  let input = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) {
    input += chunk;
  }
  return input.trim() ? JSON.parse(input) : {};
}

async function main() {
  const payload = await readPayload();
  const relevantNodes = Array.isArray(payload.nodes) ? payload.nodes : [];
  const merged = {
    version: String(payload.contractVersion || "1.0"),
    nodes: [],
    edges: [],
    issues: [],
    metadata: {
      nodeCount: 0,
      edgeCount: 0,
      issueCount: 0,
      adapterCount: 0,
    },
    adapters: [],
  };

  for (const parentNode of relevantNodes) {
    const result = analyzeJavaScriptNode(parentNode);
    merged.nodes.push(...result.nodes);
    merged.edges.push(...result.edges);
    merged.issues.push(...result.issues);
    merged.adapters.push(...result.adapters);
  }

  merged.metadata = {
    nodeCount: merged.nodes.length,
    edgeCount: merged.edges.length,
    issueCount: merged.issues.length,
    adapterCount: merged.adapters.length,
  };

  process.stdout.write(JSON.stringify(merged));
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
