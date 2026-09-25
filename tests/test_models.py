import pytest

from launchpad_pro_tab.core.constants import GRID_MAX, GRID_MIN, TILE_COLOR_DEFAULT
from launchpad_pro_tab.core.models import EditParams, ProjectData, TileData, clamp_grid
from launchpad_pro_tab.core.util import format_time, safe_filename


def test_edit_params_normalize_and_identity():
    p = EditParams(start=-3, end=99, speed=5, gain=0.01).normalized(10.0)
    assert p.start == 0.0 and p.end == 10.0
    assert p.speed == 2.0 and p.gain == pytest.approx(0.1)
    assert EditParams().is_identity(10.0)
    assert not EditParams(start=1.0).is_identity(10.0)
    assert not EditParams(speed=1.2).is_identity(10.0)
    assert not EditParams(gain=0.5).is_identity(10.0)
    # ungültige Auswahl -> ganze Datei
    q = EditParams(start=8, end=2).normalized(10.0)
    assert (q.start, q.end) == (0.0, 10.0)


def test_edit_params_roundtrip():
    p = EditParams(start=1.5, end=4.25, speed=1.25, gain=1.8)
    assert EditParams.from_dict(p.to_dict()) == p
    assert EditParams.from_dict(None) is None


def test_tile_roundtrip_and_flags():
    t = TileData(row=1, col=2, title="Donner", color="#FF5252", audio="audio/a_edit.flac",
                 original="audio/a.wav", cover="cover/x.png", loop=True,
                 edit=EditParams(0.5, 3.0, 1.1, 1.2), duration=2.3, source_name="a.wav")
    again = TileData.from_dict(t.to_dict())
    assert again == t
    assert t.is_edited and not t.is_empty and t.has_content
    assert TileData(0, 0).is_empty and not TileData(0, 0).has_content
    assert TileData(0, 0, source_name="Walzer.flac").display_title == "Walzer"
    t.clear()
    assert t.is_empty and t.color == TILE_COLOR_DEFAULT and t.edit is None


def test_project_resize_discards_outside_tiles():
    p = ProjectData(name="Test", grid=5)
    p.tile(0, 0).audio = "audio/a.wav"
    p.tile(4, 1).audio = "audio/b.wav"      # fällt bei 4×4 weg
    p.tile(2, 4).color = "#FFFFFF"          # nur Farbe -> zählt als Inhalt
    p.tile(3, 3)                            # leer -> kein Datenverlust
    assert {(t.row, t.col) for t in p.tiles_outside(4)} == {(4, 1), (2, 4)}
    removed = p.resize(4)
    assert {(t.row, t.col) for t in removed} == {(4, 1), (2, 4)}
    assert p.grid == 4
    assert (4, 1) not in p.tiles and (0, 0) in p.tiles
    # Vergrößern verliert nichts
    assert p.resize(7) == [] and p.grid == 7


def test_project_serialization_only_keeps_content():
    p = ProjectData(name="Stück", grid=3)
    p.tile(0, 0).audio = "audio/a.wav"
    p.tile(1, 1)  # leer
    data = p.to_dict()
    assert len(data["tiles"]) == 1
    q = ProjectData.from_dict(data)
    assert q.grid == 3 and q.peek(0, 0).audio == "audio/a.wav"


def test_project_rejects_foreign_or_newer_files():
    with pytest.raises(ValueError):
        ProjectData.from_dict({"format": "etwas-anderes"})
    with pytest.raises(ValueError):
        ProjectData.from_dict({"format": "launchpad-pro-tab", "version": 999})


def test_clamp_grid():
    assert clamp_grid(1) == GRID_MIN and clamp_grid(99) == GRID_MAX and clamp_grid(5) == 5


def test_format_time_and_safe_filename():
    assert format_time(7.4) == "0:07"
    assert format_time(205) == "3:25"
    assert format_time(3723) == "1:02:03"
    assert format_time(7.44, with_tenths=True) == "0:07,4"
    assert format_time(-12) == "-0:12"
    assert safe_filename('Akt 1: "Sturm"/Nacht?') == "Akt 1_ _Sturm__Nacht_"
    assert safe_filename("CON") == "_CON"
    assert safe_filename("   ") == "Projekt"
