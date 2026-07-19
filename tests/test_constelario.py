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


# ---------------------------------------------------------------------------
# Robustez (fixes da revisão adversarial)
# ---------------------------------------------------------------------------
def test_nan_e_inf_viram_null_e_nao_quebram_json():
    g = Graph(title="T")
    g.add_node("a", "A", "X", props={"score": float("nan"), "z": float("inf")},
               size=None)
    g.add_type("Y", ring=float("inf"))
    g.add_node("b", "B", "Y")
    html = g.to_html(inline_js=False)
    corpo = html[html.index("constelario-config"):]
    assert "NaN" not in corpo and "Infinity" not in corpo
    # a config precisa continuar sendo JSON parseável
    ini = corpo.index(">") + 1
    fim = corpo.index("</script>", ini)
    json.loads(corpo[ini:fim].replace("<\\/", "</"))


def test_props_tipos_exoticos_serializam(tmp_path):
    import datetime as dt
    g = Graph(title="T")
    g.add_node("a", "A", "X", props={"quando": dt.date(2026, 7, 19),
                                     "tags": {"x", "y"}})
    caminho = g.save(tmp_path / "g.html", inline_js=False)  # não deve levantar
    assert "2026-07-19" in open(caminho, encoding="utf-8").read()


def test_community_bool_rejeitada():
    g = Graph(title="T")
    with pytest.raises(ValueError, match="community"):
        g.add_node("a", "A", "X", community=True)


def test_size_nao_positivo_rejeitado():
    g = Graph(title="T")
    with pytest.raises(ValueError, match="size"):
        g.add_node("a", "A", "X", size=0)


def test_add_node_invalido_nao_registra_tipo_fantasma():
    g = Graph(title="T")
    with pytest.raises(ValueError):
        g.add_node("a", "A", "Pessoa", community=1.5)
    # o tipo não pode ter ficado registrado pela tentativa que falhou
    g.add_type("Pessoa", color="#123456")
    g.add_node("a", "Alice", "Pessoa")
    assert g.to_config()["types"]["Pessoa"]["color"] == "#123456"


def test_add_panel_rejeita_string():
    g = grafo_minimo()
    with pytest.raises(ValueError, match="string"):
        g.add_panel("P", ["Alice", "Bob"])


def test_set_node_size_invalido_nao_corrompe_estado():
    g = grafo_minimo()
    with pytest.raises(ValueError):
        g.set_node_size(min=0)
    assert g.to_config()["node_size"]["min"] > 0


def test_set_layouts_enabled_sem_default_valido_falha_sem_mutar():
    g = grafo_minimo()
    antes = g.to_config()["layouts"]["enabled"]
    with pytest.raises(ValueError):
        g.set_layouts(enabled=["communities", "layers"])  # default 'constel' ficaria órfão
    assert g.to_config()["layouts"]["enabled"] == antes  # nada mudou


def test_inspector_ranking_decimals_fora_de_faixa():
    g = grafo_minimo()
    with pytest.raises(ValueError, match="decimals"):
        g.inspector_ranking("CONHECE", title="X", decimals=-1)


def test_palette_vazia_nao_quebra():
    g = Graph(title="T", theme=Theme().with_(palette=[]))
    g.add_node("a", "A", "X")  # não deve levantar ZeroDivisionError
    assert g.to_config()["types"]["X"]["color"]


def test_from_edges_lista_de_dicts():
    edges = [
        {"de": "a", "para": "b", "rel": "AMIGO", "peso": 3},
        {"de": "a", "para": "c", "rel": "AMIGO", "peso": 1},
    ]
    g = Graph.from_edges(edges, source="de", target="para",
                         edge_type="rel", source_type="Pessoa")
    cfg = g.to_config()
    assert len(cfg["nodes"]) == 3          # a, b, c auto-criados
    assert {n["type"] for n in cfg["nodes"]} == {"Pessoa"}
    assert cfg["links"][0]["type"] == "AMIGO"
    assert cfg["links"][0]["props"]["peso"] == 3   # coluna extra vira prop


def test_from_edges_bipartido_com_tabela_de_nos():
    edges = [{"user": "u1", "item": "i1"}, {"user": "u2", "item": "i1"}]
    nodes = [{"item": "i1", "nome": "Espada", "cat": 5}]
    g = Graph.from_edges(edges, source="user", target="item",
                         source_type="Usuário", target_type="Produto",
                         nodes=nodes, node_id="item", node_label="nome",
                         node_community="cat")
    by_id = {n["id"]: n for n in g.to_config()["nodes"]}
    assert by_id["u1"]["type"] == "Usuário"
    assert by_id["i1"]["type"] == "Produto"
    assert by_id["i1"]["label"] == "Espada"
    assert by_id["i1"]["community"] == 5


def test_from_edges_csv(tmp_path):
    csv_path = tmp_path / "arestas.csv"
    csv_path.write_text("de,para,rel,score\na,b,SIMILAR,0.9\nb,c,SIMILAR,0.4\n",
                        encoding="utf-8")
    g = Graph.from_edges(str(csv_path), source="de", target="para", edge_type="rel")
    cfg = g.to_config()
    assert len(cfg["nodes"]) == 3
    # score numérico coerido (não veio como string "0.9")
    assert cfg["links"][0]["props"]["score"] == 0.9


def test_from_edges_extensao_invalida(tmp_path):
    with pytest.raises(ValueError, match="extensão"):
        Graph.from_edges(str(tmp_path / "x.txt"), source="a", target="b")


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
