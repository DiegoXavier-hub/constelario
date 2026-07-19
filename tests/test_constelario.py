# -*- coding: utf-8 -*-
"""Testes do Constelário (pytest)."""
import json

import pytest

from constelario import BUILTIN_ICONS, Graph, Theme


def grafo_minimo() -> Graph:
    g = Graph(title="Teste")
    g.add_type("Pessoa", color="#4a9c8c", icon="user")
    g.add_node("a", "Alice", "Pessoa", community=0)
    g.add_node("b", "Bob", "Pessoa", community=1)
    g.add_edge("a", "b", type="CONHECE", props={"score": 0.9})
    return g


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------
def test_no_duplicado_levanta_erro():
    g = grafo_minimo()
    with pytest.raises(ValueError, match="já existe"):
        g.add_node("a", "Outra Alice", "Pessoa")


def test_aresta_para_no_inexistente_levanta_erro_no_render():
    g = grafo_minimo()
    g.add_edge("a", "fantasma")
    with pytest.raises(ValueError, match="fantasma"):
        g.to_config()


def test_grafo_vazio_levanta_erro():
    with pytest.raises(ValueError, match="não tem nós"):
        Graph(title="Vazio").to_config()


def test_icone_desconhecido_levanta_erro():
    g = grafo_minimo()
    g.add_type("X", icon="nao-existe-nao")
    g.add_node("x1", "X1", "X")
    with pytest.raises(ValueError, match="nao-existe-nao"):
        g.to_config()


def test_tier_invalido_levanta_erro():
    g = Graph(title="T")
    with pytest.raises(ValueError, match="tier"):
        g.add_type("X", tier="epico")


def test_layout_default_precisa_estar_habilitado():
    g = grafo_minimo()
    with pytest.raises(ValueError):
        g.set_layouts(default="spiral", enabled=["constel", "layers"])


def test_string_desconhecida_levanta_erro():
    with pytest.raises(ValueError, match="chaves"):
        grafo_minimo().set_strings(chave_inventada="x")


# ---------------------------------------------------------------------------
# Tipos e configuração
# ---------------------------------------------------------------------------
def test_tipo_automatico_ganha_cor_da_paleta():
    g = Graph(title="T")
    g.add_node("n1", "N1", "TipoNovo")
    cfg = g.to_config()
    assert cfg["types"]["TipoNovo"]["color"] == g.theme.palette[0]


def test_ring_automatico_por_ordem_de_registro():
    g = Graph(title="T")
    g.add_type("A")
    g.add_type("B", ring=0)
    g.add_type("C")
    g.add_node("a", "a", "A")
    cfg = g.to_config()
    assert cfg["types"]["A"]["ring"] == 1
    assert cfg["types"]["B"]["ring"] == 0
    assert cfg["types"]["C"]["ring"] == 2


def test_config_completa():
    g = grafo_minimo()
    g.edge_style("CONHECE", color="#fff", width=2)
    g.add_color_mode("m", "Modo", prop="p", colors={"x": "#111"})
    g.add_panel("Painel", [("linha", "1", "a"), ("sem foco", "2")])
    g.inspector_ranking("CONHECE", title="Similares")
    g.add_stat("extra", 42)
    cfg = g.to_config()
    assert cfg["edge_styles"]["CONHECE"]["width"] == 2
    assert cfg["color_modes"][0]["prop"] == "p"
    assert cfg["panels"][0]["rows"][1]["node_id"] is None
    assert cfg["inspector"]["edge_rankings"][0]["edge_type"] == "CONHECE"
    assert cfg["stats_extra"] == [{"label": "extra", "value": "42"}]
    json.dumps(cfg)  # tudo serializável


# ---------------------------------------------------------------------------
# Render HTML
# ---------------------------------------------------------------------------
def test_html_inline_contem_dados_e_bibliotecas():
    html = grafo_minimo().to_html()
    assert "Alice" in html
    assert "constelario-config" in html
    assert "vis.Network" in html or "vis-network" in html.lower()
    assert "__constelario_three_b64" in html
    assert "<!--CONSTELARIO:SCRIPTS-->" not in html


def test_html_cdn_e_menor_e_pinado():
    g = grafo_minimo()
    inline = g.to_html(inline_js=True)
    cdn = g.to_html(inline_js=False)
    assert len(cdn) < len(inline) / 4
    assert "unpkg.com/vis-network@9.1.6" in cdn
    assert 'integrity="sha384-' in cdn


def test_escape_de_script_no_json():
    g = Graph(title="T")
    g.add_node("n1", "</script><b>xss</b>", "X")
    html = g.to_html(inline_js=False)
    corpo = html[html.index("constelario-config"):]
    assert "</script><b>xss</b>" not in corpo  # foi escapado para <\/
    assert "<\\/script>" in corpo


def test_save_e_show_arquivo(tmp_path):
    caminho = grafo_minimo().save(tmp_path / "g.html", inline_js=False)
    conteudo = open(caminho, encoding="utf-8").read()
    assert conteudo.startswith("<!doctype html>")


def test_temas_presets_diferem():
    assert Theme.arcano().accent != Theme().accent
    assert Theme().with_(accent="#123456").accent == "#123456"


def test_icones_builtin_disponiveis():
    for nome in ("dot", "user", "crown", "star", "database"):
        assert nome in BUILTIN_ICONS


def test_from_networkx():
    nx = pytest.importorskip("networkx")
    G = nx.Graph()
    G.add_node(1, label="Um", type="Coisa", community=0, extra="x")
    G.add_node(2, label="Dois", type="Coisa", community=1)
    G.add_edge(1, 2, type="LIGA", peso=3)
    g = Graph.from_networkx(G, title="NX")
    cfg = g.to_config()
    assert len(cfg["nodes"]) == 2
    assert cfg["nodes"][0]["props"] == {"extra": "x"}
    assert cfg["links"][0]["type"] == "LIGA"
    assert cfg["links"][0]["props"] == {"peso": 3}
