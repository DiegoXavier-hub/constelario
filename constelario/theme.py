# -*- coding: utf-8 -*-
"""Tema visual do Constelário.

Todas as cores da interface saem daqui e viram variáveis CSS no HTML final.
``accent``/``accent2`` são a cor de destaque (aros dos medalhões, títulos,
botões ativos). ``palette`` é o ciclo de cores usado para comunidades e para
tipos criados sem cor explícita.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import List

DEFAULT_PALETTE: List[str] = [
    "#d9ad3f", "#4a9c8c", "#c2564f", "#5b8fc7", "#8b7bd8", "#e08a3c",
    "#5fb3a1", "#c9576b", "#7fa650", "#a9739a", "#3f8fae", "#c98b3f",
    "#7a5fbf", "#5a9e5a", "#c46b9e", "#4f7fc4",
]


@dataclass(frozen=True)
class Theme:
    """Cores e fontes da visualização. Todos os campos aceitam cores CSS.

    Campos:
        bg / bg2: fundo do palco e da topbar.
        panel / panel2: painel lateral e caixas internas (busca, chips...).
        stroke / stroke_soft: bordas fortes e suaves.
        ink / muted: texto principal e secundário.
        accent / accent2: cor de destaque e sua variação clara.
        glow_a / glow_b: os dois brilhos radiais do fundo do palco.
        font / mono: pilhas de fonte (texto e monoespaçada).
        palette: ciclo de cores de comunidades/tipos automáticos.
    """

    bg: str = "#0a0806"
    bg2: str = "#120d09"
    panel: str = "#181109"
    panel2: str = "#100b06"
    stroke: str = "#3a2c17"
    stroke_soft: str = "#241a0f"
    ink: str = "#ecdfc2"
    muted: str = "#9c8a6a"
    accent: str = "#d9ad3f"
    accent2: str = "#f2c766"
    glow_a: str = "#1c140a"
    glow_b: str = "#150f08"
    font: str = "'Segoe UI',Inter,sans-serif"
    mono: str = "'IBM Plex Mono',Consolas,monospace"
    palette: List[str] = field(default_factory=lambda: list(DEFAULT_PALETTE))

    def with_(self, **changes) -> "Theme":
        """Retorna uma cópia do tema com os campos alterados (imutável)."""
        return replace(self, **changes)

    def to_dict(self) -> dict:
        return {
            "bg": self.bg, "bg2": self.bg2,
            "panel": self.panel, "panel2": self.panel2,
            "stroke": self.stroke, "strokeSoft": self.stroke_soft,
            "ink": self.ink, "muted": self.muted,
            "gold": self.accent, "gold2": self.accent2,
            "glowA": self.glow_a, "glowB": self.glow_b,
            "font": self.font, "mono": self.mono,
            "palette": list(self.palette),
        }

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------
    @classmethod
    def relicario(cls) -> "Theme":
        """Tema padrão: dourado sobre âmbar escuro (relíquia/pergaminho)."""
        return cls()

    @classmethod
    def arcano(cls) -> "Theme":
        """Azul-arcano: destaque azul gelo sobre fundo azul-noite."""
        return cls(
            bg="#06080d", bg2="#0a0e16", panel="#0d1420", panel2="#080d16",
            stroke="#1d2c47", stroke_soft="#121c2e", ink="#d7e2f2",
            muted="#7688a8", accent="#6ea8ff", accent2="#a5c9ff",
            glow_a="#0c1626", glow_b="#0a1120",
        )

    @classmethod
    def esmeralda(cls) -> "Theme":
        """Verde-esmeralda: destaque jade sobre fundo verde-abissal."""
        return cls(
            bg="#050a08", bg2="#08110d", panel="#0b1712", panel2="#07100c",
            stroke="#1b3a2c", stroke_soft="#102418", ink="#d7ecdf",
            muted="#75a08a", accent="#46c08a", accent2="#7fe0b2",
            glow_a="#0b1f16", glow_b="#081710",
        )

    @classmethod
    def rubi(cls) -> "Theme":
        """Vermelho-rubi: destaque carmim sobre fundo vinho profundo."""
        return cls(
            bg="#0b0507", bg2="#130a0d", panel="#1a0e12", panel2="#110a0d",
            stroke="#40202a", stroke_soft="#28141b", ink="#f0dde2",
            muted="#a87f8a", accent="#e0637a", accent2="#ff9aab",
            glow_a="#241017", glow_b="#180b10",
        )
