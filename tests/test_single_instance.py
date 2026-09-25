"""Nur eine Instanz: ein zweiter Programmstart übergibt seinen Auftrag an die laufende."""

from __future__ import annotations

import subprocess
import sys
import textwrap
import uuid

from conftest import ROOT, wait_until


def _second_start(name: str, payload: dict) -> subprocess.Popen:
    """Zweiter Programmstart als eigener Prozess (wie im echten Betrieb)."""
    code = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(ROOT)!r})
        from PySide6.QtCore import QCoreApplication
        from launchpad_pro_tab.bridge.single_instance import SingleInstance
        app = QCoreApplication(sys.argv)
        print("weitergeleitet" if SingleInstance({name!r}).forward({payload!r}) else "keine-instanz")
    """)
    return subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)


def test_second_start_is_forwarded(qapp):
    from launchpad_pro_tab.bridge.single_instance import SingleInstance

    name = f"LaunchpadProTAB-test-{uuid.uuid4().hex[:8]}"
    first = SingleInstance(name)
    received = []
    first.messageReceived.connect(received.append)
    try:
        proc = _second_start(name, {"action": "activate"})           # noch niemand da
        assert wait_until(qapp, lambda: proc.poll() is not None, 30)
        assert proc.stdout.read().strip() == "keine-instanz"

        assert first.listen()
        proc = _second_start(name, {"action": "activate", "project": "/tmp/Show"})
        assert wait_until(qapp, lambda: proc.poll() is not None and received, 30)
        assert proc.stdout.read().strip() == "weitergeleitet"
        assert received == [{"action": "activate", "project": "/tmp/Show"}]
    finally:
        first.close()

    proc = _second_start(name, {"action": "activate"})               # wieder frei
    assert wait_until(qapp, lambda: proc.poll() is not None, 30)
    assert proc.stdout.read().strip() == "keine-instanz"


def test_windows_integration_is_harmless_elsewhere():
    from launchpad_pro_tab.system import integration

    integration.create_instance_mutex()
    integration.set_app_user_model_id()
