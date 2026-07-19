# Constelário

Grafos de conhecimento **interativos (2D e 3D)** gerados a partir de Python, em **um único
arquivo HTML** que abre em qualquer navegador — sem servidor, sem `npm`, sem internet
(as bibliotecas JS já vêm embutidas). Os nós são desenhados como **medalhões ornamentados**
(estilo árvore de habilidades de RPG) e o grafo pode ser organizado em **4 layouts**
espaciais, com painel lateral de busca, legenda, inspeção e rankings.

| | |
|---|---|
| **Visualizações** | 2D (vis-network) e 3D (3d-force-graph/three.js), alternáveis a um clique |
| **Layouts** | Constelação (anéis) · Comunidades (grupos separados) · Camadas (colunas por tipo) · Espiral/Globo |
| **Tela cheia** | Com painel lateral retrátil (estilo "taskbar oculta") e toggle 2D/3D flutuante |
| **Customização** | Tema (todas as cores), tipos, ícones, tamanhos, arestas, layouts, textos da UI, painéis |
| **Saída** | Um `.html` autocontido (offline) ou versão leve via CDN |

---

## Instalação

Requer **Python ≥ 3.9**. Nenhuma dependência obrigatória.

```bash
# a partir do clone do repositório
git clone https://github.com/DiegoXavier-hub/constelario.git
pip install ./constelario

# ou, para desenvolver a própria biblioteca:
pip install -e ./constelario

# opcional: interoperabilidade com networkx e testes
pip install "./constelario[networkx,dev]"
```

## Começo rápido

```python
from constelario import Graph

g = Graph(title="Reino de Python", subtitle="exemplo básico")

# tipos definem cor, ícone e ornamentação dos nós
g.add_type("Reino",  color="#f2c766", icon="crown", tier="keystone", ring=0)
g.add_type("Cidade", color="#5b8fc7", icon="building", tier="notable")
g.add_type("Pessoa", color="#4a9c8c", icon="user")

g.add_node("r1", "Pythonia", "Reino")
g.add_node("c1", "Vilarejo das Listas", "Cidade", community=0)
g.add_node("c2", "Porto dos Dicionários", "Cidade", community=1)
g.add_node("p1", "Alice", "Pessoa", community=0, props={"idade": 30})
g.add_node("p2", "Bob", "Pessoa", community=1)

g.add_edge("c1", "r1", type="PERTENCE_A")
g.add_edge("c2", "r1", type="PERTENCE_A")
g.add_edge("p1", "c1", type="MORA_EM")
g.add_edge("p2", "c2", type="MORA_EM")
g.add_edge("p1", "p2", type="CONHECE", props={"desde": 2019})

g.save("meu_grafo.html")   # arquivo único, funciona offline
g.show()                   # atalho: salva em temp e abre no navegador
```

Pronto: abra o HTML e você tem o grafo com busca, legenda, inspetor, 4 layouts,
2D/3D e tela cheia.

---

## Conceitos

- **Nó** (`add_node`): tem `id` único, `label`, um **tipo**, propriedades livres
  (`props`, exibidas no inspetor), e opcionalmente `community` (int), `icon`,
  `color` e `size` (sobrepõem o padrão do tipo).
- **Tipo** (`add_type`): define a aparência de todos os nós daquele tipo — cor,
  ícone, `tier` do medalhão e `ring` (anel do layout Constelação). Tipos não
  registrados são criados automaticamente com cores da paleta.
- **Aresta** (`add_edge`): dirigida (`source → target`), com `type` livre e
  `props`. O estilo por tipo de aresta é configurável (`edge_style`).
- **Comunidade**: um agrupamento inteiro por nó (ex.: resultado de Louvain,
  clustering, departamento...). Alimenta a coloração "Comunidade", o layout
  "Comunidades" e o painel de comunidades.

---

## Referência da API

### `Graph(title, subtitle="", *, theme=None, generated_at=None)`

Cria o grafo. `theme` é um [`Theme`](#tema-theme); `generated_at` (str) aparece na
caixa de estatísticas (padrão: agora).

### `add_type(name, *, label=None, color=None, icon="dot", tier="small", ring=None, hidden=False)`

| Parâmetro | Significado |
|---|---|
| `label` | Nome exibido (legenda, inspetor). Padrão: o próprio `name`. |
| `color` | Cor CSS dos nós. Padrão: próxima cor da paleta do tema. |
| `icon` | Nome de um [ícone](#ícones) embutido ou registrado. |
| `tier` | Ornamentação do medalhão: `"keystone"` (máxima — use no nó raiz), `"notable"` (destacada) ou `"small"` (comum). |
| `ring` | Anel do layout Constelação (0 = centro; 1, 2, 3... para fora). Sem valor, é atribuído pela ordem de registro (a partir de 1). |
| `hidden` | Começa desligado na legenda; no layout Espiral/Globo esses nós formam o **halo externo** (bom para tipos muito numerosos). |

Registrar o mesmo tipo duas vezes levanta `ValueError` (não há redefinição —
configure o tipo uma vez só). Chamar `add_type` já é feito automaticamente por
`add_node` para tipos novos.

### `add_node(node_id, label, type_name, *, props=None, community=None, icon=None, color=None, size=None)`

Adiciona um nó. `props` é um dict livre mostrado no inspetor. `icon`/`color`/`size`
sobrepõem o padrão do tipo (sem `size`, o tamanho escala com o **grau** do nó).
IDs duplicados levantam `ValueError`.

### `add_edge(source, target, *, type="", props=None)`

Adiciona uma aresta. Os endpoints precisam existir como nós na hora do render
(senão `ValueError` com a lista dos ausentes).

### `edge_style(edge_type, *, color=None, width=None, opacity=None, dashes=None)`

Estilo das arestas de um tipo. Use `edge_type="default"` para o estilo base.

```python
g.edge_style("default", color="#4a3c28", width=0.55, opacity=0.12)
g.edge_style("SIMILAR_A", color="#f2c766", width=1.6, opacity=0.6)   # destaque
g.edge_style("RUMOR", dashes=True, opacity=0.3)
```

> **No modo 3D**, `color` e `width` são aplicados; `opacity` é uniforme e
> `dashes` não tem efeito (limitação do 3d-force-graph). Um tipo de aresta
> literalmente chamado `"default"` compartilha o estilo-base.

### `add_color_mode(key, label, *, prop, colors=None, fallback="#5a4c34")`

Adiciona uma opção no seletor **"Colorir por"** baseada numa propriedade dos nós.
Valores sem cor em `colors` ganham cores da paleta automaticamente.

```python
g.add_color_mode("regiao", "Região", prop="regiao",
                 colors={"norte": "#5b8fc7", "sul": "#c2564f"})
```

Os modos `Tipo de nó` e `Comunidade` já existem (o segundo só aparece se algum nó
tiver `community`).

### `add_panel(title, rows, *, hint="")`

Painel de ranking na barra lateral. Cada linha é `(label, valor)` ou
`(label, valor, node_id)` — com `node_id`, clicar foca o nó.

```python
g.add_panel("Mais influentes", [("Alice", "0.42", "p1"), ("Bob", "0.31", "p2")],
            hint="pagerank")
```

### `inspector_ranking(edge_type, *, title, score_prop="score", decimals=3)`

No inspetor de um nó, lista os vizinhos conectados por `edge_type` ordenados pela
propriedade numérica `score_prop` da **aresta** (ex.: similaridade):

```python
g.add_edge("p1", "p2", type="SIMILAR_A", props={"score": 0.93})
g.inspector_ranking("SIMILAR_A", title="Mais similares", score_prop="score")
```

### `add_icon(name, svg)`

Registra um glifo próprio: o *miolo* de um SVG 24×24 desenhado em stroke.

```python
g.add_icon("anel", '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>')
g.add_type("Artefato", icon="anel")
```

### `set_layouts(default=None, enabled=None, sync_community_color=None)`

- `default`: layout inicial — `"constel"`, `"communities"`, `"layers"` ou `"spiral"`.
- `enabled`: quais aparecem no menu (com um só, o menu some).
- `sync_community_color` (padrão `True`): escolher "Comunidades" troca a
  coloração para comunidade automaticamente.

### `set_node_size(min=7, max=46)` · `hide_props(*names)` · `add_stat(label, value)`

Faixa de tamanho dos nós; propriedades ocultas no inspetor; linhas extras na caixa
de estatísticas.

### `set_ui(...)`

Liga/desliga blocos e define o modo inicial:

```python
g.set_ui(search=True, legend=True, inspector=True, stats=True,
         fullscreen=True, communities_panel=True,
         mode="3d",                      # abre direto no 3D
         hint="clique nos nós!")         # texto do rodapé do palco
```

### `set_strings(**overrides)`

Sobrescreve qualquer texto da interface (todas as chaves estão em
`constelario/strings.py` — títulos, botões, descrições dos layouts...):

```python
g.set_strings(search_placeholder="Buscar heróis...",
              layout_communities="Guildas",
              layout_communities_desc="cada guilda em seu território")
```

### Saída

```python
html = g.to_html()                    # string HTML completa
g.save("grafo.html")                  # grava e retorna o caminho absoluto
g.save("grafo.html", inline_js=False) # versão leve (usa CDN; exige internet)
g.show()                              # abre no navegador padrão
```

- `inline_js=True` (padrão): as bibliotecas JS vendorizadas são embutidas — o
  arquivo fica ~3.5 MB, mas **abre offline** de qualquer lugar (file://, pendrive,
  Moodle, GitHub Pages...).
- `inline_js=False`: tags de CDN pinadas com verificação de integridade (SRI).

**Streamlit / Jupyter:**

```python
# Streamlit
import streamlit.components.v1 as components
components.html(g.to_html(), height=720)

# Jupyter
from IPython.display import IFrame
g.save("grafo.html"); IFrame("grafo.html", "100%", 600)
```

### `Graph.from_networkx(nx_graph, *, title=..., type_attr="type", label_attr="label", community_attr="community", default_type="Nó")`

Converte um grafo networkx: os atributos de nó indicados viram tipo/rótulo/
comunidade e o resto vira `props`; atributos de aresta viram `props` (o atributo
`type` vira o tipo da aresta).

```python
import networkx as nx
G = nx.karate_club_graph()
for n, d in G.nodes(data=True):
    d["label"] = f"Membro {n}"; d["type"] = "Pessoa"; d["community"] = d.pop("club") == "Officer"
g = Graph.from_networkx(G, title="Clube de Karatê")
```

---

## Tema (`Theme`)

Todas as cores da interface num só objeto imutável:

```python
from constelario import Graph, Theme

g = Graph(title="Grimório", theme=Theme.arcano())          # preset azul
g = Graph(title="Floresta", theme=Theme.esmeralda())       # preset verde
g = Graph(title="Forja", theme=Theme.rubi())               # preset vermelho
g = Graph(title="Relíquia")                                # padrão dourado

# qualquer campo pode ser ajustado (retorna um novo Theme):
tema = Theme.arcano().with_(accent="#8be9fd", ink="#f8f8f2")
```

| Campo | O que pinta |
|---|---|
| `bg`, `bg2` | fundo do palco e da topbar |
| `panel`, `panel2` | painel lateral e caixas internas |
| `stroke`, `stroke_soft` | bordas |
| `ink`, `muted` | texto principal e secundário |
| `accent`, `accent2` | cor de destaque (aros, títulos, botões) e variação clara |
| `glow_a`, `glow_b` | os dois brilhos radiais do fundo |
| `font`, `mono` | pilhas de fonte |
| `palette` | ciclo de 16 cores para comunidades e tipos automáticos |

## Ícones

Embutidos (`constelario.BUILTIN_ICONS`): `dot`, `crown`, `user`, `graduation-cap`,
`folder`, `cpu`, `git-branch`, `building`, `factory`, `activity`, `crosshair`,
`check-circle`, `x-circle`, `shield`, `alert`, `clock`, `star`, `database`, `zap`,
`globe`, `box`, `tag`, `flame`, `book`, `link`, `leaf`, `gem`, `heart`.

Cada nó vira um **medalhão**: soquete escuro com gradiente, aro gravado com
entalhes (ornamentação cresce com o `tier` do tipo — cravos em losango nos
`notable`, aro máximo com 8 cravos no `keystone`), anel na cor do nó e o glifo
central em relevo.

## Layouts

| Layout | 2D | 3D |
|---|---|---|
| **Constelação** (`constel`) | anéis concêntricos por `ring` do tipo, comunidades agrupadas em arcos, jitter orgânico | mesmos anéis com profundidade |
| **Comunidades** (`communities`) | um disco phyllotaxis por comunidade, com folga entre grupos; hubs no centro | esferas separadas no espaço |
| **Camadas** (`layers`) | colunas por tipo (ordem = `ring`), fluxo esquerda→direita | discos paralelos |
| **Espiral/Globo** (`spiral`) | espiral áurea única (comunidades contíguas); tipos `hidden` viram halo externo | globo de Fibonacci; tipos `hidden` numa casca externa |

Todos são **determinísticos** (mesmo grafo → mesmas posições).

## Interface gerada

- **Topbar**: título, toggle **2D/3D**, seletor **Colorir por**, **Tela cheia** e
  **Resetar vista**.
- **Tela cheia**: a topbar some; o painel lateral vira retrátil — encoste o mouse
  na tira dourada da borda direita para reabrir. Um toggle 2D/3D flutuante e o
  botão de sair aparecem no topo. `Esc` sai.
- **Painel lateral**: busca com foco no nó, seletor de organização espacial,
  inspetor (propriedades, rankings por aresta, vizinhos navegáveis, isolar
  vizinhança), legenda com contagens e liga/desliga por tipo, seus painéis
  customizados, painel de comunidades e estatísticas.

## Solução de problemas

- **"endpoint(s) de aresta não existem"** — você adicionou `add_edge` para um id
  sem `add_node` correspondente; a mensagem lista os ausentes.
- **Valores `NaN`/`Inf` em `props`** (comuns em dados de pandas/Neo4j) — são
  convertidos para `null` automaticamente, então não quebram a página.
- **`props` com tipos numpy/`datetime`/`set`** — `numpy` vira número, datas viram
  ISO-8601 e conjuntos viram listas; qualquer outro objeto vira `str`.
- **3D abre com esferas simples por um instante** — o three.js carrega assíncrono;
  os medalhões são aplicados assim que ele termina (evento interno `three-ready`).
- **Arquivo grande demais** — use `inline_js=False` (CDN) ou publique o HTML com
  compressão (gzip reduz ~70%).
- **Nós demais deixando o 2D lento** — esconda os tipos numerosos por padrão
  (`add_type(..., hidden=True)`); o usuário liga na legenda quando quiser.

## Licença

MIT — © Diego Henrique Xavier. Bibliotecas embutidas: [vis-network](https://visjs.org)
(MIT/Apache-2.0), [3d-force-graph](https://github.com/vasturiano/3d-force-graph) (MIT),
[three.js](https://threejs.org) (MIT). Glifos: [Lucide](https://lucide.dev) (ISC).
