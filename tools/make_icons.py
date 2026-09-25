"""Erzeugt das SVG-Icon-Set unter launchpad_pro_tab/qml/icons/.

Alle Icons sind weiß (24×24, runde Linienenden) und werden in QML per ``IconImage``
eingefärbt. Neue Icons einfach unten ergänzen und das Skript erneut ausführen:

    python tools/make_icons.py
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "launchpad_pro_tab" / "qml" / "icons"

S = 'fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
F = 'fill="#FFFFFF" stroke="#FFFFFF" stroke-width="1.4" stroke-linejoin="round"'

ICONS: dict[str, str] = {
    "play": f'<path d="M7.5 4.8v14.4a.9.9 0 0 0 1.37.77l11.2-7.2a.9.9 0 0 0 0-1.54L8.87 4.03A.9.9 0 0 0 7.5 4.8z" {F}/>',
    "pause": '<rect x="6" y="4.5" width="4.2" height="15" rx="1.2" fill="#FFFFFF"/>'
             '<rect x="13.8" y="4.5" width="4.2" height="15" rx="1.2" fill="#FFFFFF"/>',
    "stop": '<rect x="5.5" y="5.5" width="13" height="13" rx="2.2" fill="#FFFFFF"/>',
    "to-start": '<rect x="4.5" y="5" width="2.8" height="14" rx="1.1" fill="#FFFFFF"/>'
                f'<path d="M19.5 6.1v11.8a.8.8 0 0 1-1.25.66L9.6 12.66a.8.8 0 0 1 0-1.32l8.65-5.9a.8.8 0 0 1 1.25.66z" {F}/>',
    "step-back": f'<path d="M11.5 6.6v10.8a.7.7 0 0 1-1.1.57L3.4 12.57a.7.7 0 0 1 0-1.14l7-5.4a.7.7 0 0 1 1.1.57z" {F}/>'
                 f'<path d="M20.5 6.6v10.8a.7.7 0 0 1-1.1.57l-7-5.4a.7.7 0 0 1 0-1.14l7-5.4a.7.7 0 0 1 1.1.57z" {F}/>',
    "step-forward": f'<path d="M12.5 6.6v10.8a.7.7 0 0 0 1.1.57l7-5.4a.7.7 0 0 0 0-1.14l-7-5.4a.7.7 0 0 0-1.1.57z" {F}/>'
                    f'<path d="M3.5 6.6v10.8a.7.7 0 0 0 1.1.57l7-5.4a.7.7 0 0 0 0-1.14l-7-5.4a.7.7 0 0 0-1.1.57z" {F}/>',
    "reset": f'<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3" {S}/><path d="M4.5 4.2v4.3h4.3" {S}/>',
    "save": f'<path d="M5 3.5h11l4.5 4.5v11a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 19V5A1.5 1.5 0 0 1 5 3.5z" {S}/>'
            f'<path d="M8 3.5v5h7.5v-5" {S}/><path d="M7.5 20.5v-6.5h9v6.5" {S}/>',
    "save-as": f'<path d="M13 20.5H5A1.5 1.5 0 0 1 3.5 19V5A1.5 1.5 0 0 1 5 3.5h11l4.5 4.5v4" {S}/>'
               f'<path d="M8 3.5v5h7.5v-5" {S}/><path d="M7.5 20.5v-6.5h4" {S}/>'
               f'<path d="M18.5 14.5v7M15 18h7" {S}/>',
    "folder": f'<path d="M3 7A1.5 1.5 0 0 1 4.5 5.5H9l2 2.2h8.5A1.5 1.5 0 0 1 21 9.2v9.3a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z" {S}/>',
    "new": f'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" {S}/>'
           f'<path d="M14 3v5h5M12 11.5v6M9 14.5h6" {S}/>',
    "export": f'<path d="M12 14.5V3.5M7.5 8L12 3.5 16.5 8" {S}/><path d="M4.5 13v5.5A2 2 0 0 0 6.5 20.5h11a2 2 0 0 0 2-2V13" {S}/>',
    "plus": '<path d="M12 5v14M5 12h14" fill="none" stroke="#FFFFFF" stroke-width="2.3" stroke-linecap="round"/>',
    "close": '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11" fill="none" stroke="#FFFFFF" stroke-width="2.3" stroke-linecap="round"/>',
    "trash": f'<path d="M4 7h16M9.5 7V4.5h5V7" {S}/><path d="M6.5 7l.9 12.6A1.5 1.5 0 0 0 8.9 21h6.2a1.5 1.5 0 0 0 1.5-1.4L17.5 7" {S}/>'
             f'<path d="M10 11v6M14 11v6" {S}/>',
    "scissors": f'<circle cx="6" cy="6.5" r="2.7" {S}/><circle cx="6" cy="17.5" r="2.7" {S}/>'
                f'<path d="M8.3 8l11.2 10M8.3 16L19.5 6" {S}/>',
    "pencil": f'<path d="M4 20h4.2L19.3 8.9a2.1 2.1 0 0 0 0-3L18.1 4.7a2.1 2.1 0 0 0-3 0L4 15.8z" {S}/><path d="M13.5 6.3l4.2 4.2" {S}/>',
    "image": f'<rect x="3" y="4" width="18" height="16" rx="2.2" {S}/><circle cx="8.5" cy="9.5" r="1.8" {S}/>'
             f'<path d="M21 15.5l-5-5L5.5 20" {S}/>',
    "music": f'<path d="M9 18V5.5l11-2V16" {S}/><circle cx="6.5" cy="18" r="2.5" {S}/><circle cx="17.5" cy="16" r="2.5" {S}/>',
    "loop": f'<path d="M17 2.5l3 3-3 3" {S}/><path d="M4 11.5v-1a5 5 0 0 1 5-5h11" {S}/>'
            f'<path d="M7 21.5l-3-3 3-3" {S}/><path d="M20 12.5v1a5 5 0 0 1-5 5H4" {S}/>',
    "lock": f'<rect x="5" y="10.5" width="14" height="10.5" rx="2.2" {S}/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" {S}/>'
            '<circle cx="12" cy="15.7" r="1.4" fill="#FFFFFF"/>',
    "unlock": f'<rect x="5" y="10.5" width="14" height="10.5" rx="2.2" {S}/><path d="M8 10.5V7.5a4 4 0 0 1 7.7-1.6" {S}/>',
    "settings": f'<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1" {S}/>'
                f'<circle cx="15" cy="6" r="2" {S}/><circle cx="9" cy="12" r="2" {S}/><circle cx="17" cy="18" r="2" {S}/>',
    "zoom-in": f'<circle cx="10.5" cy="10.5" r="6.5" {S}/><path d="M20 20l-4.6-4.6M10.5 7.5v6M7.5 10.5h6" {S}/>',
    "zoom-out": f'<circle cx="10.5" cy="10.5" r="6.5" {S}/><path d="M20 20l-4.6-4.6M7.5 10.5h6" {S}/>',
    "fit": f'<path d="M3.5 12h17M7 8.5L3.5 12 7 15.5M17 8.5l3.5 3.5-3.5 3.5" {S}/><path d="M3.5 4v2.5M20.5 4v2.5M3.5 17.5V20M20.5 17.5V20" {S}/>',
    "mark-start": f'<path d="M9.5 4H5.5v16h4" {S}/><path d="M12.5 12H20M16.5 8.5L20 12l-3.5 3.5" {S}/>',
    "mark-end": f'<path d="M14.5 4h4v16h-4" {S}/><path d="M11.5 12H4M7.5 8.5L4 12l3.5 3.5" {S}/>',
    "volume": '<path d="M4 9.3h3.4L12 5.4v13.2l-4.6-3.9H4z" fill="#FFFFFF" stroke="#FFFFFF" stroke-width="1.2" stroke-linejoin="round"/>'
              f'<path d="M15.5 9a4.2 4.2 0 0 1 0 6M18.2 6.3a8 8 0 0 1 0 11.4" {S}/>',
    "volume-mute": '<path d="M4 9.3h3.4L12 5.4v13.2l-4.6-3.9H4z" fill="#FFFFFF" stroke="#FFFFFF" stroke-width="1.2" stroke-linejoin="round"/>'
                   f'<path d="M16 9.5l5 5M21 9.5l-5 5" {S}/>',
    "warning": f'<path d="M10.3 4.1L2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 4.1a2 2 0 0 0-3.4 0z" {S}/>'
               f'<path d="M12 9.5v4.5" {S}/><circle cx="12" cy="17.1" r="1.2" fill="#FFFFFF"/>',
    "chevron-down": f'<path d="M6 9.5l6 6 6-6" {S}/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
    "info": f'<circle cx="12" cy="12" r="9" {S}/><path d="M12 11v6" {S}/><circle cx="12" cy="7.8" r="1.2" fill="#FFFFFF"/>',
    "grip": "".join(f'<circle cx="{x}" cy="{y}" r="1.6" fill="#FFFFFF"/>' for x in (9, 15) for y in (6, 12, 18)),
    "search": f'<circle cx="10.5" cy="10.5" r="6.5" {S}/><path d="M20 20l-4.6-4.6" {S}/>',
    "grid": "".join(f'<rect x="{x}" y="{y}" width="6.5" height="6.5" rx="1.6" {S}/>' for x in (4, 13.5) for y in (4, 13.5)),
    "undo": f'<path d="M9 14L4 9l5-5" {S}/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" {S}/>',
    "headphones": f'<path d="M4 17v-4a8 8 0 0 1 16 0v4" {S}/><rect x="3.5" y="14" width="4" height="6.5" rx="1.5" {S}/>'
                  f'<rect x="16.5" y="14" width="4" height="6.5" rx="1.5" {S}/>',
    "speed": f'<path d="M5.6 18.5a8.5 8.5 0 1 1 12.8 0" {S}/><path d="M12 13.5l4-5" {S}/><circle cx="12" cy="13.5" r="1.4" fill="#FFFFFF"/>',
    "drop": f'<path d="M12 3.5v11M7.5 10L12 14.5 16.5 10" {S}/><path d="M4.5 16v2.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V16" {S}/>',
    "masks": f'<path d="M3.5 4.5c3 1.3 6.5 1.3 9.5 0v6.3a4.75 4.75 0 0 1-9.5 0z" {S}/>'
             f'<path d="M13.5 9.2c2.3.9 4.7.9 7 0v5.1a4.6 4.6 0 0 1-8.2 2.9" {S}/>'
             f'<path d="M6 9h1.2M9.4 9h1.2M6.8 12.5c.9.8 2.1.8 3 0" {S}/><path d="M15.4 13.2h1M18.4 13.2h1M16.2 16.3c.7-.6 1.9-.6 2.6 0" {S}/>',
    # Darstellung
    "sun": f'<circle cx="12" cy="12" r="4.2" {S}/>'
           f'<path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.55 1.55M17.15 17.15l1.55 1.55'
           f'M5.3 18.7l1.55-1.55M17.15 6.85l1.55-1.55" {S}/>',
    "moon": f'<path d="M20 14.6A8.5 8.5 0 0 1 9.4 4a8.5 8.5 0 1 0 10.6 10.6z" {S}/>',
    "monitor": f'<rect x="3" y="4" width="18" height="12.5" rx="2" {S}/><path d="M8.5 20.5h7M12 16.5v4" {S}/>',
    # Updates
    "download": f'<path d="M12 3.5v11M7.5 10L12 14.5 16.5 10" {S}/><path d="M4.5 15.5v3a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3" {S}/>',
    "refresh": f'<path d="M20 11.5A8 8 0 0 0 5.6 7.2" {S}/><path d="M5 3.8v3.9h3.9" {S}/>'
               f'<path d="M4 12.5a8 8 0 0 0 14.4 4.3" {S}/><path d="M19 20.2v-3.9h-3.9" {S}/>',
    "external": f'<path d="M14 4h6v6M20 4l-8.5 8.5" {S}/><path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10" {S}/>',
    "sparkle": f'<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" {F}/>'
               f'<path d="M18.5 15.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z" {F}/>',
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in ICONS.items():
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">{body}</svg>\n'
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    print(f"{len(ICONS)} Icons geschrieben nach {OUT}")


if __name__ == "__main__":
    main()
