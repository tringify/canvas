#!/usr/bin/env python3
"""Copy shared markup and CSS from partials/ into the sections and theme blocks that mark where they go.

Markup: {%- comment -%}partial:NAME{%- endcomment -%} ... {%- comment -%}/partial:NAME{%- endcomment -%}
CSS:    /* partial:NAME */ ... /* /partial:NAME */
A partial can mark places for other partials too; they are filled in as it is copied.
Run before `tringify theme build`; `--check` exits non-zero when a section is out of date.
"""
import re, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
partials = root / "partials"
html_re = re.compile(r"(\{%- comment -%\}partial:([a-z0-9-]+)\{%- endcomment -%\})(.*?)(\{%- comment -%\}/partial:\2\{%- endcomment -%\})", re.S)
css_re = re.compile(r"(/\* partial:([a-z0-9-]+) \*/)(.*?)(/\* /partial:\2 \*/)", re.S)

def fill(regex, ext, text, depth=0):
    # A partial may itself mark where another partial goes (the phone field inside the sign-in form).
    if depth > 4:
        sys.exit("partials nest too deeply")
    def sub(m):
        body = (partials / f"{m.group(2)}.{ext}").read_text(encoding="utf-8").rstrip("\n")
        body = fill(regex, ext, body, depth + 1)
        return f"{m.group(1)}\n{body}\n{m.group(4)}"
    return regex.sub(sub, text)

# A partial that reads a variable each place must set first (the card's cv_wl: an unset name is an error when the page renders,
# which the theme check cannot see): the line before its start marker assigns it.
needs = {"card": "cv_wl", "pager": "cv_pg", "header-suggest": "cv_sg_id", "cart-lines": "cv_ls"}
missing = []
def check_needs(label, text):
    for m in html_re.finditer(text):
        var = needs.get(m.group(2))
        before = text[:m.start()].rstrip().rsplit("\n", 1)[-1]
        if var and not re.search(r"\{%-? assign " + var + r" = ", before):
            missing.append(f"{label}: assign {var} on the line before partial:{m.group(2)}")

stale = []
for section in sorted((root / "src" / "sections").iterdir()):
    for name, regex, ext in (("body.html", html_re, "html"), ("style.css", css_re, "css")):
        path = section / name
        if not path.exists():
            continue
        old = path.read_text(encoding="utf-8")
        if ext == "html":
            check_needs(f"{section.name}/{name}", old)
        new = fill(regex, ext, old)
        if new != old:
            stale.append(f"{section.name}/{name}")
            if "--check" not in sys.argv:
                path.write_text(new, encoding="utf-8")
# Theme blocks (blocks/<name>.vasc) take markup partials the same way.
for path in sorted((root / "blocks").glob("*.vasc")):
    old = path.read_text(encoding="utf-8")
    check_needs(f"blocks/{path.name}", old)
    new = fill(html_re, "html", old)
    if new != old:
        stale.append(f"blocks/{path.name}")
        if "--check" not in sys.argv:
            path.write_text(new, encoding="utf-8")
if missing:
    sys.exit("\n".join(missing))
if stale:
    print(("out of date: " if "--check" in sys.argv else "synced: ") + ", ".join(stale))
    sys.exit(1 if "--check" in sys.argv else 0)
