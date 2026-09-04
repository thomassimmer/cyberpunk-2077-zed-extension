#!/usr/bin/env python3
"""Render one SVG preview per theme from themes/cyberpunk.json.

Draws a mock Zed window — title bar, tab bar, project tree, gutter, a syntax
highlighted snippet, scrollbar and status bar — using the theme's own colours,
so the previews never drift from the themes. Output goes to assets/, and the
gallery is spliced into README.md between the previews markers.

Run: python3 scripts/generate_previews.py
"""

import json
import os

from generate_themes import FACTIONS

PREVIEW_W = 400  # rendered width in the README; two fit side by side
START = "<!-- previews:start -->"
END = "<!-- previews:end -->"

# --- geometry -------------------------------------------------------------
W = 760
TITLE_H = 30
TAB_H = 30
STATUS_H = 24
SIDEBAR_W = 190
GUTTER_W = 40
LINE_H = 18
CODE_TOP_PAD = 13
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
UI_FONT = "-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif"
CH = 7.22  # advance width of the monospace font at 12px

# --- content --------------------------------------------------------------
# (syntax token, text); "" falls back to editor.foreground.
CODE = [
    [("keyword.import", "use"), ("", " "), ("variable", "std"),
     ("punctuation.delimiter", "::"), ("variable", "net"),
     ("punctuation.delimiter", "::"), ("type", "TcpStream"),
     ("punctuation.delimiter", ";")],
    [],
    [("comment.doc", "/// Uplink to a corpo subnet.")],
    [("keyword", "pub"), ("", " "), ("keyword.declaration", "struct"), ("", " "),
     ("type", "Deck"), ("", " "), ("punctuation.bracket", "{")],
    [("", "    "), ("keyword", "pub"), ("", " "), ("property", "id"),
     ("punctuation.delimiter", ": "), ("type", "u32"),
     ("punctuation.delimiter", ",")],
    [("", "    "), ("keyword", "pub"), ("", " "), ("property", "ice"),
     ("punctuation.delimiter", ": "), ("type", "bool"),
     ("punctuation.delimiter", ",")],
    [("punctuation.bracket", "}")],
    [],
    [("keyword.declaration", "fn"), ("", " "), ("function", "breach"),
     ("punctuation.bracket", "("), ("variable", "host"),
     ("punctuation.delimiter", ": "), ("operator", "&"), ("type", "str"),
     ("punctuation.bracket", ")"), ("", " "), ("operator", "->"), ("", " "),
     ("type", "Result"), ("punctuation.bracket", "<"), ("type", "Deck"),
     ("punctuation.bracket", ">"), ("", " "), ("punctuation.bracket", "{")],
    [("", "    "), ("keyword", "let"), ("", " "), ("variable", "s"), ("", " "),
     ("operator", "="), ("", " "), ("type", "TcpStream"),
     ("punctuation.delimiter", "::"), ("function", "connect"),
     ("punctuation.bracket", "("), ("variable", "host"),
     ("punctuation.bracket", ")"), ("operator", "?"),
     ("punctuation.delimiter", ";")],
    [("", "    "), ("function", "println!"), ("punctuation.bracket", "("),
     ("string", '"breached {}"'), ("punctuation.delimiter", ", "),
     ("variable", "host"), ("punctuation.bracket", ")"),
     ("punctuation.delimiter", ";")],
    [("", "    "), ("constructor", "Ok"), ("punctuation.bracket", "("),
     ("type", "Deck"), ("", " "), ("punctuation.bracket", "{"), ("", " "),
     ("property", "id"), ("punctuation.delimiter", ": "), ("number", "2077"),
     ("punctuation.delimiter", ", "), ("property", "ice"),
     ("punctuation.delimiter", ": "), ("boolean", "false"), ("", " "),
     ("punctuation.bracket", "}"), ("punctuation.bracket", ")")],
    [("punctuation.bracket", "}")],
]
ACTIVE_LINE = 9  # 1-based, the `let s = ...` line

TREE = [
    ("CYBERPUNK", 0, "header"),
    ("src", 1, "dir"),
    ("main.rs", 2, "file"),
    ("deck.rs", 2, "selected"),
    ("ice.rs", 2, "file"),
    ("themes", 1, "dir"),
    ("cyberpunk.json", 2, "file"),
    ("Cargo.toml", 1, "file"),
    ("README.md", 1, "file"),
]

TABS = [("main.rs", False), ("deck.rs", True)]

H = TITLE_H + TAB_H + CODE_TOP_PAD * 2 + len(CODE) * LINE_H + STATUS_H


# --- svg helpers ----------------------------------------------------------
def paint(color):
    """Split #rrggbbaa into an SVG colour plus an opacity attribute."""
    c = color.lstrip("#")
    if len(c) == 8:
        a = int(c[6:8], 16) / 255
        if a < 0.999:
            return "#" + c[:6], ' fill-opacity="%.3f"' % a
    return "#" + c[:6], ""


def rect(x, y, w, h, color, rx=0):
    fill, op = paint(color)
    return '<rect x="%g" y="%g" width="%g" height="%g"%s fill="%s"%s/>' % (
        x, y, w, h, ' rx="%g"' % rx if rx else "", fill, op)


def stroke_rect(x, y, w, h, color):
    c = color.lstrip("#")
    op = ""
    if len(c) == 8 and int(c[6:8], 16) < 255:
        op = ' stroke-opacity="%.3f"' % (int(c[6:8], 16) / 255)
    return ('<rect x="%g" y="%g" width="%g" height="%g" fill="none" '
            'stroke="#%s"%s/>') % (x, y, w, h, c[:6], op)


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def label(x, y, text, color, size=12, font=FONT, weight=None, anchor=None):
    fill, op = paint(color)
    return (
        '<text x="%g" y="%g" font-family="%s" font-size="%g"%s%s fill="%s"%s'
        ' xml:space="preserve">%s</text>'
    ) % (
        x, y, font, size,
        ' font-weight="%s"' % weight if weight else "",
        ' text-anchor="%s"' % anchor if anchor else "",
        fill, op, esc(text),
    )


def build(theme):
    s = theme["style"]
    syntax = s["syntax"]
    body_y = TITLE_H + TAB_H
    body_h = H - body_y - STATUS_H
    main_x = SIDEBAR_W
    code_x = main_x + GUTTER_W + 10
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" role="img" aria-label="%s">'
        % (W, H, W, H, esc(theme["name"]))
    ]

    # panels and editor surface
    out.append(rect(0, 0, W, H, s["panel.background"]))
    out.append(rect(main_x, body_y, W - main_x, body_h, s["editor.background"]))
    out.append(rect(main_x, body_y, GUTTER_W, body_h, s["editor.gutter.background"]))

    # active line, spanning gutter and text
    active_y = body_y + CODE_TOP_PAD + (ACTIVE_LINE - 1) * LINE_H
    out.append(rect(main_x, active_y, W - main_x, LINE_H,
                    s["editor.active_line.background"]))

    # code
    for i, line in enumerate(CODE):
        base = body_y + CODE_TOP_PAD + i * LINE_H
        text_y = base + LINE_H - 5
        num = str(i + 1)
        is_active = i + 1 == ACTIVE_LINE
        out.append(label(
            main_x + GUTTER_W - 10, text_y, num,
            s["editor.active_line_number"] if is_active else s["editor.line_number"],
            size=11, anchor="end"))
        col = 0
        for token, text in line:
            color = syntax[token]["color"] if token else s["editor.foreground"]
            weight = 700 if token and syntax[token]["font_weight"] == 700 else None
            out.append(label(code_x + col * CH, text_y, text, color, weight=weight))
            col += len(text)

    # scrollbar
    out.append(rect(W - 9, body_y + 20, 5, 70, s["scrollbar.thumb.background"], rx=2.5))

    # project tree
    for i, (text, depth, kind) in enumerate(TREE):
        row_y = body_y + 8 + i * 20
        if kind == "selected":
            out.append(rect(0, row_y, SIDEBAR_W, 20, s["element.selected"]))
        x = 12 + depth * 12
        if kind == "header":
            out.append(label(x, row_y + 14, text, s["text"], size=10.5,
                             font=UI_FONT, weight=600))
            continue
        if kind == "dir":
            out.append(label(x, row_y + 14, "▾", s["icon.muted"], size=9,
                             font=UI_FONT))
            x += 11
        color = s["text"] if kind == "selected" else s["text.muted"]
        out.append(label(x, row_y + 14, text, color, size=11.5, font=UI_FONT))

    # tab bar
    out.append(rect(main_x, TITLE_H, W - main_x, TAB_H, s["tab_bar.background"]))
    tab_x = main_x
    for name, is_active in TABS:
        tab_w = 118
        out.append(rect(tab_x, TITLE_H, tab_w, TAB_H,
                        s["tab.active_background"] if is_active
                        else s["tab.inactive_background"]))
        out.append(rect(tab_x + tab_w - 1, TITLE_H, 1, TAB_H, s["border.variant"]))
        out.append(label(tab_x + 14, TITLE_H + 19, name,
                         s["text"] if is_active else s["text.muted"],
                         size=11.5, font=UI_FONT))
        tab_x += tab_w

    # title bar
    out.append(rect(0, 0, W, TITLE_H, s["title_bar.background"]))
    for i, dot in enumerate([s["error"], s["warning"], s["success"]]):
        out.append('<circle cx="%g" cy="15" r="5" fill="%s"%s/>'
                   % (16 + i * 16, *paint(dot)))
    out.append(label(72, 19, theme["name"], s["text"], size=11.5, font=UI_FONT,
                     weight=600))
    out.append(label(W - 14, 19, "cyberpunk", s["text.muted"], size=11.5,
                     font=UI_FONT, anchor="end"))

    # status bar
    out.append(rect(0, H - STATUS_H, W, STATUS_H, s["status_bar.background"]))
    out.append('<circle cx="16" cy="%g" r="4" fill="%s"%s/>'
               % (H - STATUS_H / 2, *paint(s["error"])))
    out.append(label(26, H - 8, "1", s["text.muted"], size=11, font=UI_FONT))
    out.append('<circle cx="42" cy="%g" r="4" fill="%s"%s/>'
               % (H - STATUS_H / 2, *paint(s["warning"])))
    out.append(label(52, H - 8, "3", s["text.muted"], size=11, font=UI_FONT))
    out.append(label(84, H - 8, "main", s["text.accent"], size=11, font=UI_FONT))
    out.append(label(W - 14, H - 8, "Ln 9, Col 12    Rust", s["text.muted"],
                     size=11, font=UI_FONT, anchor="end"))

    # borders, drawn last so they sit on top
    out.append(rect(SIDEBAR_W, body_y, 1, body_h, s["border.variant"]))
    out.append(rect(0, TITLE_H, W, 1, s["border.variant"]))
    out.append(rect(main_x, body_y, W - main_x, 1, s["border.variant"]))
    out.append(rect(0, H - STATUS_H, W, 1, s["border.variant"]))
    out.append(stroke_rect(0.5, 0.5, W - 1, H - 1, s["border"]))

    out.append("</svg>")
    return "\n".join(out)


def slug(name):
    return name.replace("Cyberpunk - ", "").lower().replace(" ", "-")


def gallery():
    """The README section: one collapsible block per faction, both variants."""
    blocks = [START]
    for i, (label, accent) in enumerate(FACTIONS):
        names = ["Cyberpunk - %s" % label, "Cyberpunk - %s Dark" % label]
        imgs = "".join(
            '<img src="assets/%s.svg" width="%d" alt="%s">'
            % (slug(n), PREVIEW_W, n) for n in names
        )
        blocks.append(
            "<details%s>\n<summary><b>%s</b> &nbsp;<code>%s</code></summary>\n"
            "<p>%s</p>\n</details>" % (" open" if i == 0 else "", label, accent, imgs)
        )
    blocks.append(END)
    return "\n\n".join(blocks)


def splice_readme(path):
    text = open(path).read()
    if START not in text or END not in text:
        print("! %s has no previews markers, skipped" % os.path.basename(path))
        return
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    open(path, "w").write(head + gallery() + tail)
    print("spliced gallery into %s" % os.path.basename(path))


def main():
    root = os.path.join(os.path.dirname(__file__), "..")
    themes = json.load(open(os.path.join(root, "themes", "cyberpunk.json")))["themes"]
    out_dir = os.path.join(root, "assets")
    os.makedirs(out_dir, exist_ok=True)
    for theme in themes:
        path = os.path.join(out_dir, "%s.svg" % slug(theme["name"]))
        with open(path, "w") as f:
            f.write(build(theme) + "\n")
    print("wrote %d previews to %s" % (len(themes), os.path.normpath(out_dir)))
    splice_readme(os.path.join(root, "README.md"))


if __name__ == "__main__":
    main()
