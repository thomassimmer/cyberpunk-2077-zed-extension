#!/usr/bin/env python3
"""Generate themes/cyberpunk.json.

Each faction is derived from a single accent colour and ships in two
variants: the default one is built on Zed's One Dark greys, the "Dark" one on
the darker One Dark Pro greys. Panels, buttons and other chrome come from those
base themes; the accent carries the faction identity through borders, cursor,
selection, active line and a subtle tint on the title/status bar. Syntax
colours are the theme's own VS Code Dark+ palette, unchanged.

Run: python3 scripts/generate_themes.py
"""

import colorsys
import json
import os

# --- tunables -------------------------------------------------------------
BORDER_MIX = 1  # how much accent in regular borders (1.0 = raw accent)
CHROME_TINT = 0.12  # accent tint on title bar / status bar
TAB_TINT = 0.07  # accent tint on the active tab
ACTIVE_LINE_TINT = 0.10  # accent tint on the active editor line
MIN_ACCENT_CONTRAST = 3.0  # accent readability vs. the surface it sits on

FACTIONS = [
    ("Biotechnica", "#358a74"),
    ("Softsys", "#009090"),
    ("Arasaka", "#cc0000"),
    ("Militech", "#e6d709"),
    ("Kang tao", "#e16b27"),
    ("NCPD", "#445e88"),
    ("Delamain", "#a0a0a0"),
    ("Pink neon", "#c871af"),
    ("Mox", "#9b59d0"),
]


# --- colour helpers -------------------------------------------------------
def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _hex(rgb):
    r, g, b = (max(0, min(255, round(c * 255))) for c in rgb)
    return "#%02x%02x%02xff" % (r, g, b)


def mix(base, accent, ratio):
    """Opaque blend: `ratio` of accent over base. Predictable, unlike alpha."""
    b, a = _rgb(base), _rgb(accent)
    return _hex(tuple(b[i] * (1 - ratio) + a[i] * ratio for i in range(3)))


def luminance(hex_color):
    def chan(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(c) for c in _rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    lo, hi = sorted((la, lb))
    return (hi + 0.05) / (lo + 0.05)


def relight(hex_color, lightness):
    h, _, s = colorsys.rgb_to_hls(*_rgb(hex_color))
    return _hex(colorsys.hls_to_rgb(h, max(0.0, min(1.0, lightness)), s))


def lighten_to_contrast(hex_color, background, target):
    """Lighten `hex_color` until it reaches `target` contrast on `background`.

    Hue and saturation are preserved, so the colour stays recognisable. Dark
    accents such as Arasaka's red would otherwise vanish into the grey.
    """
    if contrast(hex_color, background) >= target:
        return hex_color
    _, l, _ = colorsys.rgb_to_hls(*_rgb(hex_color))
    while l <= 1.0:
        l += 0.02
        candidate = relight(hex_color, l)
        if contrast(candidate, background) >= target:
            return candidate
    return relight(hex_color, 1.0)


def dim(hex_color, factor=0.62):
    """A darker sibling of `hex_color`, for the terminal's dim ANSI slots."""
    _, l, _ = colorsys.rgb_to_hls(*_rgb(hex_color))
    return relight(hex_color, l * factor)


def alpha(hex_color, aa):
    return hex_color[:7] + aa


# --- base palettes --------------------------------------------------------
# Verbatim from zed/assets/themes/one/one.json (One Dark) and the One Dark Pro
# extension. Where One Dark Pro leaves a key unset, One Dark's value is used.

ONE_DARK = dict(
    editor="#282c33",
    toolbar="#282c33",
    surface="#2f343e",
    elevated="#2f343e",
    tab_bar="#2f343e",
    tab_inactive="#2f343e",
    chrome="#3b414d",  # title bar
    status_chrome="#3b414d",
    title_bar_inactive="#2f343e",
    element="#2e343e",
    element_hover="#363c46",
    element_active="#454a56",
    element_selected="#454a56",
    element_disabled="#2e343e",
    border="#464b57",
    border_variant="#363c46",
    border_disabled="#414754",
    text="#B0B0B0ff",  # kept from the original Cyberpunk themes
    text_muted="#a9afbcff",
    text_dim="#878a98ff",
    icon="#dce0e5ff",
    icon_muted="#a9afbcff",
    accent_ui="#74ade8ff",  # One Dark blue: links, info, renamed
    editor_fg="#FFFFFFff",  # kept from the original Cyberpunk themes
    line_number="#4e5a5f",
    active_line_number="#d0d4da",
    hover_line_number="#acb0b4",
    invisible="#878a98ff",
    wrap_guide="#c8ccd40d",
    wrap_guide_active="#c8ccd41a",
    indent_guide="#3b4048ff",
    indent_guide_active="#c8c8c859",
    highlight_read="#74ade81a",
    highlight_write="#555a6366",
    scroll_track_border="#2e333cff",
    minimap_border="#363c46ff",
    drop_target="#83899480",
    search_match="#74ade866",
    search_active="#e8af7466",
)

# One Dark Pro: flatter and a couple of steps darker than One Dark.
ONE_DARK_PRO = dict(
    ONE_DARK,
    editor="#23272e",
    toolbar="#23272e",
    surface="#23272e",
    elevated="#1e2227",
    tab_bar="#1e2227",
    tab_inactive="#1e2227",
    chrome="#23272e",
    status_chrome="#1e2227",
    title_bar_inactive="#1e2227",
    element="#404754",
    element_hover="#2c313a",
    element_active="#404754",
    element_selected="#2c313a",
    element_disabled="#2c313a",
    border="#3e4452",
    border_variant="#3e4452",
    border_disabled="#3e4452",
    line_number="#495162",
    active_line_number="#abb2bfff",
    wrap_guide="#3e4452ff",
    wrap_guide_active="#3e4452ff",
    highlight_read="#555a6345",
    highlight_write="#555a6345",
    scroll_track_border="#1e2227ff",
    minimap_border="#3e4452ff",
    search_match="#d19a6644",
)


# --- diagnostics & version control ---------------------------------------
ONE_DARK_STATUS = {
    "conflict": "#dec184ff",
    "conflict.background": "#dec1841a",
    "conflict.border": "#5d4c2fff",
    "created": "#a1c181ff",
    "created.background": "#a1c1811a",
    "created.border": "#38482fff",
    "deleted": "#d07277ff",
    "deleted.background": "#d072771a",
    "deleted.border": "#4c2b2cff",
    "error": "#d07277ff",
    "error.background": "#d072771a",
    "error.border": "#4c2b2cff",
    "hidden": "#878a98ff",
    "hidden.background": "#696b771a",
    "hidden.border": "#414754ff",
    "hint": "#788ca6ff",
    "hint.background": "#5a6f891a",
    "hint.border": "#293b5bff",
    "ignored": "#878a98ff",
    "ignored.background": "#696b771a",
    "ignored.border": "#464b57ff",
    "info": "#74ade8ff",
    "info.background": "#74ade81a",
    "info.border": "#293b5bff",
    "modified": "#dec184ff",
    "modified.background": "#dec1841a",
    "modified.border": "#5d4c2fff",
    "predictive": "#5a6a87ff",
    "predictive.background": "#5a6a871a",
    "predictive.border": "#38482fff",
    "renamed": "#74ade8ff",
    "renamed.background": "#74ade81a",
    "renamed.border": "#293b5bff",
    "success": "#a1c181ff",
    "success.background": "#a1c1811a",
    "success.border": "#38482fff",
    "unreachable": "#a9afbcff",
    "unreachable.background": "#8389941a",
    "unreachable.border": "#464b57ff",
    "warning": "#dec184ff",
    "warning.background": "#dec1841a",
    "warning.border": "#5d4c2fff",
    "version_control.added": "#27a657ff",
    "version_control.modified": "#d3b020ff",
    "version_control.deleted": "#e06c76ff",
    "version_control.renamed": "#74ade8ff",
    "version_control.conflict": "#dec184ff",
    "version_control.ignored": "#878a98ff",
    "version_control.word_added": "#2EA04859",
    "version_control.word_deleted": "#78081BCC",
    "version_control.conflict_marker.ours": "#a1c1811a",
    "version_control.conflict_marker.theirs": "#74ade81a",
}

# Only the keys One Dark Pro actually sets; the rest fall back to One Dark.
ONE_DARK_PRO_STATUS = dict(
    ONE_DARK_STATUS,
    **{
        "created": "#a5e075ff",
        "deleted": "#ff616eff",
        "error": "#c24038ff",
        "error.border": "#a03237ff",
        "hint": "#7a849cff",
        "hint.border": "#013b64ff",
        "ignored": "#636b78ff",
        "modified": "#e5c07bff",
        "predictive": "#4D5970ff",
        "warning": "#d19a66ff",
        "warning.border": "#89734dff",
        "version_control.added": "#a5e075ff",
        "version_control.modified": "#e5c07bff",
        "version_control.deleted": "#ff616eff",
        "version_control.ignored": "#636b78ff",
    }
)

# --- terminal -------------------------------------------------------------
ONE_DARK_TERMINAL = {
    "terminal.foreground": "#abb2bfff",
    "terminal.bright_foreground": "#dce0e5ff",
    "terminal.dim_foreground": "#636d83ff",
    "terminal.ansi.black": "#282c34ff",
    "terminal.ansi.bright_black": "#636d83ff",
    "terminal.ansi.dim_black": "#3b3f4aff",
    "terminal.ansi.red": "#e06c75ff",
    "terminal.ansi.bright_red": "#EA858Bff",
    "terminal.ansi.dim_red": "#a7545aff",
    "terminal.ansi.green": "#98c379ff",
    "terminal.ansi.bright_green": "#AAD581ff",
    "terminal.ansi.dim_green": "#6d8f59ff",
    "terminal.ansi.yellow": "#e5c07bff",
    "terminal.ansi.bright_yellow": "#FFD885ff",
    "terminal.ansi.dim_yellow": "#b8985bff",
    "terminal.ansi.blue": "#61afefff",
    "terminal.ansi.bright_blue": "#85C1FFff",
    "terminal.ansi.dim_blue": "#457cadff",
    "terminal.ansi.magenta": "#c678ddff",
    "terminal.ansi.bright_magenta": "#D398EBff",
    "terminal.ansi.dim_magenta": "#8d54a0ff",
    "terminal.ansi.cyan": "#56b6c2ff",
    "terminal.ansi.bright_cyan": "#6ED5DEff",
    "terminal.ansi.dim_cyan": "#3c818aff",
    "terminal.ansi.white": "#abb2bfff",
    "terminal.ansi.bright_white": "#fafafaff",
    "terminal.ansi.dim_white": "#8f969bff",
}

# One Dark Pro's ANSI set. It defines no dim_* slots, so those are derived
# from the matching base colour.
ONE_DARK_PRO_ANSI = {
    "black": ("#3f4451ff", "#4f5666ff"),
    "red": ("#e05561ff", "#ff616eff"),
    "green": ("#8cc265ff", "#a5e075ff"),
    "yellow": ("#d18f52ff", "#f0a45dff"),
    "blue": ("#4aa5f0ff", "#4dc4ffff"),
    "magenta": ("#c162deff", "#de73ffff"),
    "cyan": ("#42b3c2ff", "#4cd1e0ff"),
    "white": ("#d7dae0ff", "#e6e6e6ff"),
}


def build_pro_terminal():
    t = {
        "terminal.foreground": "#abb2bfff",
        "terminal.bright_foreground": "#d7dae0ff",
        "terminal.dim_foreground": "#636d83ff",
    }
    for name, (base, bright) in ONE_DARK_PRO_ANSI.items():
        t["terminal.ansi.%s" % name] = base
        t["terminal.ansi.bright_%s" % name] = bright
        t["terminal.ansi.dim_%s" % name] = dim(base)
    return t


ONE_DARK_PRO_TERMINAL = build_pro_terminal()

# The original Cyberpunk syntax palette (VS Code Dark+), unchanged.
SYNTAX = {
    "attribute": "#9CDCFE",
    "boolean": "#569CD6",
    "comment": "#6A9955",
    "comment.doc": "#6A9955",
    "constant": "#4FC1FF",
    "constructor": "#569CD6",
    "embedded": "#D4D4D4",
    "emphasis.strong": "#569CD6",
    "function": "#DCDCAA",
    "keyword": "#569CD6",
    "keyword.declaration": "#569CD6",
    "keyword.control": "#C586C0",
    "keyword.import": "#C586C0",
    "number": "#B5CEA8",
    "operator": "#D4D4D4",
    "preproc": "#569CD6",
    "property": "#9CDCFE",
    "punctuation": "#CCCCCC",
    "punctuation.bracket": "#CCCCCC",
    "punctuation.delimiter": "#CCCCCC",
    "punctuation.list_marker": "#CCCCCC",
    "punctuation.special": "#569CD6",
    "string": "#CE9178",
    "string.escape": "#D7BA7D",
    "string.regex": "#D16969",
    "string.special": "#D16969",
    "string.special.symbol": "#D16969",
    "tag": "#569CD6",
    "text.literal": "#CE9178",
    "type": "#4EC9B0",
    "variable": "#9CDCFE",
    "variable.special": "#569CD6",
}
SYNTAX_BOLD = {"emphasis.strong"}

# Players 2..9, from One Dark. Slot 1 is the faction accent.
PLAYERS = [
    "#74ade8ff",
    "#be5046ff",
    "#bf956aff",
    "#b477cfff",
    "#6eb4bfff",
    "#d07277ff",
    "#dec184ff",
    "#a1c181ff",
]

# (name suffix, surfaces, diagnostics, terminal)
VARIANTS = [
    ("", ONE_DARK, ONE_DARK_STATUS, ONE_DARK_TERMINAL),
    (" Dark", ONE_DARK_PRO, ONE_DARK_PRO_STATUS, ONE_DARK_PRO_TERMINAL),
]


def build_syntax():
    return {
        token: {
            "color": color,
            "background_color": None,
            "font_style": None,
            "font_weight": 700 if token in SYNTAX_BOLD else None,
        }
        for token, color in SYNTAX.items()
    }


def build_style(accent, p, status, terminal):
    # Keep the faction hue but guarantee it reads against the surface it sits on.
    ui = lighten_to_contrast(accent, p["surface"], MIN_ACCENT_CONTRAST)
    on_editor = lighten_to_contrast(accent, p["editor"], MIN_ACCENT_CONTRAST)

    style = {
        # --- borders: the faction's signature lines ---
        "border": mix(p["border"], ui, BORDER_MIX),
        "border.variant": mix(p["border_variant"], ui, BORDER_MIX * 0.6),
        "border.focused": ui,
        "border.selected": mix(p["chrome"], ui, 0.45),
        "border.transparent": "#00000000",
        "border.disabled": p["border_disabled"] + "ff",
        # --- surfaces: One Dark / One Dark Pro, with a faint faction tint ---
        "elevated_surface.background": p["elevated"] + "ff",
        "surface.background": p["surface"] + "ff",
        "background": mix(p["chrome"], accent, CHROME_TINT * 0.65),
        "element.background": p["element"] + "ff",
        "element.hover": mix(p["element_hover"], accent, 0.18),
        "element.active": mix(p["element_active"], accent, 0.28),
        "element.selected": mix(p["element_selected"], accent, 0.28),
        "element.disabled": p["element_disabled"] + "ff",
        "drop_target.background": p["drop_target"],
        "ghost_element.background": "#00000000",
        "ghost_element.hover": mix(p["element_hover"], accent, 0.18),
        "ghost_element.active": mix(p["element_active"], accent, 0.28),
        "ghost_element.selected": mix(p["element_selected"], accent, 0.28),
        "ghost_element.disabled": p["element_disabled"] + "ff",
        # --- text & icons ---
        "text": p["text"],
        "text.muted": p["text_muted"],
        "text.placeholder": p["text_dim"],
        "text.disabled": p["text_dim"],
        "text.accent": p["accent_ui"],
        "icon": p["icon"],
        "icon.muted": p["icon_muted"],
        "icon.disabled": p["text_dim"],
        "icon.placeholder": p["icon_muted"],
        "icon.accent": p["accent_ui"],
        # --- chrome ---
        "status_bar.background": mix(p["status_chrome"], accent, CHROME_TINT),
        "title_bar.background": mix(p["chrome"], accent, CHROME_TINT),
        "title_bar.inactive_background": p["title_bar_inactive"] + "ff",
        "toolbar.background": p["toolbar"] + "ff",
        "tab_bar.background": p["tab_bar"] + "ff",
        "tab.inactive_background": p["tab_inactive"] + "ff",
        "tab.active_background": mix(p["editor"], accent, TAB_TINT),
        "search.match_background": p["search_match"],
        "search.active_match_background": p["search_active"],
        "panel.background": p["surface"] + "ff",
        "panel.focused_border": ui,
        "panel.overlay_background": p["surface"] + "ff",
        "panel.overlay_hover": mix(p["surface"], accent, 0.18),
        "pane.focused_border": ui,
        # --- scrollbar & minimap ---
        "scrollbar.thumb.background": alpha(ui, "59"),
        "scrollbar.thumb.hover_background": alpha(ui, "8c"),
        "scrollbar.thumb.border": alpha(ui, "40"),
        "scrollbar.track.background": "#00000000",
        "scrollbar.track.border": p["scroll_track_border"],
        "minimap.thumb.background": alpha(ui, "40"),
        "minimap.thumb.hover_background": alpha(ui, "66"),
        "minimap.thumb.border": p["minimap_border"],
        # --- editor ---
        "editor.foreground": p["editor_fg"],
        "editor.background": p["editor"] + "ff",
        "editor.gutter.background": p["editor"] + "ff",
        "editor.subheader.background": p["surface"] + "ff",
        "editor.active_line.background": mix(p["editor"], accent, ACTIVE_LINE_TINT),
        "editor.highlighted_line.background": mix(p["editor"], accent, 0.18),
        "editor.line_number": p["line_number"],
        "editor.active_line_number": p["active_line_number"],
        "editor.hover_line_number": p["hover_line_number"],
        "editor.invisible": p["invisible"],
        "editor.wrap_guide": p["wrap_guide"],
        "editor.active_wrap_guide": p["wrap_guide_active"],
        "editor.indent_guide": p["indent_guide"],
        "editor.indent_guide_active": p["indent_guide_active"],
        "editor.document_highlight.read_background": p["highlight_read"],
        "editor.document_highlight.write_background": p["highlight_write"],
        "editor.document_highlight.bracket_background": alpha(on_editor, "40"),
        # --- terminal ---
        "terminal.background": p["editor"] + "ff",
        "link_text.hover": p["accent_ui"],
    }
    style.update(terminal)
    style.update(status)

    palette = [on_editor] + PLAYERS
    style["players"] = [
        {"cursor": c, "background": c, "selection": alpha(c, "3d")} for c in palette
    ]
    style["syntax"] = build_syntax()
    return style


def main():
    themes = []
    for label, accent in FACTIONS:
        for suffix, palette, status, terminal in VARIANTS:
            themes.append(
                {
                    "name": "Cyberpunk - %s%s" % (label, suffix),
                    "appearance": "dark",
                    "style": build_style(accent, palette, status, terminal),
                }
            )

    doc = {
        "$schema": "https://zed.dev/schema/themes/v0.2.0.json",
        "name": "Cyberpunk",
        "author": "Thomas Simmer",
        "isUserGenerated": True,
        "description": "Inspired by Cyberpunk 2077 (Arasaka, Biotechnica, Softsys, NCPD, Kang Tao, Militech, Delamain, Pink neon, Mox), on One Dark and One Dark Pro greys",
        "themes": themes,
    }

    path = os.path.join(os.path.dirname(__file__), "..", "themes", "cyberpunk.json")
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print("wrote %d themes to %s" % (len(themes), os.path.normpath(path)))


if __name__ == "__main__":
    main()
