# -*- coding: utf-8 -*-
"""Exemplo avançado: tema custom, ícone próprio, painéis, modos de cor,
estilos de aresta, ranking no inspetor e layout inicial por comunidades.

Rode com:  python examples/customizado.py
"""
import random

from constelario import Graph, Theme

random.seed(42)

tema = Theme.arcano().with_(accent="#8be9fd", accent2="#c8f4ff")
g = Graph(title="Rede Arcana", subtitle="exemplo customizado", theme=tema)

# ícone próprio (miolo de SVG 24x24 em stroke)
g.add_icon("anel", '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>')

g.add_type("Torre", label="Torre Arcana", color="#8be9fd", icon="crown",
           tier="keystone", ring=0)
g.add_type("Mago", color="#bd93f9", icon="user", tier="notable")
g.add_type("Feitiço", color="#ff79c6", icon="zap")
g.add_type("Artefato", color="#f1fa8c", icon="anel")
g.add_type("Pergaminho", color="#6272a4", icon="book", hidden=True)  # massa: halo

g.add_node("torre", "Torre de Cristal", "Torre")
escolas = ["evocação", "ilusão", "abjuração"]
for i in range(9):
    g.add_node(f"m{i}", f"Mago {i}", "Mago", community=i % 3,
               props={"escola": escolas[i % 3], "nível": 3 + i})
    g.add_edge(f"m{i}", "torre", type="SERVE_A")
for i in range(15):
    g.add_node(f"f{i}", f"Feitiço {i}", "Feitiço", community=i % 3,
               props={"escola": escolas[i % 3]})
    g.add_edge(f"m{i % 9}", f"f{i}", type="CONHECE")
for i in range(6):
    g.add_node(f"a{i}", f"Artefato {i}", "Artefato", community=i % 3)
    g.add_edge(f"a{i}", f"m{i}", type="GUARDADO_POR")
for i in range(40):
    g.add_node(f"s{i}", f"Pergaminho {i}", "Pergaminho", community=i % 3)
    g.add_edge(f"s{i}", f"f{i % 15}", type="DESCREVE")

# arestas de similaridade com score -> ranking no inspetor
for a, b in [("m0", "m3"), ("m0", "m6"), ("m1", "m4"), ("m2", "m8")]:
    g.add_edge(a, b, type="SIMILAR_A", props={"score": round(random.uniform(0.5, 1), 3)})

g.edge_style("default", opacity=0.15)
g.edge_style("SIMILAR_A", color="#8be9fd", width=1.6, opacity=0.7)
g.edge_style("DESCREVE", dashes=True, opacity=0.25)

g.add_color_mode("escola", "Escola de magia", prop="escola")
g.inspector_ranking("SIMILAR_A", title="Magos mais similares", score_prop="score")
g.add_panel("Magos mais poderosos",
            [(f"Mago {i}", str(12 - i), f"m{i}") for i in range(5)], hint="nível")
g.add_stat("edição", "2026")
g.set_layouts(default="communities")
g.set_ui(hint="explore a rede arcana — clique nos medalhões")
g.set_strings(layout_communities="Escolas",
              layout_communities_desc="cada escola de magia em seu território")

caminho = g.save("customizado.html")
print(f"Grafo salvo em: {caminho}")
