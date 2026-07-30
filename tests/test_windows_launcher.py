from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_admin_launcher_forwards_configurable_ports() -> None:
    launcher = (ROOT / "scripts" / "dev-admin.ps1").read_text(encoding="utf-8")
    runner = (ROOT / "scripts" / "dev.ps1").read_text(encoding="utf-8")

    assert "[int]$FrontendPort = 7800" in launcher
    assert "[int]$FrontendPort = 7800" in runner
    assert '$env:HOST_API_PORT = "$Port"' in runner
    assert '$env:FRONTEND_ADMIN_PORT = "$FrontendPort"' in runner


def test_admin_compose_uses_launcher_ports() -> None:
    compose = (
        ROOT / "docker" / "frontend" / "compose-admin.yml"
    ).read_text(encoding="utf-8")
    override = (
        ROOT / "docker" / "frontend" / "compose-admin.host-api.yml"
    ).read_text(encoding="utf-8")

    assert "${FRONTEND_ADMIN_PORT:-7800}:7800" in compose
    assert "host.docker.internal:${HOST_API_PORT:-7799}" in override


def test_windows_runner_checks_docker_compose_v2() -> None:
    runner = (ROOT / "scripts" / "dev.ps1").read_text(encoding="utf-8")

    assert "docker compose version" in runner
