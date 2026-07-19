# -*- coding: utf-8 -*-
"""Empacotamento do HTML final: template + bibliotecas JS + configuração.

Dois modos de entrega das bibliotecas (vis-network, 3d-force-graph, three):

* ``inline_js=True``  — o JS vendorizado em ``assets/vendor/`` é embutido no
  próprio HTML. O arquivo fica ~2.6 MB maior, mas abre offline, de file://,
  pendrive, Moodle, onde for. O three (só distribuído como ES module) é
  embutido em base64 e importado via Blob URL em runtime.
* ``inline_js=False`` — tags de CDN pinadas com Subresource Integrity.
"""
from __future__ import annotations

import base64
import datetime as _dt
import json
import math
from importlib import resources

_CONFIG_OPEN = '<script id="constelario-config" type="application/json">'
_CONFIG_CLOSE = "</script>"
_SCRIPTS_MARK = "<!--CONSTELARIO:SCRIPTS-->"

_CDN_TAGS = """
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"
  integrity="sha384-Ux6phic9PEHJ38YtrijhkzyJ8yQlH8i/+buBR8s3mAZOJrP1gwyvAcIYl3GWtpX1" crossorigin="anonymous"></script>
<script src="https://unpkg.com/3d-force-graph@1.80.0/dist/3d-force-graph.min.js"
  integrity="sha384-Y7bC2PBKu8ujxtvo5+Z61OeGdSVRzFsYWBK4i5dnL/U6aFDTodk61qOUkTfInaxS" crossorigin="anonymous"></script>
<script type="module">
  import * as THREE from 'https://unpkg.com/three@0.180.0/build/three.module.js';
  window.THREE = THREE;
  window.dispatchEvent(new Event('three-ready'));
</script>
"""


def _asset_text(*parts: str) -> str:
    # joinpath com vários argumentos só é garantido no Traversable a partir do
    # 3.10; encadear com "/" (um componente por vez) funciona em 3.9 inclusive
    # quando o pacote está dentro de um zip (zipfile.Path).
    ref = resources.files("constelario")
    for part in ("assets", *parts):
        ref = ref / part
    return ref.read_text(encoding="utf-8")


def _json_default(obj):
    """Converte tipos comuns não-JSON (numpy, datetime, set...) — importante
    para ``from_networkx``, onde props trazem escalares numpy/datas."""
    if hasattr(obj, "item"):          # escalares numpy (float32, int64...)
        try:
            return _finite(obj.item())
        except Exception:
            pass
    if isinstance(obj, (_dt.date, _dt.datetime, _dt.time)):
        return obj.isoformat()
    if isinstance(obj, (set, frozenset, tuple)):
        return list(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", "replace")
    return str(obj)


def _finite(value):
    """NaN/Infinity não são JSON válido e quebrariam o ``JSON.parse`` do
    viewer (página em branco). Troca por ``None`` — comum em props vindas de
    pandas/Neo4j."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _sanitize(obj):
    """Percorre a config trocando floats não-finitos por None (recursivo)."""
    if isinstance(obj, float):
        return _finite(obj)
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def _inline_classic(js: str, label: str) -> str:
    if "</script" in js.lower():
        raise RuntimeError(
            f"o bundle {label} contém '</script' e não pode ser embutido; "
            "use inline_js=False (CDN)")
    return f"<script>\n{js}\n</script>"


def _b64_tag(element_id: str, text: str) -> str:
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f'<script type="text/plain" id="{element_id}">{b64}</script>'


def _inline_scripts() -> str:
    vis = _asset_text("vendor", "vis-network.min.js")
    fg3d = _asset_text("vendor", "3d-force-graph.min.js")
    three_main = _asset_text("vendor", "three.module.js")
    three_core = _asset_text("vendor", "three.core.js")
    # O three só existe como ES module e, desde o r167, vem em DOIS arquivos
    # (three.module.js importa './three.core.js'). Embutimos ambos em base64 e
    # importamos via Blob URLs, reescrevendo o specifier relativo do módulo
    # principal para apontar para o blob do core — um import relativo não
    # resolve a partir de blob: (a URL não é hierárquica).
    three_boot = (
        _b64_tag("__constelario_three_core_b64", three_core) + "\n"
        + _b64_tag("__constelario_three_b64", three_main) + "\n"
        + "<script>\n"
        "(function () {\n"
        "  function decode(id) {\n"
        "    var bin = atob(document.getElementById(id).textContent);\n"
        "    var bytes = new Uint8Array(bin.length);\n"
        "    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);\n"
        "    return new TextDecoder().decode(bytes);\n"
        "  }\n"
        "  var coreUrl = URL.createObjectURL(new Blob([decode('__constelario_three_core_b64')], { type: 'text/javascript' }));\n"
        "  var mainSrc = decode('__constelario_three_b64').split('./three.core.js').join(coreUrl);\n"
        "  var mainUrl = URL.createObjectURL(new Blob([mainSrc], { type: 'text/javascript' }));\n"
        "  import(mainUrl).then(function (m) {\n"
        "    window.THREE = m;\n"
        "    window.dispatchEvent(new Event('three-ready'));\n"
        "  });\n"
        "})();\n"
        "</script>"
    )
    return "\n".join([
        _inline_classic(vis, "vis-network"),
        _inline_classic(fg3d, "3d-force-graph"),
        three_boot,
    ])


def render(config: dict, *, inline_js: bool = True) -> str:
    """Gera o HTML final a partir do template + config + bibliotecas JS."""
    template = _asset_text("viewer.html")
    scripts = _inline_scripts() if inline_js else _CDN_TAGS
    if _SCRIPTS_MARK not in template:
        raise RuntimeError("template inválido: marcador de scripts ausente")
    html = template.replace(_SCRIPTS_MARK, scripts, 1)

    start = html.index(_CONFIG_OPEN) + len(_CONFIG_OPEN)
    end = html.index(_CONFIG_CLOSE, start)
    # allow_nan=False garante JSON válido (NaN/Infinity quebrariam o JSON.parse
    # do viewer); _sanitize já trocou os não-finitos por None e _json_default
    # cobre numpy/datetime/set. "</" -> "<\/" impede que um "</script" no texto
    # do usuário feche o bloco <script>.
    payload = json.dumps(_sanitize(config), ensure_ascii=False,
                         allow_nan=False, default=_json_default).replace("</", "<\\/")
    return html[:start] + "\n" + payload + "\n" + html[end:]
