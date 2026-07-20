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
import pathlib
import tempfile
import webbrowser
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

from . import _packaging, _tabular
from .icons import BUILTIN_ICONS
from .model import VALID_TIERS, Edge, Node, TypeStyle, _require_str
from .strings import DEFAULT_STRINGS
from .theme import DEFAULT_PALETTE, Theme

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
        self._edge_weight: "Optional[dict]" = None
        # Velocidades do mouse no 3D. Os defaults do TrackballControls
        # (rotate 1.0 / zoom 1.2 / pan 0.3) são agressivos em telas grandes;
        # aqui o padrão já nasce calmo e o usuário ajusta pelo slider.
        self._controls = {"rotate": 0.5, "zoom": 0.7, "pan": 0.2,
                          "sensitivity": 1.0, "slider": True}
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
            palette = self.theme.palette or DEFAULT_PALETTE
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
        # constrói o nó (valida label/community/size/color) ANTES de registrar
        # o tipo — assim uma entrada inválida não deixa um tipo-fantasma
        # consumindo cor da paleta.
        node = Node(id=node_id, label=label, type=type_name,
                    props=dict(props or {}), community=community,
                    icon=icon, color=color, size=size)
        if type_name not in self._types:
            self.add_type(type_name)
        self._nodes[node_id] = node
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
            elif isinstance(row, str):
                # uma str também é Sequence — sem esta guarda, "Bob" viraria
                # três colunas ('B','o','b'). Exija tupla/lista explícita.
                raise ValueError(
                    f"cada linha do painel deve ser uma tupla (label, valor[, node_id]), "
                    f"não uma string (recebido: {row!r})")
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
        decimals = int(decimals)
        # toFixed() no navegador só aceita 0..100; fora disso o inspetor
        # inteiro deixaria de renderizar com RangeError.
        if not 0 <= decimals <= 20:
            raise ValueError(f"decimals deve estar entre 0 e 20 (recebido: {decimals})")
        self._edge_rankings.append({"edge_type": edge_type, "title": title,
                                    "score_prop": score_prop, "decimals": decimals})
        return self

    def set_edge_weight(self, prop: str, *, min_width: float = 0.4,
                        max_width: float = 4.0, scale_opacity: bool = True) -> "Graph":
        """Faz a **largura** (e opcionalmente a opacidade) de cada aresta escalar
        pela propriedade numérica ``prop`` — o "peso" da aresta, como num grafo
        de conhecimento. Os valores são normalizados entre todas as arestas.

        Combine com ``edge_style`` (cor por tipo) e ``inspector_ranking`` (para
        listar vizinhos por peso). As estratégias de ``constelario.edges`` já
        gravam um peso (``score``/``dist``/``peso``) pronto para usar aqui.
        """
        _require_str(prop, "prop de peso")
        if max_width < min_width or min_width <= 0:
            raise ValueError(f"faixa de largura inválida (0 < min <= max): "
                             f"min={min_width}, max={max_width}")
        self._edge_weight = {"prop": prop, "min": float(min_width),
                             "max": float(max_width), "opacity": bool(scale_opacity)}
        return self

    def set_controls(self, *, rotate_speed: Optional[float] = None,
                     zoom_speed: Optional[float] = None,
                     pan_speed: Optional[float] = None,
                     sensitivity: Optional[float] = None,
                     slider: Optional[bool] = None) -> "Graph":
        """Ajusta a sensibilidade do mouse na visualização 3D.

        ``pan_speed`` é o arrasto com o **botão direito**, ``rotate_speed`` o
        arrasto com o esquerdo e ``zoom_speed`` a roda. ``sensitivity`` é um
        multiplicador global aplicado sobre os três (é a posição inicial do
        slider "Sensibilidade do mouse" da barra lateral; ``slider=False``
        esconde esse controle).
        """
        for key, val in (("rotate", rotate_speed), ("zoom", zoom_speed),
                         ("pan", pan_speed), ("sensitivity", sensitivity)):
            if val is None:
                continue
            val = float(val)
            if val <= 0:
                raise ValueError(f"{key}: velocidade deve ser > 0 (recebido: {val})")
            self._controls[key] = val
        if slider is not None:
            self._controls["slider"] = bool(slider)
        return self

    def connect(self, strategy) -> "Graph":
        """Aplica uma estratégia de conexão (de ``constelario.edges``) sobre os
        nós atuais, criando as arestas. Encadeável; pode ser chamado várias vezes
        com estratégias diferentes."""
        for e in strategy.build(self):
            self.add_edge(e["source"], e["target"],
                          type=e.get("type", ""), props=e.get("props") or {})
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
        # valida TUDO antes de gravar qualquer campo — uma chamada que falha
        # não pode deixar o objeto num estado parcialmente alterado.
        new_enabled = self._layouts["enabled"]
        if enabled is not None:
            new_enabled = list(enabled)
            bad = [x for x in new_enabled if x not in LAYOUTS]
            if bad or not new_enabled:
                raise ValueError(f"layouts válidos: {LAYOUTS} (recebido: {new_enabled})")
        new_default = default if default is not None else self._layouts["default"]
        if new_default not in new_enabled:
            raise ValueError(
                f"o layout padrão {new_default!r} precisa estar entre os habilitados "
                f"{new_enabled} — passe default= junto ao mudar enabled=")
        self._layouts["enabled"] = new_enabled
        self._layouts["default"] = new_default
        if sync_community_color is not None:
            self._layouts["sync_community_color"] = bool(sync_community_color)
        return self

    def set_node_size(self, min: Optional[float] = None, max: Optional[float] = None) -> "Graph":
        """Faixa de tamanho dos nós (o tamanho escala com o grau do nó)."""
        new_min = float(min) if min is not None else self._node_size["min"]
        new_max = float(max) if max is not None else self._node_size["max"]
        # valida antes de gravar: uma chamada inválida não pode corromper a faixa.
        if new_min <= 0 or new_max < new_min:
            raise ValueError(
                f"faixa de tamanho inválida: min={new_min}, max={new_max} "
                "(exige 0 < min <= max)")
        self._node_size["min"] = new_min
        self._node_size["max"] = new_max
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

    @classmethod
    def from_edges(
        cls,
        edges: Any,
        *,
        source: str,
        target: str,
        edge_type: Optional[str] = None,
        edge_props: Optional[Sequence[str]] = None,
        weight: Optional[str] = None,
        source_type: str = "Nó",
        target_type: Optional[str] = None,
        nodes: Optional[Any] = None,
        node_id: str = "id",
        node_label: Optional[str] = None,
        node_type: Optional[str] = None,
        node_community: Optional[str] = None,
        node_props: Optional[Sequence[str]] = None,
        title: str = "Constelário",
        **kwargs,
    ) -> "Graph":
        """Cria um :class:`Graph` a partir de uma **lista de arestas** tabular.

        ``edges`` pode ser um caminho ``.csv``/``.parquet``, um ``DataFrame`` do
        pandas ou um iterável de dicionários — cada linha é uma ligação, com uma
        coluna de origem (``source``) e uma de destino (``target``). Os nós são
        criados automaticamente a partir dos endpoints.

        Parâmetros de aresta:
            source, target: nomes das colunas dos endpoints (obrigatórios).
            edge_type: coluna cujo valor vira o tipo da aresta (ex.: a relação).
            edge_props: colunas que viram ``props`` da aresta. ``None`` (padrão)
                usa todas as colunas exceto source/target/edge_type; ``[]`` = nenhuma.
            weight: coluna numérica de peso da aresta — a largura da linha passa a
                escalar por ela (equivale a chamar :meth:`set_edge_weight`).

        Tipagem dos nós auto-criados:
            source_type / target_type: tipo dos nós de origem / destino (útil em
                grafos bipartidos, ex.: "Usuário" → "Produto"). ``target_type``
                ausente reusa ``source_type``. Cada id recebe o tipo do primeiro
                papel em que aparece.

        Tabela de nós opcional (``nodes``) — mesmo tipo de fonte de ``edges`` —
        para dar rótulo, tipo, comunidade e propriedades aos nós:
            node_id: coluna do identificador (casa com source/target). Padrão "id".
            node_label: coluna do rótulo (padrão: o próprio id).
            node_type: coluna do tipo (padrão: ``source_type``).
            node_community: coluna da comunidade (convertida para int).
            node_props: colunas que viram ``props`` (padrão: todas as demais).

        ``**kwargs`` vai para o construtor (``theme``, ``subtitle``...).

        Exemplo::

            g = Graph.from_edges("ligacoes.csv", source="de", target="para",
                                 edge_type="relacao")
            g = Graph.from_edges(df_arestas, source="user", target="item",
                                 source_type="Usuário", target_type="Produto",
                                 nodes=df_itens, node_id="item", node_label="nome")
        """
        g = cls(title=title, **kwargs)
        edge_rows = _tabular.read_rows(edges)
        known: set = set()

        # tipagem por papel: cada id herda o tipo do primeiro papel (origem /
        # destino) em que aparece nas arestas. É o fallback quando a tabela de
        # nós não tiver uma coluna de tipo — essencial no caso bipartido.
        tgt_type = target_type or source_type
        auto_type: dict = {}
        for row in edge_rows:
            s, t = row.get(source), row.get(target)
            if s is not None:
                auto_type.setdefault(str(s), source_type)
            if t is not None:
                auto_type.setdefault(str(t), tgt_type)

        # 1) nós explícitos, se houver tabela de nós
        if nodes is not None:
            n_exclude = {node_id, node_label, node_type, node_community}
            for row in _tabular.read_rows(nodes):
                raw = row.get(node_id)
                if raw is None:
                    continue
                nid = str(raw)
                if nid in known:
                    continue
                label = str(row.get(node_label) if node_label and row.get(node_label) is not None else nid)
                if node_type and row.get(node_type) is not None:
                    ntype = str(row.get(node_type))
                else:
                    ntype = auto_type.get(nid, source_type)
                community = row.get(node_community) if node_community else None
                if community is not None:
                    try:
                        community = int(community)
                    except (TypeError, ValueError):
                        community = None
                props = _tabular.pick_props(row, node_props, n_exclude)
                g.add_node(nid, label, ntype, props=props, community=community)
                known.add(nid)

        # 2) endpoints ausentes da tabela de nós
        for nid, ntype in auto_type.items():
            if nid not in known:
                g.add_node(nid, nid, ntype)
                known.add(nid)

        # 3) arestas
        e_exclude = {source, target, edge_type}
        for row in edge_rows:
            s, t = row.get(source), row.get(target)
            if s is None or t is None:
                continue
            etype = str(row.get(edge_type)) if edge_type and row.get(edge_type) is not None else ""
            props = _tabular.pick_props(row, edge_props, e_exclude)
            g.add_edge(str(s), str(t), type=etype, props=props)
        if weight:
            g.set_edge_weight(weight)
        return g

    @classmethod
    def from_table(
        cls,
        table: Any,
        *,
        id: str,
        label: Optional[str] = None,
        type: Optional[str] = None,
        community: Optional[str] = None,
        props: Optional[Sequence[str]] = None,
        default_type: str = "Nó",
        connect: Optional[Any] = None,
        title: str = "Constelário",
        **kwargs,
    ) -> "Graph":
        """Cria um :class:`Graph` a partir de uma tabela de **nós** e conecta-os
        por uma (ou várias) estratégia(s) de ``constelario.edges``.

        ``table`` pode ser um caminho ``.csv``/``.parquet``, ``DataFrame`` ou
        iterável de dicts. Cada linha vira um nó.

        Mapeamento de colunas:
            id: coluna do identificador único (obrigatória).
            label: coluna do rótulo (padrão: o próprio id).
            type: coluna do tipo do nó (padrão: ``default_type`` para todos).
            community: coluna da comunidade (convertida para int).
            props: colunas que viram ``props`` (padrão: todas as demais) — são
                elas que as estratégias de similaridade leem como features.

        connect: uma estratégia de ``constelario.edges`` (ou uma lista delas)
            aplicada após criar os nós. Ex.: ``connect=edges.knn(["x","y"], k=5)``.

        Exemplo::

            from constelario import Graph, edges
            g = Graph.from_table("alunos.csv", id="matricula", label="nome",
                                 community="turma",
                                 connect=edges.knn(["nota", "faltas"], k=4))
        """
        g = cls(title=title, **kwargs)
        exclude = {id, label, type, community}
        for row in _tabular.read_rows(table):
            raw = row.get(id)
            if raw is None:
                continue
            nid = str(raw)
            if nid in g._nodes:
                continue
            lbl = str(row.get(label) if label and row.get(label) is not None else nid)
            ntype = str(row.get(type)) if type and row.get(type) is not None else default_type
            comm = row.get(community) if community else None
            if comm is not None:
                try:
                    comm = int(comm)
                except (TypeError, ValueError):
                    comm = None
            g.add_node(nid, lbl, ntype, props=_tabular.pick_props(row, props, exclude),
                       community=comm)
        if connect is not None:
            for strategy in (connect if isinstance(connect, (list, tuple)) else [connect]):
                g.connect(strategy)
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
            "edge_weight": dict(self._edge_weight) if self._edge_weight else None,
            "color_modes": list(self._color_modes),
            "node_size": dict(self._node_size),
            "controls": dict(self._controls),
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
        """Salva num arquivo temporário e abre no navegador padrão.

        Nota: o arquivo temporário persiste (não pode ser apagado logo após
        abrir, pois o navegador o carrega de forma assíncrona).
        """
        fd, path = tempfile.mkstemp(prefix="constelario_", suffix=".html")
        os.close(fd)
        self.save(path, inline_js=inline_js)
        # Path.as_uri() resolve drive (file:///C:/...), UNC (\\srv\share) e
        # percent-encoding (#, %, espaços) — bem mais robusto que montar à mão.
        webbrowser.open(pathlib.Path(path).as_uri())
        return path
