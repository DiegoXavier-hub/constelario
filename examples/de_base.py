# -*- coding: utf-8 -*-
"""Carregar o grafo a partir de uma base tabular e escolher como criar as arestas.

Mostra os dois caminhos:
  (1) lista de arestas com PESO  → Graph.from_edges (grafo de conhecimento).
  (2) tabela de nós + estratégia → Graph.from_table + constelario.edges.

Rode com:  python examples/de_base.py
(usa dados sintéticos; troque pelos seus .csv/.parquet reais.)
"""
import csv
import os
import tempfile

from constelario import Graph, Theme, edges

tmp = tempfile.mkdtemp(prefix="constelario_ex_")

# ------------------------------------------------------------------ (1)
# Uma lista de arestas com peso — como uma tabela de comércio bilateral,
# citações, transferências... cada linha é uma ligação com um valor.
arestas_csv = os.path.join(tmp, "fluxos.csv")
with open(arestas_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["origem", "destino", "relacao", "valor_usd"])
    w.writerow(["Brasil", "EUA", "EXPORTA", 4_000_000])
    w.writerow(["Brasil", "França", "EXPORTA", 1_300_000])
    w.writerow(["Brasil", "China", "EXPORTA", 900_000])
    w.writerow(["Brasil", "Argentina", "EXPORTA", 300_000])
    w.writerow(["EUA", "México", "EXPORTA", 1_100_000])

g = Graph.from_edges(
    arestas_csv, source="origem", target="destino",
    edge_type="relacao", weight="valor_usd",     # a espessura da linha = valor
    source_type="País", title="Fluxos de comércio",
    theme=Theme.esmeralda(),
)
g.edge_style("EXPORTA", color="#7fe0b2")
g.inspector_ranking("EXPORTA", title="Maiores fluxos", score_prop="valor_usd", decimals=0)
print("(1) fluxos com peso:", g.save(os.path.join(tmp, "fluxos.html")))

# ------------------------------------------------------------------ (2)
# Uma tabela de nós com atributos numéricos — conecta por similaridade.
nos_csv = os.path.join(tmp, "paises.csv")
with open(nos_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["pais", "demanda_kg", "preco_usd_kg", "regiao"])
    w.writerow(["EUA", 18767, 171.5, "america"])
    w.writerow(["França", 24937, 123.6, "europa"])
    w.writerow(["Alemanha", 22100, 130.2, "europa"])
    w.writerow(["China", 9800, 95.0, "asia"])
    w.writerow(["Japão", 10200, 98.4, "asia"])
    w.writerow(["Argentina", 3100, 60.0, "america"])

g2 = Graph.from_table(
    nos_csv, id="pais", label="pais", community=None,
    title="Países por perfil de demanda", theme=Theme.arcano(),
    connect=edges.knn(["demanda_kg", "preco_usd_kg"], k=2,
                      metric="euclidean", standardize=True),
)
g2.set_edge_weight("score")                       # linha mais grossa = mais parecido
g2.add_color_mode("regiao", "Região", prop="regiao")
g2.inspector_ranking("SIMILAR", title="Mais parecidos", score_prop="score")
print("(2) similaridade knn:", g2.save(os.path.join(tmp, "paises.html")))
