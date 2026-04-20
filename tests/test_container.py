"""Container smoke tests.

These tests verify the container can be built and starts without crashing.
They require podman to be available on the host.

Run with:
    pytest tests/test_container.py -v -s
"""

import subprocess
import time
import pytest


def _podman(*args: str) -> subprocess.CompletedProcess:
    """Run a podman command and return the result."""
    return subprocess.run(
        ["podman", *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def podman_available() -> bool:
    """Skip all tests in this module if podman is not installed."""
    result = _podman("--version")
    if result.returncode != 0:
        pytest.skip("podman not available on this host")
    return True


@pytest.fixture(scope="module")
def built_image(podman_available, tmp_path_factory) -> str:
    """Build the Council image once for all tests in this module."""
    import pathlib
    repo_root = pathlib.Path(__file__).parent.parent
    result = subprocess.run(
        ["podman", "build", "-t", "council-test:latest", str(repo_root)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Image build failed:\n{result.stdout}\n{result.stderr}"
    )
    return "council-test:latest"


class TestContainerSmoke:
    """Verify the container starts and doesn't crash immediately."""

    def test_container_starts_without_crash(self, built_image: str) -> None:
        """Container should run for at least 5 seconds without a non-zero exit.

        We run in --local mode (no Discord) with a dummy .env so it doesn't
        need real AWS credentials to pass the startup phase.
        """
        result = _podman(
            "run",
            "--rm",
            "--env", "AWS_ACCESS_KEY_ID=test",
            "--env", "AWS_SECRET_ACCESS_KEY=test",
            "--env", "AWS_DEFAULT_REGION=us-east-1",
            # Stop the daemon after 5 seconds via timeout
            "--timeout", "5",
            built_image,
            "--daemon", "--local",
        )
        # exit code 124 = timed out (still running after 5s) — that's a pass.
        # exit code 0 = clean exit — also fine.
        # Anything else (1, 2, …) = crash.
        assert result.returncode in (0, 124), (
            f"Container crashed (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    def test_help_flag_works(self, built_image: str) -> None:
        """The --help flag should exit cleanly with usage text."""
        result = _podman(
            "run", "--rm",
            built_image,
            "--help",
        )
        assert result.returncode == 0, (
            f"--help exited with {result.returncode}:\n{result.stderr}"
        )
        assert "council" in result.stdout.lower() or "usage" in result.stdout.lower()
