#!/usr/bin/env python3
"""把 README.md + 各章 Markdown 合并为一个带目录的 HTML，再用 Chromium 打印成 PDF。
用法: python3 tools/build_pdf.py   (在 图形推理教程/ 目录或任意目录运行均可)
依赖: pip install markdown-it-py mdit-py-plugins；Chromium（环境变量 CHROME 可指定路径）。
Markdown 按 CommonMark + GFM 表格解析，与 GitHub 网页上的显示保持一致。"""
import glob, os, re, subprocess, sys
from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
OUT_HTML = os.path.join(ROOT, "tools", "_book.html")
OUT_PDF = os.path.join(ROOT, "图形推理教程.pdf")

files = [os.path.join(ROOT, "README.md")] + sorted(glob.glob(os.path.join(ROOT, "[0-9][0-9]-*.md")))

CSS = """
@page { size: A4; margin: 14mm 13mm 16mm 13mm; }
html { font-size: 10.5pt; }
body { font-family: "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Zen Hei", sans-serif;
       line-height: 1.65; color: #222; max-width: 100%; }
h1 { font-size: 1.9em; color: #c2410c; border-bottom: 3px solid #fb923c; padding-bottom: .2em;
     break-before: page; margin-top: 0; }
h1.first { break-before: auto; }
h2 { font-size: 1.4em; color: #9a3412; border-left: 6px solid #fb923c; padding-left: .4em; margin-top: 1.4em; break-after: avoid; }
h3 { font-size: 1.15em; color: #7c2d12; margin-top: 1.1em; break-after: avoid; }
h4 { font-size: 1.02em; color: #444; break-after: avoid; }
p, li { orphans: 3; widows: 3; }
img { max-width: 100%; max-height: 118mm; display: block; margin: .5em auto; border: 1px solid #e5e7eb;
      border-radius: 4px; break-inside: avoid; }
blockquote { margin: .8em 0; padding: .5em .9em; background: #fff7ed; border-left: 4px solid #fb923c; color: #431407; }
blockquote p { margin: .3em 0; }
table { border-collapse: collapse; width: 100%; margin: .8em 0; font-size: .95em; break-inside: auto; }
th, td { border: 1px solid #d6d3d1; padding: .35em .5em; vertical-align: top; }
th { background: #ffedd5; }
tr { break-inside: avoid; }
code { background: #f5f5f4; padding: 0 .25em; border-radius: 3px; font-size: .92em; }
pre { background: #f5f5f4; padding: .6em; border-radius: 4px; white-space: pre; font-size: .8em; line-height: 1.45;
      font-family: "Noto Sans Mono CJK SC", "WenQuanYi Zen Hei Mono", monospace; break-inside: auto; }
pre code { background: none; padding: 0; font-size: 1em; font-family: inherit; }
strong { color: #9a3412; }
hr { border: none; border-top: 1px dashed #d6d3d1; margin: 1.2em 0; }
nav.toc { break-after: page; }
nav.toc h1 { break-before: auto; }
nav.toc ul { list-style: none; padding-left: 1em; }
nav.toc > ul { padding-left: 0; }
nav.toc a { color: #222; text-decoration: none; }
nav.toc li.l1 { font-weight: bold; margin-top: .5em; }
a { color: #c2410c; }
"""

def slug_base(path):
    return os.path.splitext(os.path.basename(path))[0]

parts, toc = [], []
for i, f in enumerate(files):
    src = open(f, encoding="utf-8").read()
    base = slug_base(f)
    md = (MarkdownIt("commonmark", {"html": True}).enable("table").enable("strikethrough")
          .use(anchors_plugin, min_level=1, max_level=2,
               slug_func=lambda v, b=base: f"{b}-" + re.sub(r"\W+", "-", v).strip("-")))
    tokens = md.parse(src)
    for k, t in enumerate(tokens):
        if i > 0 and t.type == "heading_open" and t.tag in ("h1", "h2"):
            toc.append((int(t.tag[1]), tokens[k + 1].content, t.attrGet("id")))
    html = md.renderer.render(tokens, md.options, {})
    # 章节间的相对链接 xxx.md -> 锚点
    html = re.sub(r'href="(\d\d-[^"#]+|README)\.md(#[^"]*)?"', lambda m: f'href="#{m.group(1)}-top"', html)
    if i == 0:
        html = html.replace("<h1", '<h1 class="first"', 1)
    parts.append(f'<section id="{base}-top">{html}</section>')

toc_html = ['<nav class="toc"><h1>目录</h1><ul>']
import html as _h
for lvl, name, anchor in toc:
    name = re.sub(r"[*`]", "", name)
    toc_html.append(f'<li class="l{lvl}" style="margin-left:{(lvl-1)*1.2}em"><a href="#{anchor}">{_h.escape(name)}</a></li>')
toc_html.append("</ul></nav>")

body = parts[0] + "".join(toc_html) + "".join(parts[1:])
doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<base href="file://{ROOT}/"><title>图形推理教程</title><style>{CSS}</style></head><body>{body}</body></html>"""
open(OUT_HTML, "w", encoding="utf-8").write(doc)
cmd = [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
       "--allow-file-access-from-files", f"--print-to-pdf={OUT_PDF}", "file://" + OUT_HTML]
subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
print(OUT_PDF, f"{os.path.getsize(OUT_PDF)/1e6:.1f} MB")
