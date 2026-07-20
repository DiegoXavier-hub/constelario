# -*- coding: utf-8 -*-
"""Estratégias de **criação de arestas** para ``Graph.connect`` / ``from_table``.

Em vez de ligar os nós à mão, você escolhe *como* eles se conectam. Cada função
aqui devolve uma "estratégia" que o grafo aplica sobre os nós já existentes,
lendo as colunas/propriedades deles:

* :func:`knn`          — k vizinhos mais próximos por uma métrica de similaridade;
* :func:`threshold`    — todos os pares acima de um limiar de similaridade;
* :func:`radius`       — todos os pares dentro de um raio de distância;
* :func:`cosine`       — atalho de similaridade por cosseno (= ``threshold`` cosseno);
* :func:`correlation`  — similaridade por correlação de Pearson entre os perfis;
* :func:`jaccard`      — similaridade de Jaccard entre conjuntos (tags, categorias);
* :func:`cooccurrence` — co-ocorrência: liga nós que compartilham um contexto;
* :func:`rule`         — regra de negócio: uma função sua decide quem liga com quem;
* :func:`bipartite`    — projeção de grafo bipartido (liga nós por vizinhos em comum).

Todas atribuem um **peso** à aresta (``props[score_prop]``), que você pode usar
para engrossar a linha (:meth:`Graph.set_edge_weight`) e para ranquear vizinhos
no inspetor (:meth:`Graph.inspector_ranking`).

Exemplo::

    from constelario import Graph, edges
    g = Graph.from_table("alunos.csv", id="matricula", label="nome",
                         connect=edges.knn(["nota", "faltas"], k=5, metric="cosine"))
"""
from __future__ import annotations

import inspect
import math
from typing import Any, Callable, List, Optional, Sequence, Union

METRICS = ("cosine", "euclidean", "correlation", "jaccard")
SELECTS = ("knn", "threshold", "radius")

# Alvo de células por bloco no caminho vetorizado. A matriz de similaridade
# completa seria n² (inviável: 50 mil nós = 20 GB), então processamos em blocos
# de linhas — memória fica O(bloco × n) ≈ 40 MB em vez de O(n²).
_CHUNK_CELLS = 5_000_000


def _numpy():
    """numpy é opcional: acelera ~100× as métricas numéricas quando presente."""
    try:
        import numpy as np  # noqa: WPS433
        return np
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# Métricas (Python puro — dimensionado para grafos de visualização)
# ---------------------------------------------------------------------------
def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


def _euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _pearson(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    da = [x - ma for x in a]
    db = [y - mb for y in b]
    denom = math.sqrt(sum(x * x for x in da)) * math.sqrt(sum(y * y for y in db))
    return 0.0 if denom == 0 else sum(x * y for x, y in zip(da, db)) / denom


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Extração de features dos nós do grafo
# ---------------------------------------------------------------------------
def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def _vectors(graph, features: Sequence[str], standardize: bool):
    """(ids, vetores) só dos nós com TODAS as features numéricas presentes."""
    ids: List[str] = []
    vecs: List[List[float]] = []
    for n in graph._nodes.values():
        vec, ok = [], True
        for c in features:
            v = _num(n.props.get(c))
            if v is None:
                ok = False
                break
            vec.append(v)
        if ok:
            ids.append(n.id)
            vecs.append(vec)
    if standardize and vecs:
        dim = len(vecs[0])
        for j in range(dim):
            col = [v[j] for v in vecs]
            mean = sum(col) / len(col)
            var = sum((x - mean) ** 2 for x in col) / len(col)
            sd = math.sqrt(var)
            if sd > 0:
                for v in vecs:
                    v[j] = (v[j] - mean) / sd
    return ids, vecs


def _to_set(value: Any, sep: Optional[str]) -> set:
    if value is None:
        return set()
    if isinstance(value, (set, frozenset, list, tuple)):
        return set(value)
    if isinstance(value, str):
        return set(value.split(sep)) if sep else {value}
    return {value}


def _sets(graph, feature: str, sep: Optional[str]):
    ids, sets = [], []
    for n in graph._nodes.values():
        s = _to_set(n.props.get(feature), sep)
        if s:
            ids.append(n.id)
            sets.append(s)
    return ids, sets


# ---------------------------------------------------------------------------
# Estratégias
# ---------------------------------------------------------------------------
class Strategy:
    """Base — implementa ``build(graph) -> list[dict(source,target,type,props)]``."""

    def build(self, graph) -> List[dict]:  # pragma: no cover - interface
        raise NotImplementedError


class _Similarity(Strategy):
    def __init__(self, features, metric, select, k, threshold, radius,
                 sep, edge_type, score_prop, standardize, directed):
        if metric not in METRICS:
            raise ValueError(f"métrica inválida: {metric!r} (use {METRICS})")
        if select not in SELECTS:
            raise ValueError(f"seleção inválida: {select!r} (use {SELECTS})")
        if metric == "jaccard" and not isinstance(features, str):
            raise ValueError("jaccard exige UMA coluna de conjuntos (features=str)")
        if metric != "jaccard" and isinstance(features, str):
            features = [features]
        self.features = features
        self.metric = metric
        self.select = select
        self.k = k
        self.threshold = threshold
        self.radius = radius
        self.sep = sep
        self.edge_type = edge_type
        self.score_prop = score_prop
        self.standardize = standardize
        self.directed = directed

    def _pairs_data(self, graph):
        if self.metric == "jaccard":
            ids, data = _sets(graph, self.features, self.sep)
            return ids, data, _jaccard, False
        ids, data = _vectors(graph, self.features, self.standardize)
        if self.metric == "cosine":
            return ids, data, _cosine, False
        if self.metric == "correlation":
            return ids, data, _pearson, False
        return ids, data, _euclidean, True  # euclidean -> distância

    def _emit(self, edges, seen, ids, i, j, score):
        key = (i, j) if self.directed else (min(i, j), max(i, j))
        if not self.directed:
            if key in seen:
                return
            seen.add(key)
        edges.append({"source": ids[i], "target": ids[j], "type": self.edge_type,
                      "props": {self.score_prop: round(float(score), 6)}})

    # -- caminho vetorizado (numpy): matriz por blocos de linhas ------------
    def _build_vectorized(self, ids, data, np) -> List[dict]:
        X = np.asarray(data, dtype=float)
        n = X.shape[0]
        is_dist = self.metric == "euclidean"
        if self.metric == "correlation":
            X = X - X.mean(axis=1, keepdims=True)
        if self.metric in ("cosine", "correlation"):
            norms = np.linalg.norm(X, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            X = X / norms
        sq = (X * X).sum(axis=1) if is_dist else None

        edges: List[dict] = []
        seen: set = set()
        chunk = max(1, min(n, _CHUNK_CELLS // max(1, n)))
        for start in range(0, n, chunk):
            stop = min(n, start + chunk)
            block = X[start:stop]
            if is_dist:
                # |a-b|² = |a|² + |b|² - 2·a·b (evita materializar diferenças)
                M = sq[start:stop, None] + sq[None, :] - 2.0 * (block @ X.T)
                np.maximum(M, 0, out=M)
                np.sqrt(M, out=M)
            else:
                M = block @ X.T
            # neutraliza a diagonal (auto-similaridade) do bloco
            rows = np.arange(stop - start)
            M[rows, rows + start] = np.inf if is_dist else -np.inf

            if self.select == "knn":
                k = min(self.k, n - 1)
                if k <= 0:
                    continue
                part = np.argpartition(M if is_dist else -M, k - 1, axis=1)[:, :k]
                for r in range(stop - start):
                    for j in part[r]:
                        self._emit(edges, seen, ids, start + r, int(j), M[r, j])
            else:
                lim = self.threshold if self.select == "threshold" else self.radius
                hits = np.argwhere(M <= lim) if is_dist else np.argwhere(M >= lim)
                for r, j in hits:
                    i, j = start + int(r), int(j)
                    # i<j basta: cada par não-dirigido aparece uma única vez
                    if self.directed or i < j:
                        self._emit(edges, seen, ids, i, j, M[int(r), j])
        return edges

    # -- Jaccard por índice invertido: só compara quem divide algum elemento -
    def _build_jaccard(self, ids, sets) -> List[dict]:
        inverted: dict = {}
        for i, s in enumerate(sets):
            for token in s:
                inverted.setdefault(token, []).append(i)
        shared: dict = {}
        for members in inverted.values():
            if len(members) < 2:
                continue
            for a in range(len(members)):
                for b in range(a + 1, len(members)):
                    key = (members[a], members[b])
                    shared[key] = shared.get(key, 0) + 1

        edges: List[dict] = []
        seen: set = set()
        if self.select == "knn":
            best: dict = {}
            for (i, j), inter in shared.items():
                score = inter / (len(sets[i]) + len(sets[j]) - inter)
                best.setdefault(i, []).append((score, j))
                best.setdefault(j, []).append((score, i))
            for i, scored in best.items():
                scored.sort(reverse=True)
                for score, j in scored[: self.k]:
                    self._emit(edges, seen, ids, i, j, score)
        else:
            for (i, j), inter in shared.items():
                score = inter / (len(sets[i]) + len(sets[j]) - inter)
                if score >= self.threshold:
                    self._emit(edges, seen, ids, i, j, score)
        return edges

    # -- fallback puro-Python (sem numpy) ----------------------------------
    def _build_pure(self, ids, data, fn, is_dist) -> List[dict]:
        n = len(ids)
        edges: List[dict] = []
        seen: set = set()
        if self.select == "knn":
            for i in range(n):
                scored = [(fn(data[i], data[j]), j) for j in range(n) if j != i]
                scored.sort(key=lambda t: t[0], reverse=not is_dist)
                for s, j in scored[: self.k]:
                    self._emit(edges, seen, ids, i, j, s)
        else:
            lim = self.threshold if self.select == "threshold" else self.radius
            for i in range(n):
                for j in range(i + 1, n):
                    s = fn(data[i], data[j])
                    if (s <= lim) if is_dist else (s >= lim):
                        self._emit(edges, seen, ids, i, j, s)
        return edges

    def build(self, graph) -> List[dict]:
        ids, data, fn, is_dist = self._pairs_data(graph)
        if not ids:
            return []
        if self.metric == "jaccard":
            return self._build_jaccard(ids, data)
        np = _numpy()
        if np is not None:
            return self._build_vectorized(ids, data, np)
        return self._build_pure(ids, data, fn, is_dist)


class _CoOccurrence(Strategy):
    def __init__(self, by, edge_type, score_prop, sep, min_shared):
        self.by = by
        self.edge_type = edge_type
        self.score_prop = score_prop
        self.sep = sep
        self.min_shared = min_shared

    def build(self, graph) -> List[dict]:
        # Índice invertido contexto -> membros. Só nós que dividem ao menos um
        # contexto viram par, em vez de varrer todos os n² pares do grafo.
        by_context: dict = {}
        for nid, n in graph._nodes.items():
            for ctx in _to_set(n.props.get(self.by), self.sep):
                by_context.setdefault(ctx, []).append(nid)

        shared: dict = {}
        for members in by_context.values():
            if len(members) < 2:
                continue
            for a in range(len(members)):
                for b in range(a + 1, len(members)):
                    x, y = members[a], members[b]
                    key = (x, y) if x <= y else (y, x)
                    shared[key] = shared.get(key, 0) + 1

        return [{"source": x, "target": y, "type": self.edge_type,
                 "props": {self.score_prop: count}}
                for (x, y), count in shared.items() if count >= self.min_shared]


class _Rule(Strategy):
    def __init__(self, fn, edge_type, directed, score_prop):
        self.fn = fn
        self.edge_type = edge_type
        self.directed = directed
        self.score_prop = score_prop
        self.arity = len(inspect.signature(fn).parameters)

    def _view(self, n):
        return {"id": n.id, "label": n.label, "type": n.type,
                "community": n.community, **n.props}

    def build(self, graph) -> List[dict]:
        nodes = list(graph._nodes.values())
        edges, seen = [], set()

        def add(src, tgt, score):
            key = (src, tgt) if self.directed else (min(src, tgt), max(src, tgt))
            if src == tgt or (not self.directed and key in seen):
                return
            seen.add(key)
            props = {} if score is None else {self.score_prop: score}
            edges.append({"source": src, "target": tgt, "type": self.edge_type, "props": props})

        if self.arity >= 2:
            # fn(a, b) -> bool | número (peso) para cada par
            views = [self._view(n) for n in nodes]
            rng = range(len(nodes))
            for i in rng:
                for j in (rng if self.directed else range(i + 1, len(nodes))):
                    if i == j:
                        continue
                    res = self.fn(views[i], views[j])
                    if res is None or res is False:
                        continue
                    score = None if res is True else float(res)
                    add(nodes[i].id, nodes[j].id, score)
        else:
            # fn(node) -> iterável de ids alvo (ou (id, peso))
            valid = set(graph._nodes)
            for n in nodes:
                out = self.fn(self._view(n))
                if not out:
                    continue
                for item in out:
                    if isinstance(item, (list, tuple)):
                        tgt, score = str(item[0]), (float(item[1]) if len(item) > 1 else None)
                    else:
                        tgt, score = str(item), None
                    if tgt in valid:
                        add(n.id, tgt, score)
        return edges


class _Bipartite(Strategy):
    """Projeta um lado do grafo bipartido: liga nós de ``project`` que
    compartilham vizinhos (Jaccard sobre os conjuntos de vizinhos)."""

    def __init__(self, project, over, threshold, k, edge_type, score_prop):
        self.project = project
        self.over = over
        self.threshold = threshold
        self.k = k
        self.edge_type = edge_type
        self.score_prop = score_prop

    def build(self, graph) -> List[dict]:
        neigh = {nid: set() for nid, n in graph._nodes.items() if n.type == self.project}
        for e in graph._edges:
            for a, b in ((e.source, e.target), (e.target, e.source)):
                if a in neigh:
                    other = graph._nodes.get(b)
                    if other is not None and (self.over is None or other.type == self.over):
                        neigh[a].add(b)
        ids = [i for i in neigh if neigh[i]]
        # Índice invertido vizinho -> quem o tem: gera só os pares que de fato
        # compartilham algum vizinho (em vez de todos os pares projetados).
        by_neighbor: dict = {}
        for i in ids:
            for nb in neigh[i]:
                by_neighbor.setdefault(nb, []).append(i)
        inter: dict = {}
        for holders in by_neighbor.values():
            if len(holders) < 2:
                continue
            for a in range(len(holders)):
                for b in range(a + 1, len(holders)):
                    x, y = holders[a], holders[b]
                    key = (x, y) if x <= y else (y, x)
                    inter[key] = inter.get(key, 0) + 1

        edges, seen = [], set()

        def emit(i, j, score):
            key = (i, j) if i <= j else (j, i)
            if key in seen:
                return
            seen.add(key)
            edges.append({"source": i, "target": j, "type": self.edge_type,
                          "props": {self.score_prop: round(score, 6)}})

        def score_of(x, y, shared):
            return shared / (len(neigh[x]) + len(neigh[y]) - shared)

        if self.k:
            best: dict = {}
            for (x, y), shared in inter.items():
                s = score_of(x, y, shared)
                best.setdefault(x, []).append((s, y))
                best.setdefault(y, []).append((s, x))
            for i, scored in best.items():
                scored.sort(reverse=True)
                for s, j in scored[: self.k]:
                    emit(i, j, s)
        else:
            for (x, y), shared in inter.items():
                s = score_of(x, y, shared)
                if s >= self.threshold:
                    emit(x, y, s)
        return edges


# ---------------------------------------------------------------------------
# Fábricas (a API pública, amigável)
# ---------------------------------------------------------------------------
def knn(features: Union[str, Sequence[str]], *, k: int = 5, metric: str = "cosine",
        edge_type: str = "SIMILAR", score_prop: str = "score",
        standardize: bool = False, mutual: bool = False) -> Strategy:
    """k vizinhos mais próximos: liga cada nó aos ``k`` mais parecidos.

    ``metric``: ``"cosine"`` | ``"euclidean"`` | ``"correlation"`` | ``"jaccard"``.
    ``mutual=True`` gera arestas dirigidas (i→vizinho); o padrão une pares.
    ``standardize=True`` normaliza (z-score) cada feature antes — recomendado
    para ``euclidean`` quando as colunas têm escalas diferentes.
    """
    return _Similarity(features, metric, "knn", k, None, None, None,
                       edge_type, score_prop, standardize, mutual)


def threshold(features: Union[str, Sequence[str]], *, threshold: float = 0.7,
              metric: str = "cosine", edge_type: str = "SIMILAR",
              score_prop: str = "score", standardize: bool = False) -> Strategy:
    """Liga todos os pares com similaridade ``>= threshold`` (ou distância
    ``<= threshold`` quando ``metric="euclidean"``)."""
    return _Similarity(features, metric, "threshold", None, threshold, None, None,
                       edge_type, score_prop, standardize, False)


def radius(features: Union[str, Sequence[str]], *, radius: float = 1.0,
           metric: str = "euclidean", edge_type: str = "PROXIMO",
           score_prop: str = "dist", standardize: bool = False) -> Strategy:
    """Raio de vizinhança: liga todos os pares a uma distância ``<= radius``."""
    return _Similarity(features, metric, "radius", None, None, radius, None,
                       edge_type, score_prop, standardize, False)


def cosine(features: Sequence[str], *, threshold: float = 0.7,
           edge_type: str = "SIMILAR", score_prop: str = "score") -> Strategy:
    """Atalho: similaridade por cosseno acima de um limiar."""
    return _Similarity(features, "cosine", "threshold", None, threshold, None, None,
                       edge_type, score_prop, False, False)


def correlation(features: Sequence[str], *, threshold: float = 0.7,
                edge_type: str = "CORRELACIONADO", score_prop: str = "r") -> Strategy:
    """Similaridade por correlação de Pearson entre os perfis de features."""
    return _Similarity(features, "correlation", "threshold", None, threshold, None, None,
                       edge_type, score_prop, False, False)


def jaccard(feature: str, *, threshold: float = 0.3, sep: Optional[str] = None,
            edge_type: str = "SIMILAR", score_prop: str = "score") -> Strategy:
    """Similaridade de Jaccard entre conjuntos. ``feature`` é UMA coluna com
    conjuntos/listas ou uma string delimitada por ``sep`` (ex.: ``"a;b;c"``)."""
    return _Similarity(feature, "jaccard", "threshold", None, threshold, None, sep,
                       edge_type, score_prop, False, False)


def cooccurrence(by: str, *, edge_type: str = "CO_OCORRE", score_prop: str = "peso",
                 sep: Optional[str] = None, min_shared: int = 1) -> Strategy:
    """Co-ocorrência: liga nós que compartilham um contexto (mesmo valor em
    ``by``). ``by`` pode ser uma coleção/string delimitada (vários contextos);
    o peso é o nº de contextos em comum."""
    return _CoOccurrence(by, edge_type, score_prop, sep, min_shared)


def rule(fn: Callable, *, edge_type: str = "REGRA", directed: bool = False,
         score_prop: str = "peso") -> Strategy:
    """Regra de negócio via função sua.

    * ``fn(a, b)`` (2 args) — recebe dois nós (dict ``id/label/type/community`` +
      props) e devolve ``False``/``None`` (não liga), ``True`` (liga) ou um número
      (liga com esse peso). Avalia todos os pares.
    * ``fn(node)`` (1 arg) — devolve os ids-alvo (ou pares ``(id, peso)``).
    """
    return _Rule(fn, edge_type, directed, score_prop)


def bipartite(project: str, *, over: Optional[str] = None, threshold: float = 0.1,
              k: Optional[int] = None, edge_type: str = "SIMILAR",
              score_prop: str = "score") -> Strategy:
    """Projeção de grafo bipartido: liga nós do tipo ``project`` que
    compartilham vizinhos (opcionalmente só vizinhos do tipo ``over``), por
    Jaccard. Use ``k`` para k-vizinhos ou ``threshold`` para todos acima do corte.
    Requer que o grafo já tenha as arestas bipartidas (ex.: via ``from_edges``)."""
    return _Bipartite(project, over, threshold, k, edge_type, score_prop)
