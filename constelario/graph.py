# -*- coding: utf-8 -*-
"""A classe :class:`Graph` — ponto de entrada da biblioteca.

Fluxo típico::

    from constelario import Graph

    g = Graph(title="Meu Grafo")
    g.add_type("Pessoa", color="#4a9c8c", icon="user", tier="notable")
    g.add_node("p1", "Alice", "Pessoa", community=0)
    g.add_node("p2", "Bob", "Pessoa", community=0)
    g.add_edge("p1", "p2", type="CONHECE")
    g.save("grafo.html")     # arquivo único, funciona offline
    g.show()                 # abre no navegador
"""
from __future__ import annotations

import datetime as _dt
import os
import tempfile
import webbrowser
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

from . import _packaging
from .icons import BUILTIN_ICONS
from .model import VALID_TIERS, Edge, Node, TypeStyle, _require_str
from .strings import DEFAULT_STRINGS
from .theme import Theme

LAYOUTS = ("constel", "communities", "layers", "spiral")
_ROW_KEYS = ("label", "value", "node_id")


class Graph:
    """Um grafo de conhecimento renderizável como HTML interativo único."""

    def __init__(
        self,
        title: str = "Constelário",
        subtitle: str = "",
        *,
        theme: Optional[Theme] = None,
        generated_at: Optional[str] = None,
    ) -> None:
        _require_str(title, "title")
        self.title = title
        self.subtitle = subtitle
        self.theme = theme if theme is not None else Theme()
        self.generated_at = generated_at or _dt.datetime.now().isoformat(timespec="seconds")

        self._types: "dict[str, TypeStyle]" = {}
        self._type_order: "list[str]" = []
        self._nodes: "dict[str, Node]" = {}
        self._edges: "list[Edge]" = []
        self._icons: "dict[str, str]" = {}
        self._edge_styles: "dict[str, dict]" = {}
        self._color_modes: "list[dict]" = []
        self._panels: "list[dict]" = []
        self._edge_rankings: "list[dict]" = []
        self._hidden_props: "list[str]" = []
        self._stats_extra: "list[dict]" = []
        self._strings: "dict[str, str]" = {}
        self._node_size = {"min": 7.0, "max": 46.0}
        self._layouts = {"default": "constel", "enabled": list(LAYOUTS),
                         "sync_community_color": True}
        self._ui = {"search": True, "legend": True, "inspector": True,
                    "stats": True, "fullscreen": True, "communities_panel": True,
                    "mode": "2d", "hint": None}

    # ------------------------------------------------------------------
    # Tipos, ícones, nós e arestas
    # ------------------------------------------------------------------
    def add_type(
        self,
        name: str,
        *,
        label: Optional[str] = None,
        color: Optional[str] = None,
        icon: str = "dot",
        tier: str = "small",
        ring: Optional[float] = None,
        hidden: bool = False,
    ) -> "Graph":
        """Registra um tipo de nó (aparência + comportamento).

        ``color`` ausente recebe a próxima cor da paleta do tema. Ver
        :class:`constelario.model.TypeStyle` para o significado de cada campo.
        """
        _require_str(name, "nome do tipo")
        if name in self._types:
            raise ValueError(f"tipo {name!r} já registrado")
        if color is None:
            palette = self.theme.palette
            color = palette[len(self._types) % len(palette)]
        self._types[name] = TypeStyle(label=label or name, color=color, icon=icon,
                                      tier=tier, ring=ring, hidden=hidden)
        self._type_order.append(name)
        return self

    def add_icon(self, name: str, svg: str) -> "Graph":
        """Registra um glifo SVG próprio (miolo de um viewBox 24x24 em stroke).

        Exemplo: ``g.add_icon("anel", '<circle cx="12" cy="12" r="8"/>')``.
        """
        _require_str(name, "nome do ícone")
        _require_str(svg, "svg do ícone")
        self._icons[name] = svg
        return self

    def add_node(
        self,
        node_id: str,
        label: str,
        type_name: str,
        *,
        props: Optional[Mapping[str, Any]] = None,
        community: Optional[int] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        size: Optional[float] = None,
    ) -> "Graph":
        """Adiciona um nó. Tipos desconhecidos são registrados automaticamente
        (cor da paleta, ícone "dot"). IDs duplicados levantam ``ValueError``."""
        if node_id in self._nodes:
            raise ValueError(f"nó com id {node_id!r} já existe")
        if type_name not in self._types:
            self.add_type(type_name)
        self._nodes[node_id] = Node(id=node_id, label=label, type=type_name,
                                    props=dict(props or {}), community=community,
                                    icon=icon, color=color, size=size)
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        *,
        type: str = "",
        props: Optional[Mapping[str, Any]] = None,
    ) -> "Graph":
        """Adiciona uma aresta dirigida. Os endpoints são validados no render."""
        self._edges.append(Edge(source=source, target=target, type=type,
                                props=dict(props or {})))
        return self

    # ------------------------------------------------------------------
    # Estilo e comportamento
    # ------------------------------------------------------------------
    def edge_style(
        self,
        edge_type: str,
        *,
        color: Optional[str] = None,
        width: Optional[float] = None,
        opacity: Optional[float] = None,
        dashes: Optional[bool] = None,
    ) -> "Graph":
        """Define o estilo das arestas de um tipo. Use ``edge_type="default"``
        para o estilo base de todas as arestas sem estilo próprio."""
        style = {k: v for k, v in
                 (("color", color), ("width", width), ("opacity", opacity),
                  ("dashes", dashes)) if v is not None}
        if not style:
            raise ValueError("edge_style exige ao menos um de color/width/opacity/dashes")
        self._edge_styles.setdefault(edge_type, {}).update(style)
        return self

    def add_color_mode(
        self,
        key: str,
        label: str,
        *,
        prop: str,
        colors: Optional[Mapping[str, str]] = None,
        fallback: str = "#5a4c34",
    ) -> "Graph":
        """Adiciona um modo no seletor "Colorir por" baseado numa propriedade
        dos nós. ``colors`` mapeia valor da propriedade -> cor; valores fora
        do mapa (ou ``colors=None``) recebem cores da paleta automaticamente."""
        _require_str(key, "key do modo de cor")
        if key in ("type", "community") or any(m["key"] == key for m in self._color_modes):
            raise ValueError(f"modo de cor {key!r} já existe")
        self._color_modes.append({"key": key, "label": label, "by": "prop",
                                  "prop": prop, "colors": dict(colors or {}),
                                  "fallback": fallback})
        return self

    def add_panel(
        self,
        title: str,
        rows: Iterable[Union[Mapping[str, Any], Sequence[Any]]],
        *,
        hint: str = "",
    ) -> "Graph":
        """Adiciona um painel de ranking na barra lateral.

        Cada linha é ``(label, valor)`` ou ``(label, valor, node_id)`` — com
        ``node_id``, clicar na linha foca o nó no grafo. Também aceita dicts
        com as chaves ``label``, ``value`` e ``node_id``.
        """
        _require_str(title, "título do painel")
        norm = []
        for row in rows:
            if isinstance(row, Mapping):
                item = {k: row.get(k) for k in _ROW_KEYS}
            else:
                seq = list(row)
                if len(seq) not in (2, 3):
                    raise ValueError(
                        f"linha de painel deve ter 2 ou 3 itens (recebido: {row!r})")
                item = {"label": seq[0], "value": seq[1],
                        "node_id": seq[2] if len(seq) == 3 else None}
            item["label"] = str(item["label"])
            item["value"] = "" if item["value"] is None else str(item["value"])
            norm.append(item)
        self._panels.append({"title": title, "hint": hint, "rows": norm})
        return self

    def inspector_ranking(
        self,
        edge_type: str,
        *,
        title: str,
        score_prop: str = "score",
        decimals: int = 3,
    ) -> "Graph":
        """No inspetor, lista os vizinhos conectados por ``edge_type`` ordenados
        pela propriedade numérica ``score_prop`` da aresta (ex.: similaridade)."""
        _require_str(edge_type, "edge_type")
        _require_str(title, "título do ranking")
        self._edge_rankings.append({"edge_type": edge_type, "title": title,
                                    "score_prop": score_prop, "decimals": int(decimals)})
        return self

    def hide_props(self, *names: str) -> "Graph":
        """Oculta propriedades no painel de inspeção (ex.: ids internos)."""
        self._hidden_props.extend(names)
        return self

    def add_stat(self, label: str, value: Any) -> "Graph":
        """Acrescenta uma linha própria na caixa de estatísticas."""
        self._stats_extra.append({"label": str(label), "value": str(value)})
        return self

    def set_strings(self, **overrides: str) -> "Graph":
        """Sobrescreve textos da interface (chaves em ``constelario.strings``)."""
        unknown = set(overrides) - set(DEFAULT_STRINGS)
        if unknown:
            raise ValueError(f"chaves de string desconhecidas: {sorted(unknown)}")
        self._strings.update(overrides)
        return self

    def set_layouts(
        self,
        default: Optional[str] = None,
        enabled: Optional[Sequence[str]] = None,
        sync_community_color: Optional[bool] = None,
    ) -> "Graph":
        """Configura os layouts: qual abre por padrão, quais aparecem no menu
        e se escolher "Comunidades" troca a coloração junto."""
        if enabled is not None:
            enabled = list(enabled)
            bad = [x for x in enabled if x not in LAYOUTS]
            if bad or not enabled:
                raise ValueError(f"layouts válidos: {LAYOUTS} (recebido: {enabled})")
            self._layouts["enabled"] = enabled
        if default is not None:
            if default not in self._layouts["enabled"]:
                raise ValueError(
                    f"default {default!r} precisa estar entre os habilitados "
                    f"{self._layouts['enabled']}")
            self._layouts["default"] = default
        if sync_community_color is not None:
            self._layouts["sync_community_color"] = bool(sync_community_color)
        return self

    def set_node_size(self, min: Optional[float] = None, max: Optional[float] = None) -> "Graph":
        """Faixa de tamanho dos nós (o tamanho escala com o grau do nó)."""
        if min is not None:
            self._node_size["min"] = float(min)
        if max is not None:
            self._node_size["max"] = float(max)
        if self._node_size["min"] <= 0 or self._node_size["max"] < self._node_size["min"]:
            raise ValueError(f"faixa de tamanho inválida: {self._node_size}")
        return self

    def set_ui(
        self,
        *,
        search: Optional[bool] = None,
        legend: Optional[bool] = None,
        inspector: Optional[bool] = None,
        stats: Optional[bool] = None,
        fullscreen: Optional[bool] = None,
        communities_panel: Optional[bool] = None,
        mode: Optional[str] = None,
        hint: Optional[str] = None,
    ) -> "Graph":
        """Liga/desliga blocos da interface e define o modo inicial (2d/3d)."""
        for key, val in (("search", search), ("legend", legend),
                         ("inspector", inspector), ("stats", stats),
                         ("fullscreen", fullscreen),
                         ("communities_panel", communities_panel)):
            if val is not None:
                self._ui[key] = bool(val)
        if mode is not None:
            if mode not in ("2d", "3d"):
                raise ValueError(f"mode deve ser '2d' ou '3d' (recebido: {mode!r})")
            self._ui["mode"] = mode
        if hint is not None:
            self._ui["hint"] = hint
        return self

    # ------------------------------------------------------------------
    # Interoperabilidade
    # ------------------------------------------------------------------
    @classmethod
    def from_networkx(
        cls,
        nx_graph,
        *,
        title: str = "Constelário",
        type_attr: str = "type",
        label_attr: str = "label",
        community_attr: str = "community",
        default_type: str = "Nó",
        **kwargs,
    ) -> "Graph":
        """Cria um :class:`Graph` a partir de um grafo networkx.

        Os atributos de nó ``type_attr``/``label_attr``/``community_attr`` viram
        tipo, rótulo e comunidade; os demais atributos viram ``props``. Atributos
        de aresta viram ``props`` da aresta (o atributo ``type`` vira o tipo).
        """
        g = cls(title=title, **kwargs)
        for node_id, data in nx_graph.nodes(data=True):
            data = dict(data)
            ntype = str(data.pop(type_attr, default_type))
            label = str(data.pop(label_attr, node_id))
            community = data.pop(community_attr, None)
            if community is not None:
                community = int(community)
            g.add_node(str(node_id), label, ntype, props=data, community=community)
        for source, target, data in nx_graph.edges(data=True):
            data = dict(data)
            etype = str(data.pop("type", ""))
            g.add_edge(str(source), str(target), type=etype, props=data)
        return g

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def _resolved_types(self) -> dict:
        """Tipos com ``ring`` resolvido: os sem anel recebem 1, 2, 3... pela
        ordem de registro (0 é reservado para quem pedir explicitamente)."""
        out = {}
        next_ring = 1.0
        for name in self._type_order:
            ts = self._types[name]
            ring = ts.ring
            if ring is None:
                ring = next_ring
                next_ring += 1.0
            out[name] = {"label": ts.label, "color": ts.color, "icon": ts.icon,
                         "tier": ts.tier, "ring": ring, "hidden": ts.hidden}
        return out

    def _validate(self) -> None:
        if not self._nodes:
            raise ValueError("o grafo não tem nós — adicione com add_node()")
        missing = []
        for e in self._edges:
            for endpoint in (e.source, e.target):
                if endpoint not in self._nodes:
                    missing.append(endpoint)
        if missing:
            sample = ", ".join(repr(m) for m in sorted(set(missing))[:5])
            raise ValueError(
                f"{len(set(missing))} endpoint(s) de aresta não existem como nó: "
                f"{sample}...")
        known_icons = set(BUILTIN_ICONS) | set(self._icons)
        for name, ts in self._types.items():
            if ts.icon not in known_icons:
                raise ValueError(
                    f"tipo {name!r} usa ícone desconhecido {ts.icon!r} "
                    f"(builtin: {sorted(BUILTIN_ICONS)})")
        for n in self._nodes.values():
            if n.icon is not None and n.icon not in known_icons:
                raise ValueError(f"nó {n.id!r} usa ícone desconhecido {n.icon!r}")

    def to_config(self) -> dict:
        """Monta o dicionário de configuração embutido no HTML (JSON)."""
        self._validate()
        strings = dict(DEFAULT_STRINGS)
        strings.update(self._strings)
        edge_styles = {"default": {"color": "#4a3c28", "width": 0.55,
                                   "opacity": 0.12, "dashes": False}}
        for etype, style in self._edge_styles.items():
            edge_styles.setdefault(etype, {}).update(style)
        return {
            "meta": {"title": self.title, "subtitle": self.subtitle,
                     "generated_at": self.generated_at},
            "strings": strings,
            "theme": self.theme.to_dict(),
            "types": self._resolved_types(),
            "icons": {**BUILTIN_ICONS, **self._icons},
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "links": [e.to_dict() for e in self._edges],
            "edge_styles": edge_styles,
            "color_modes": list(self._color_modes),
            "node_size": dict(self._node_size),
            "layouts": dict(self._layouts),
            "ui": dict(self._ui),
            "panels": list(self._panels),
            "inspector": {"edge_rankings": list(self._edge_rankings),
                          "hide_props": list(self._hidden_props)},
            "stats_extra": list(self._stats_extra),
        }

    def to_html(self, *, inline_js: bool = True) -> str:
        """Retorna o HTML completo. ``inline_js=True`` (padrão) embute as
        bibliotecas JS no arquivo (funciona offline); ``False`` usa CDN com
        integridade (arquivo ~2.6 MB menor, exige internet ao abrir)."""
        return _packaging.render(self.to_config(), inline_js=inline_js)

    def save(self, path: Union[str, os.PathLike], *, inline_js: bool = True) -> str:
        """Grava o HTML em ``path`` e retorna o caminho absoluto."""
        html = self.to_html(inline_js=inline_js)
        path = os.path.abspath(os.fspath(path))
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    def show(self, *, inline_js: bool = True) -> str:
        """Salva num arquivo temporário e abre no navegador padrão."""
        fd, path = tempfile.mkstemp(prefix="constelario_", suffix=".html")
        os.close(fd)
        self.save(path, inline_js=inline_js)
        webbrowser.open("file:///" + path.replace(os.sep, "/").lstrip("/"))
        return path
