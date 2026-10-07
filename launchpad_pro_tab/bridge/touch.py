"""Eingabe-Korrektur für Touchmonitore und Stifte."""

from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QInputDevice

log = logging.getLogger(__name__)

_MOUSE_BUTTON_EVENTS = (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
                        QEvent.Type.MouseButtonDblClick)
_TOUCH_OR_PEN = (QInputDevice.DeviceType.TouchScreen, QInputDevice.DeviceType.Stylus,
                 QInputDevice.DeviceType.Airbrush, QInputDevice.DeviceType.Puck)


class SyntheticRightClickFilter(QObject):
    """Verwirft Rechtsklicks, die das System aus Finger oder Stift erzeugt.

    Windows macht aus „Gedrückt halten“ beim Loslassen einen Rechtsklick an der Fingerposition.
    Das Programm wertet langes Drücken selbst aus (Kachel-Menü); der zusätzliche Klick lag
    neben dem gerade geöffneten Menü und schloss es sofort wieder. Echte Rechtsklicks von Maus
    und Touchpad bleiben unberührt.
    """

    def eventFilter(self, obj, event):  # noqa: N802 – Qt-API
        if event.type() in _MOUSE_BUTTON_EVENTS and event.button() == Qt.MouseButton.RightButton:
            if (event.source() != Qt.MouseEventSource.MouseEventNotSynthesized
                    or event.device().type() in _TOUCH_OR_PEN):
                log.debug("Vom System erzeugter Rechtsklick (Touch/Stift) verworfen")
                return True
        return False
