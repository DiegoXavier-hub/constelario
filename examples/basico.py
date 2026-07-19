# -*- coding: utf-8 -*-
"""Exemplo básico do Constelário: um pequeno reino com cidades e pessoas.

Rode com:  python examples/basico.py
"""
from constelario import Graph

g = Graph(title="Reino de Python", subtitle="exemplo básico")

g.add_type("Reino", color="#f2c766", icon="crown", tier="keystone", ring=0)
g.add_type("Cidade", color="#5b8fc7", icon="building", tier="notable")
g.add_type("Pessoa", color="#4a9c8c", icon="user")

g.add_node("r1", "Pythonia", "Reino")
g.add_node("c1", "Vilarejo das Listas", "Cidade", community=0)
g.add_node("c2", "Porto dos Dicionários", "Cidade", community=1)
g.add_node("c3", "Fortaleza das Tuplas", "Cidade", community=2)

pessoas = [
    ("p1", "Alice", 0), ("p2", "Bob", 0), ("p3", "Carol", 0),
    ("p4", "Davi", 1), ("p5", "Elisa", 1), ("p6", "Fábio", 1),
    ("p7", "Gabi", 2), ("p8", "Hugo", 2),
]
for pid, nome, comm in pessoas:
    g.add_node(pid, nome, "Pessoa", community=comm, props={"comunidade": comm})

for cid in ("c1", "c2", "c3"):
    g.add_edge(cid, "r1", type="PERTENCE_A")
casas = {"p1": "c1", "p2": "c1", "p3": "c1", "p4": "c2", "p5": "c2",
         "p6": "c2", "p7": "c3", "p8": "c3"}
for pid, cid in casas.items():
    g.add_edge(pid, cid, type="MORA_EM")
g.add_edge("p1", "p4", type="CONHECE")
g.add_edge("p3", "p7", type="CONHECE")
g.add_edge("p5", "p8", type="CONHECE")

caminho = g.save("basico.html")
print(f"Grafo salvo em: {caminho}")
