from __future__ import annotations

from typing import Any, Dict, Iterable

from ir_adapters.common import merge_adapter_results
from ir_adapters.html_css_adapter import build_html_css_semantic_graph
from ir_adapters.inter_module_linker import link_inter_module_semantics
from ir_adapters.javascript_adapter import build_javascript_semantic_graph
from ir_adapters.python_adapter import build_python_semantic_graph


SEMANTIC_ADAPTERS = (
    build_python_semantic_graph,
    build_javascript_semantic_graph,
    build_html_css_semantic_graph,
)


def build_semantic_graph(nodes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    node_list = list(nodes)
    merged = merge_adapter_results(adapter(node_list) for adapter in SEMANTIC_ADAPTERS)
    return link_inter_module_semantics(node_list, merged)
