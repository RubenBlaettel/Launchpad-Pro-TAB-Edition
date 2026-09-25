"""Zentrale Konstanten der Anwendung."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Kachel-Raster
# ---------------------------------------------------------------------------
GRID_MIN = 3
GRID_MAX = 7
GRID_DEFAULT = 4

# ---------------------------------------------------------------------------
# Projektdateien
# ---------------------------------------------------------------------------
PROJECT_FILE_NAME = "projekt.lptab"
PROJECT_FORMAT = "launchpad-pro-tab"
PROJECT_FORMAT_VERSION = 1
AUDIO_DIR = "audio"
EDITED_DIR = "audio/bearbeitet"
COVER_DIR = "cover"
AUTOSAVE_DIR = ".autosave"
CACHE_DIR = ".cache"
EDIT_SESSION_FILE = "bearbeitung.json"
EXPORT_EXCLUDE_DIRS = (AUTOSAVE_DIR, CACHE_DIR)

# Zyklisches Speichern
AUTOSAVE_INTERVAL_MS = 30_000        # Sicherheitsnetz: spätestens alle 30 s
AUTOSAVE_DEBOUNCE_MS = 2_000         # nach einer Änderung: 2 s später speichern
EDIT_AUTOSAVE_INTERVAL_MS = 5_000    # Zwischenstand "Bearbeiten & Schneiden"

# ---------------------------------------------------------------------------
# Dateiformate
# ---------------------------------------------------------------------------
# Formate, die libsndfile (soundfile) direkt und sehr schnell dekodiert.
SNDFILE_EXTENSIONS = frozenset(
    {".wav", ".wave", ".flac", ".ogg", ".oga", ".aif", ".aiff", ".aifc", ".w64", ".au", ".snd", ".caf", ".rf64"}
)
# Alles Weitere wird über FFmpeg (PyAV) dekodiert.
FFMPEG_EXTENSIONS = frozenset(
    {
        ".mp3", ".mp2", ".m4a", ".m4b", ".aac", ".mp4", ".m4v", ".mov", ".wma", ".wmv", ".asf",
        ".opus", ".webm", ".mka", ".mkv", ".ac3", ".eac3", ".dts", ".amr", ".3gp", ".alac",
        ".ape", ".wv", ".tta", ".mpc", ".spx", ".dsf", ".dff", ".ra", ".voc",
    }
)
AUDIO_EXTENSIONS = SNDFILE_EXTENSIONS | FFMPEG_EXTENSIONS
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".ico"})

# ---------------------------------------------------------------------------
# Bearbeiten & Schneiden
# ---------------------------------------------------------------------------
SPEED_MIN = 0.5
SPEED_MAX = 2.0
GAIN_MIN = 0.1       # 10 %
GAIN_MAX = 2.0       # 200 %
MIN_SELECTION_S = 0.05
STEP_SECONDS = 1.0   # "Schritt vor/zurück" (Taste gedrückt halten = Dauerlauf)
RENDER_FADE_MS = 4.0  # Anti-Klick-Blende an Schnittkanten

# ---------------------------------------------------------------------------
# Wiedergabe
# ---------------------------------------------------------------------------
STOP_FADE_MS_DEFAULT = 40.0  # kurzes Ausblenden beim Stoppen (gegen Knackser)
PREVIEW_KEY = "__preview__"

# ---------------------------------------------------------------------------
# Kachel-Farben (Launchpad-typische Neonfarben)
# ---------------------------------------------------------------------------
TILE_COLORS = (
    "#D64DFF",  # Magenta (Standard)
    "#FF4FA3",  # Pink
    "#FF5252",  # Rot
    "#FF8A1F",  # Orange
    "#FFC61A",  # Gelb
    "#C6FF2E",  # Limette
    "#2EE66E",  # Grün
    "#14D9A0",  # Mint
    "#1FD6FF",  # Cyan
    "#3D8BFF",  # Blau
    "#7A5CFF",  # Violett
    "#E6E9F0",  # Weiß
)
TILE_COLOR_DEFAULT = TILE_COLORS[0]
