# -*- coding: utf-8 -*-
"""Tipos de dados do Constelário: nós, arestas e estilos de tipo.

Tudo aqui é imutável (dataclasses frozen) — o `Graph` guarda coleções desses
objetos e nunca os modifica depois de criados.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

VALID_TIERS = ("keystone", "notable", "small")


def _require_str(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} deve ser uma string não vazia (recebido: {value!r})")
    return value


def _optional_number(value: Any, name: str) -> Optional[float]:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} deve ser numérico (recebido: {value!r})")
    return float(value)


@dataclass(frozen=True)
class Node:
    """Um nó do grafo.

    Atributos:
        id: identificador único (string).
        label: texto exibido no grafo e na busca.
        type: nome do tipo (registrado via ``Graph.add_type`` ou criado
            automaticamente no primeiro uso).
        props: propriedades livres exibidas no painel de inspeção.
        community: id inteiro da comunidade (usado pelo layout "Comunidades"
            e pela coloração por comunidade). Opcional.
        icon: nome de um ícone (builtin ou registrado) que sobrepõe o ícone
            do tipo. Opcional.
        color: cor CSS que sobrepõe a cor do tipo. Opcional.
        size: tamanho fixo do nó; se ausente, o tamanho é proporcional ao
            grau (quantidade de arestas). Opcional.
    """

    id: str
    label: str
    type: str
    props: Mapping[str, Any] = field(default_factory=dict)
    community: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    size: Optional[float] = None

    def __post_init__(self) -> None:
        _require_str(self.id, "Node.id")
        _require_str(self.label, "Node.label")
        _require_str(self.type, "Node.type")
        if self.community is not None and not isinstance(self.community, int):
            raise ValueError(
                f"Node.community deve ser int (recebido: {self.community!r})"
            )
        _optional_number(self.size, "Node.size")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "props": dict(self.props),
            "community": self.community,
            "icon": self.icon,
            "color": self.color,
            "size": self.size,
        }


@dataclass(frozen=True)
class Edge:
    """Uma aresta dirigida entre dois nós (source -> target).

    ``type`` é livre (ex.: "PERTENCE_A", "SIMILAR_A") e pode receber estilo
    próprio via ``Graph.edge_style``. ``props`` aparece no inspetor quando a
    aresta participa de um ranking (``Graph.inspector_ranking``).
    """

    source: str
    target: str
    type: str = ""
    props: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_str(self.source, "Edge.source")
        _require_str(self.target, "Edge.target")

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "props": dict(self.props),
        }


@dataclass(frozen=True)
class TypeStyle:
    """Aparência e comportamento de um tipo de nó.

    Atributos:
        label: nome exibido (legenda, inspetor, busca).
        color: cor CSS base dos nós desse tipo.
        icon: nome do ícone (builtin ou registrado via ``Graph.add_icon``).
        tier: nível de ornamentação do medalhão — "keystone" (máximo, use no
            nó raiz), "notable" (destacado) ou "small" (comum).
        ring: anel do layout Constelação (0 = centro). Se None, é atribuído
            automaticamente pela ordem de registro (começando em 1).
        hidden: se True, o tipo começa desligado na legenda e, no layout
            Espiral/Globo, seus nós formam o halo externo.
    """

    label: str
    color: str
    icon: str = "dot"
    tier: str = "small"
    ring: Optional[float] = None
    hidden: bool = False

    def __post_init__(self) -> None:
        _require_str(self.label, "TypeStyle.label")
        _require_str(self.color, "TypeStyle.color")
        _require_str(self.icon, "TypeStyle.icon")
        if self.tier not in VALID_TIERS:
            raise ValueError(
                f"TypeStyle.tier deve ser um de {VALID_TIERS} (recebido: {self.tier!r})"
            )
        _optional_number(self.ring, "TypeStyle.ring")
