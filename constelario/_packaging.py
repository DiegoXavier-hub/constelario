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
import json
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
    ref = resources.files("constelario").joinpath("assets", *parts)
    return ref.read_text(encoding="utf-8")


def _inline_classic(js: str, label: str) -> str:
    if "</script" in js.lower():
        raise RuntimeError(
            f"o bundle {label} contém '</script' e não pode ser embutido; "
            "use inline_js=False (CDN)")
    return f"<script>\n{js}\n</script>"


def _inline_scripts() -> str:
    vis = _asset_text("vendor", "vis-network.min.js")
    fg3d = _asset_text("vendor", "3d-force-graph.min.js")
    three = _asset_text("vendor", "three.module.js")
    three_b64 = base64.b64encode(three.encode("utf-8")).decode("ascii")
    # O three só existe como ES module; embutimos em base64 e importamos de um
    # Blob URL — assim o HTML continua um arquivo único que abre de file://.
    three_boot = (
        f'<script type="text/plain" id="__constelario_three_b64">{three_b64}</script>\n'
        "<script>\n"
        "(function () {\n"
        "  var b64 = document.getElementById('__constelario_three_b64').textContent;\n"
        "  var bin = atob(b64), bytes = new Uint8Array(bin.length);\n"
        "  for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);\n"
        "  var url = URL.createObjectURL(new Blob([bytes], { type: 'text/javascript' }));\n"
        "  import(url).then(function (m) {\n"
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
    # "</" vira "<\/" dentro do JSON (parse idêntico): impede que um "</script"
    # em algum texto do usuário feche o bloco <script> e corrompa o HTML.
    payload = json.dumps(config, ensure_ascii=False).replace("</", "<\\/")
    return html[:start] + "\n" + payload + "\n" + html[end:]
