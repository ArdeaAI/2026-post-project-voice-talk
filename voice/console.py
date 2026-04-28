"""Shared Rich Console with the Gruvbox dark palette.

Demos import the `console` singleton from here rather than instantiating their
own. The theme entries match the slide deck's Gruvbox theme so visual identity
is consistent on stage.
"""

from rich.console import Console
from rich.theme import Theme

GRUVBOX_PALETTE: dict[str, str] = {
    "bg0": "#282828",
    "bg1": "#3c3836",
    "bg2": "#504945",
    "fg": "#ebdbb2",
    "fg_muted": "#a89984",
    "gray": "#928374",
    "red": "#fb4934",
    "green": "#b8bb26",
    "yellow": "#fabd2f",
    "blue": "#83a598",
    "purple": "#d3869b",
    "aqua": "#8ec07c",
    "orange": "#fe8019",
}

GRUVBOX_THEME = Theme(
    {
        "info": f"bold {GRUVBOX_PALETTE['blue']}",
        "warning": f"bold {GRUVBOX_PALETTE['yellow']}",
        "error": f"bold {GRUVBOX_PALETTE['red']}",
        "success": f"bold {GRUVBOX_PALETTE['green']}",
        "muted": GRUVBOX_PALETTE["gray"],
        "accent": GRUVBOX_PALETTE["orange"],
        "primary": GRUVBOX_PALETTE["yellow"],
        "secondary": GRUVBOX_PALETTE["green"],
        "panel.border": GRUVBOX_PALETTE["bg2"],
        "panel.title": f"bold {GRUVBOX_PALETTE['orange']}",
        "rule.line": GRUVBOX_PALETTE["bg2"],
        "table.header": f"bold {GRUVBOX_PALETTE['yellow']}",
    }
)

console = Console(theme=GRUVBOX_THEME, highlight=False)
