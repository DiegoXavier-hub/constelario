# -*- coding: utf-8 -*-
"""Constelário — grafos de conhecimento interativos (2D/3D) em um único HTML.

API pública::

    from constelario import Graph, Theme, Node, Edge

    g = Graph(title="Meu Grafo", theme=Theme.arcano())
    g.add_type("Pessoa", color="#4a9c8c", icon="user")
    g.add_node("p1", "Alice", "Pessoa")
    g.save("grafo.html")
"""
from . import edges
from .graph import LAYOUTS, Graph
from .icons import BUILTIN_ICONS
from .model import Edge, Node, TypeStyle
from .strings import DEFAULT_STRINGS
from .theme import DEFAULT_PALETTE, Theme

__version__ = "0.2.0"
__all__ = [
    "Graph", "Theme", "Node", "Edge", "TypeStyle", "edges",
    "BUILTIN_ICONS", "DEFAULT_PALETTE", "DEFAULT_STRINGS", "LAYOUTS",
    "__version__",
]
