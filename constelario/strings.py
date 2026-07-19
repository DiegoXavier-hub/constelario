# -*- coding: utf-8 -*-
"""Textos da interface (pt-BR por padrão).

Qualquer chave pode ser sobrescrita com ``Graph.set_strings(chave="texto")``
— útil para traduzir a UI ou ajustar o vocabulário ao domínio do projeto.
"""
from __future__ import annotations

DEFAULT_STRINGS: dict = {
    # busca
    "search_title": "Buscar",
    "search_placeholder": "Buscar nós...",
    "no_results": "sem resultados",
    # seletor de organização espacial
    "layout_title": "Organização espacial",
    "layout_constel": "Constelação",
    "layout_constel_desc": "anéis radiais por hierarquia de tipo",
    "layout_communities": "Comunidades",
    "layout_communities_desc": "grupos separados no espaço, um por comunidade",
    "layout_layers": "Camadas",
    "layout_layers_desc": "colunas por tipo de nó, fluxo da esquerda p/ direita",
    "layout_spiral": "Espiral · Globo",
    "layout_spiral_desc": "espiral áurea no 2D, globo no 3D",
    # inspetor
    "inspect_title": "Inspecionar",
    "inspect_hint": "clique num nó",
    "inspect_empty": "Clique num nó do grafo para ver seus detalhes e vizinhos.",
    "neighbors_title": "Vizinhos",
    "no_neighbors": "sem vizinhos visíveis",
    "isolate_btn": "◎ isolar vizinhança",
    "show_all_btn": "mostrar tudo",
    "degree_chip": "grau",
    "community_chip": "comunidade",
    # legenda
    "legend_title": "Legenda",
    "legend_all": "todos",
    # painel de comunidades
    "communities_title": "Comunidades",
    "communities_hint": "",
    "community_word": "Comunidade",
    # topbar
    "color_by": "Colorir por",
    "color_type": "Tipo de nó",
    "color_community": "Comunidade",
    "btn_fullscreen": "⛶ Tela cheia",
    "btn_fullscreen_exit": "⛶ Sair da tela cheia",
    "btn_reset": "↺ Resetar vista",
    # palco
    "hint_stage": "arraste o fundo para navegar · roda do mouse para zoom · clique num nó para inspecionar",
    # estatísticas
    "stats_nodes": "nós",
    "stats_edges": "arestas",
    "stats_communities": "comunidades",
    "stats_generated": "gerado em",
    # genéricos
    "empty_panel": "sem dados",
}
