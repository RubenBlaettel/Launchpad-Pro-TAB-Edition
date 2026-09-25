"""Nur eine Instanz: ein zweiter Programmstart übergibt seinen Auftrag an die laufende."""

from __future__ import annotations

import uuid

from conftest import wait_until


def test_second_start_is_forwarded(qapp):
    from launchpad_pro_tab.bridge.single_instance import SingleInstance

    name = f"LaunchpadProTAB-test-{uuid.uuid4().hex[:8]}"
    first = SingleInstance(name)
    received = []
    first.messageReceived.connect(received.append)
    try:
        assert not SingleInstance(name).forward({"action": "activate"})   # noch niemand da
        assert first.listen()
        assert SingleInstance(name).forward({"action": "activate", "project": "/tmp/Show"})
        assert wait_until(qapp, lambda: len(received) == 1, 5)
        assert received[0] == {"action": "activate", "project": "/tmp/Show"}
    finally:
        first.close()
    assert not SingleInstance(name).forward({"action": "activate"})       # wieder frei


def test_windows_integration_is_harmless_elsewhere():
    from launchpad_pro_tab.system import integration

    integration.create_instance_mutex()
    integration.set_app_user_model_id()
