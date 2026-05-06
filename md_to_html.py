"""
Convert IWI markdown docs to styled HTML with Mermaid support.
Run:  python3 md_to_html.py          — regenerates all docs
      python3 md_to_html.py file.md  — regenerates one file
"""
import re, sys, html, os

DOC = os.path.dirname(os.path.abspath(__file__))

# ── inline markdown ───────────────────────────────────────────────────────────
def esc(s): return html.escape(s)

def inline(s):
    s = re.sub(r'`([^`]+)`', lambda m: f'<code>{esc(m.group(1))}</code>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*',     r'<em>\1</em>', s)
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
    return s

def make_back_btn(href):
    return (
        '<div class="back-bar">'
        f'<a class="back-btn" href="{href}">'
        '<svg width="13" height="13" viewBox="0 0 14 14" fill="none">'
        '<path d="M8.5 2.5L4 7l4.5 4.5" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>Back to Index</a></div>'
    )

def slug(text):
    s = text.lower()
    s = re.sub(r'[/()\'\",.]', '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')

# ── block converter ───────────────────────────────────────────────────────────
def convert(md, back_href="index.html"):
    lines = md.split('\n')
    out = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # back-link shortcut — render as the styled button
        if re.match(r'^\[.{0,6}Back to Index\]', line):
            out.append(make_back_btn(back_href))
            i += 1
            continue

        # fenced code block
        if line.strip().startswith('```'):
            lang = line.strip()[3:].strip()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                block.append(lines[i])
                i += 1
            code = '\n'.join(block)
            if lang == 'mermaid':
                out.append(f'<div class="mw"><pre class="mermaid">{esc(code)}</pre></div>')
            else:
                lc = esc(lang) if lang else ''
                out.append(f'<pre class="cb"><code class="l-{lc}">{esc(code)}</code></pre>')
            i += 1
            continue

        # blockquote
        if line.startswith('>'):
            out.append(f'<blockquote>{inline(esc(line[1:].strip()))}</blockquote>')
            i += 1; continue

        # HR
        if re.match(r'^---+$', line.strip()):
            out.append('<hr>'); i += 1; continue

        # headings
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            lv, text = len(m.group(1)), m.group(2)
            # strip trailing hashes
            text = re.sub(r'\s+#+\s*$', '', text)
            out.append(f'<h{lv} id="{slug(text)}">{inline(esc(text))}</h{lv}>')
            i += 1; continue

        # table (line + separator)
        if '|' in line and i+1 < len(lines) and re.match(r'^[\|\s\-:]+$', lines[i+1]):
            headers = [c.strip() for c in line.strip().strip('|').split('|')]
            i += 2
            rows = []
            while i < len(lines) and '|' in lines[i]:
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            th = ''.join(f'<th>{inline(esc(h))}</th>' for h in headers)
            body = ''.join(
                '<tr>' + ''.join(f'<td>{inline(esc(c))}</td>' for c in r) + '</tr>'
                for r in rows
            )
            out.append(f'<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>')
            continue

        # unordered list
        if re.match(r'^\s*[-*]\s+', line):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*]\s+', lines[i]):
                items.append(re.sub(r'^\s*[-*]\s+', '', lines[i]))
                i += 1
            lis = ''.join(f'<li>{inline(esc(it))}</li>' for it in items)
            out.append(f'<ul>{lis}</ul>')
            continue

        # ordered list
        if re.match(r'^\d+\.\s+', line):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i]):
                items.append(re.sub(r'^\d+\.\s+', '', lines[i]))
                i += 1
            lis = ''.join(f'<li>{inline(esc(it))}</li>' for it in items)
            out.append(f'<ol>{lis}</ol>')
            continue

        # blank line
        if line.strip() == '':
            out.append(''); i += 1; continue

        # paragraph
        out.append(f'<p>{inline(esc(line))}</p>')
        i += 1

    return '\n'.join(out)

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
:root{
  --bd:#0052CC;--bl:#DEEBFF;--gl:#E3FCEF;--yl:#FFFAE6;
  --gb:#F4F5F7;--gb2:#DFE1E6;--tx:#172B4D;--tm:#5E6C84;
  --red:#FF5630;--green:#36B37E
}
*{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  font-size:13.5px;line-height:1.45;color:var(--tx);background:#F4F5F7
}
.pw{max-width:1280px;margin:0 auto;background:#fff;min-height:100vh;
    box-shadow:0 0 0 1px var(--gb2)}

/* ── header ── */
.ph{background:var(--bd);color:#fff;padding:10px 52px 9px;
    border-bottom:3px solid #0065FF;display:flex;align-items:baseline;gap:18px}
.ph .t{font-size:16px;font-weight:700;letter-spacing:.2px}
.ph .m{font-size:11px;opacity:.75}

/* ── back bar ── */
.back-bar{background:#fff;border-bottom:1px solid var(--gb2);
          padding:4px 52px;display:flex;align-items:center}
.back-btn{display:inline-flex;align-items:center;gap:5px;color:var(--bd);
          font-size:11px;font-weight:600;text-decoration:none;
          padding:2px 8px;border:1px solid var(--bd);border-radius:3px;
          background:#fff;transition:background .12s,color .12s;line-height:1.4}
.back-btn:hover{background:var(--bd);color:#fff}
.back-btn svg{flex-shrink:0}

/* ── content ── */
.ct{padding:14px 52px 28px}

h1{font-size:18px;margin:0 0 6px;padding-bottom:4px;
   border-bottom:2px solid var(--bd);display:none}
h2{font-size:14px;font-weight:700;margin:18px 0 5px;
   padding:4px 10px;background:var(--bl);
   border-left:3px solid var(--bd);border-radius:2px}
h3{font-size:13px;font-weight:700;margin:10px 0 3px;color:var(--bd)}
h4{font-size:12.5px;font-weight:700;margin:8px 0 3px}

p{margin:3px 0}
strong{font-weight:700}
em{font-style:italic}
code{background:var(--gb);border:1px solid var(--gb2);border-radius:3px;
     padding:0 5px;font-size:12px;
     font-family:'SFMono-Regular',Consolas,monospace;color:#C0392B}
a{color:var(--bd);text-decoration:none}
a:hover{text-decoration:underline}

/* ── code block ── */
pre.cb{background:#1e1e2e;color:#cdd6f4;border-radius:5px;
       padding:8px 14px;overflow-x:auto;margin:5px 0;font-size:11.5px;
       font-family:'SFMono-Regular',Consolas,monospace;line-height:1.4}
pre.cb code{background:none;border:none;color:inherit;padding:0;font-size:inherit}

/* ── mermaid ── */
.mw{background:#fafbfc;border:1px solid var(--gb2);border-radius:6px;
    padding:10px 8px;margin:6px 0;overflow:hidden;position:relative;
    cursor:grab;min-height:60px;text-align:center}
.mw pre.mermaid{display:inline-block;text-align:left;
                background:none;border:none;padding:0;max-width:100%}
.zm-bar{position:absolute;top:6px;right:8px;display:flex;gap:3px;z-index:20}
.zm-btn{background:rgba(255,255,255,.92);border:1px solid var(--gb2);border-radius:3px;
        padding:1px 8px;font-size:14px;font-weight:700;cursor:pointer;
        color:var(--tx);line-height:1.5;transition:background .1s,color .1s}
.zm-btn:hover{background:var(--bd);color:#fff;border-color:var(--bd)}

/* ── table ── */
table{border-collapse:collapse;width:100%;margin:5px 0;font-size:12.5px;
      border:1px solid var(--gb2);border-radius:5px;overflow:hidden}
thead{background:var(--bd);color:#fff}
thead th{padding:4px 10px;text-align:left;font-weight:600;font-size:11.5px}
tbody tr{background:#fff}
tbody tr:nth-child(even){background:var(--gb)}
tbody tr:hover{background:var(--bl)}
td{padding:3px 10px;border-bottom:1px solid var(--gb2);vertical-align:top}

/* ── lists ── */
ul,ol{margin:3px 0 3px 18px}
li{margin:1px 0}

/* ── misc ── */
blockquote{border-left:3px solid #FF8B00;background:var(--yl);
           padding:4px 12px;margin:5px 0;border-radius:0 3px 3px 0;font-size:12.5px}
hr{border:none;border-top:1px solid var(--gb2);margin:12px 0}

/* ── footer ── */
.pf{background:var(--gb);border-top:1px solid var(--gb2);
    padding:6px 52px;font-size:11px;color:var(--tm)}

/* ── floating back button ── */
.back-float{position:fixed;bottom:18px;right:22px;z-index:200;
            display:inline-flex;align-items:center;gap:5px;
            background:var(--bd);color:#fff;border-radius:4px;
            padding:5px 13px;font-size:12px;font-weight:600;
            text-decoration:none;box-shadow:0 2px 10px rgba(0,0,82,.28);
            transition:background .12s}
.back-float:hover{background:#0065FF;color:#fff;text-decoration:none}
"""

MERMAID_INIT = """
mermaid.initialize({
  startOnLoad: true,
  theme: 'base',
  themeVariables: {
    primaryColor:'#DEEBFF', primaryTextColor:'#172B4D',
    primaryBorderColor:'#0052CC', lineColor:'#0052CC',
    secondaryColor:'#E3FCEF', tertiaryColor:'#F4F5F7',
    noteBkgColor:'#FFFAE6', noteTextColor:'#172B4D',
    actorBkg:'#0052CC', actorTextColor:'#ffffff',
    actorBorderColor:'#003d99', activationBkgColor:'#DEEBFF',
    signalColor:'#172B4D', signalTextColor:'#172B4D'
  },
  sequence:{ actorMargin:55, messageMargin:30, mirrorActors:false, boxMargin:8 },
  flowchart:{ htmlLabels:true, curve:'basis', padding:16 },
  gantt:{ axisFormat:'%M', leftPadding:110 }
});
"""

ZOOM_JS = """
(function(){
  function initZoom(wrap){
    if(wrap.dataset.zm)return;
    var svg=wrap.querySelector('svg');
    if(!svg)return;
    wrap.dataset.zm='1';
    var target=svg;
    while(target.parentNode && target.parentNode!==wrap){target=target.parentNode;}
    target.style.transformOrigin='0 0';
    target.style.userSelect='none';
    target.style.display='inline-block';
    target.style.maxWidth='none';
    // Capture natural (centered) offset of target inside wrap before any transforms
    var wr=wrap.getBoundingClientRect(),tr=target.getBoundingClientRect();
    var ox=tr.left-wr.left, oy=tr.top-wr.top;
    var scale=1,tx=0,ty=0,drag=false,sx=0,sy=0,stx=0,sty=0;
    function ap(){target.style.transform='translate('+tx+'px,'+ty+'px) scale('+scale+')';}
    var bar=document.createElement('div');bar.className='zm-bar';
    bar.innerHTML='<button class="zm-btn" data-a="in" title="Zoom in">+</button>'
      +'<button class="zm-btn" data-a="out" title="Zoom out">−</button>'
      +'<button class="zm-btn" data-a="r" title="Reset">↺</button>';
    wrap.appendChild(bar);
    bar.addEventListener('click',function(e){
      e.stopPropagation();
      var b=e.target.closest('[data-a]');if(!b)return;
      var cx=wrap.clientWidth/2-ox,cy=wrap.clientHeight/2-oy,ns;
      if(b.dataset.a==='in'){ns=Math.min(scale*1.3,8);tx=cx-(cx-tx)*(ns/scale);ty=cy-(cy-ty)*(ns/scale);scale=ns;}
      else if(b.dataset.a==='out'){ns=Math.max(scale/1.3,.1);tx=cx-(cx-tx)*(ns/scale);ty=cy-(cy-ty)*(ns/scale);scale=ns;}
      else{scale=1;tx=0;ty=0;}
      ap();
    });
    wrap.addEventListener('wheel',function(e){
      e.preventDefault();
      var r=wrap.getBoundingClientRect();
      var mx=e.clientX-r.left-ox,my=e.clientY-r.top-oy;
      var d=e.deltaY<0?1.12:.89,ns=Math.min(Math.max(scale*d,.1),8);
      tx=mx-(mx-tx)*(ns/scale);ty=my-(my-ty)*(ns/scale);scale=ns;ap();
    },{passive:false});
    wrap.addEventListener('mousedown',function(e){
      if(e.target.closest('.zm-btn'))return;
      drag=true;sx=e.clientX;sy=e.clientY;stx=tx;sty=ty;
      wrap.style.cursor='grabbing';e.preventDefault();
    });
    document.addEventListener('mousemove',function(e){
      if(!drag)return;tx=stx+(e.clientX-sx);ty=sty+(e.clientY-sy);ap();
    });
    document.addEventListener('mouseup',function(){
      if(drag){drag=false;wrap.style.cursor='grab';}
    });
  }
  var attempts=0;
  var t=setInterval(function(){
    document.querySelectorAll('.mw').forEach(initZoom);
    if(++attempts>40)clearInterval(t);
  },150);
})();
"""

TITLES = {
    'oauth01_flow_diagram.md':  'oauth01 — Flow Diagrams',
    'oauth01_api_list.md':      'oauth01 — API Reference',
    'userauth01_flow_diagram.md': 'userauth01 — Flow Diagrams',
    'userauth01_api_list.md':   'userauth01 — API Reference',
    'dev_manual.md':            'IWI Developer Manual',
}

FOOTERS = {
    'oauth01_flow_diagram.md':  'Reference: RFC 6749 · © Funai Soken Digital',
    'oauth01_api_list.md':      'Reference: RFC 6749 · © Funai Soken Digital',
    'userauth01_flow_diagram.md': '© Funai Soken Digital — IWI Documentation',
    'userauth01_api_list.md':   '© Funai Soken Digital — IWI Documentation',
    'dev_manual.md':            '© Funai Soken Digital — IWI Documentation',
}

# ── build one HTML file ───────────────────────────────────────────────────────
def build(src_path):
    fname = os.path.basename(src_path)
    src_dir = os.path.dirname(os.path.abspath(src_path))
    # Use ../index.html for files inside a subfolder, index.html for root-level
    back_href = "../index.html" if src_dir != DOC else "index.html"

    title  = TITLES.get(fname, fname.replace('_', ' ').replace('.md', ''))
    footer = FOOTERS.get(fname, '© Funai Soken Digital')

    with open(src_path, encoding='utf-8') as f:
        md = f.read()

    body = convert(md, back_href)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div class="pw">
<div class="ph">
  <span class="t">{esc(title)}</span>
  <span class="m">IWI — Integrated Web Infrastructure · Funai Soken Digital</span>
</div>
{body}
<div class="pf">{esc(footer)}</div>
</div>
<a class="back-float" href="{back_href}">
<svg width="11" height="11" viewBox="0 0 14 14" fill="none">
<path d="M8.5 2.5L4 7l4.5 4.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>Index</a>
<script>{MERMAID_INIT}</script>
<script>{ZOOM_JS}</script>
</body>
</html>"""


# ── main ──────────────────────────────────────────────────────────────────────
SOURCES = [
    os.path.join(DOC, 'oauth',    'oauth01_flow_diagram.md'),
    os.path.join(DOC, 'oauth',    'oauth01_api_list.md'),
    os.path.join(DOC, 'userauth', 'userauth01_flow_diagram.md'),
    os.path.join(DOC, 'userauth', 'userauth01_api_list.md'),
    os.path.join(DOC,             'dev_manual.md'),
]

if __name__ == '__main__':
    if len(sys.argv) > 1:
        targets = [sys.argv[1]]
    else:
        targets = SOURCES

    for src in targets:
        out = src.replace('.md', '.html')
        html_out = build(src)
        with open(out, 'w', encoding='utf-8') as f:
            f.write(html_out)
        print(f'OK  {os.path.basename(out)}')
