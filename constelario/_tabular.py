# -*- coding: utf-8 -*-
"""Leitura de dados tabulares para os construtores ``Graph.from_*``.

Fontes aceitas:

* caminho ``.csv``  — lido com a stdlib, **sem nenhuma dependência**;
* caminho ``.parquet`` — exige ``pandas`` ou ``pyarrow`` (``pip install
  "constelario[data]"``);
* um ``DataFrame`` do pandas — usado diretamente;
* um iterável de dicionários (uma linha por dict).

Todas as fontes são normalizadas para ``list[dict]``.
"""
from __future__ import annotations

import csv as _csv
import os
from typing import Any, List, Mapping


def _coerce(value: Any) -> Any:
    """O CSV entrega tudo como string; tenta int, depois float, senão mantém a
    string. Assim o inspetor e os rankings numéricos recebem números de verdade
    (e "" vira None, tratado como ausência)."""
    if not isinstance(value, str):
        return value
    s = value.strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return value


def _read_csv(path: str) -> List[dict]:
    # utf-8-sig descarta o BOM que o Excel costuma gravar no começo do arquivo.
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = _csv.DictReader(f)
        return [{k: _coerce(v) for k, v in row.items()} for row in reader]


def _read_parquet(path: str) -> List[dict]:
    try:
        import pandas as pd  # noqa: WPS433
        return pd.read_parquet(path).to_dict(orient="records")
    except ImportError:
        pass
    try:
        import pyarrow.parquet as pq  # noqa: WPS433
        return pq.read_table(path).to_pylist()
    except ImportError:
        raise ImportError(
            "ler arquivos .parquet exige pandas ou pyarrow — instale com "
            '`pip install "constelario[data]"`'
        )


def read_rows(source: Any) -> List[dict]:
    """Normaliza ``source`` para uma ``list[dict]`` (uma linha por dicionário)."""
    # DataFrame do pandas (detectado por pato, sem importar pandas à toa)
    if hasattr(source, "to_dict") and hasattr(source, "columns"):
        return source.to_dict(orient="records")
    if isinstance(source, (str, os.PathLike)):
        path = os.fspath(source)
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            return _read_csv(path)
        if ext in (".parquet", ".pq"):
            return _read_parquet(path)
        raise ValueError(
            f"extensão não suportada: {ext!r} — use .csv, .parquet, um DataFrame "
            "ou uma lista de dicionários")
    if isinstance(source, Mapping):
        raise TypeError("passe uma lista de linhas (dicts), não um único dict")
    rows = list(source)
    for r in rows:
        if not isinstance(r, Mapping):
            raise TypeError(
                f"cada linha deve ser um dict (recebido: {type(r).__name__})")
    return [dict(r) for r in rows]


def pick_props(row: Mapping, selected, exclude) -> dict:
    """Escolhe as colunas que viram ``props``.

    ``selected=None`` pega todas as colunas menos as estruturais (``exclude``);
    uma lista restringe às colunas dadas. Valores None são descartados.
    """
    if selected is None:
        keys = [k for k in row.keys() if k not in exclude]
    else:
        keys = list(selected)
    out = {}
    for k in keys:
        v = row.get(k)
        if v is not None:
            out[k] = v
    return out
