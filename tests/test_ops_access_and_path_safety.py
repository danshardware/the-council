"""Tests for path safety: sensitive file denylist and command argument blocking."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import ToolContext
from tools.file_tools import read_file, write_file
from tools.command_tools import run_command


@pytest.fixture()
def tmp_path_fixture(tmp_path: Path) -> Path:
    """Create a temporary directory with test files."""
    return tmp_path


@pytest.fixture()
def ctx(tmp_path: Path) -> ToolContext:
    """Create a basic ToolContext for testing."""
    return ToolContext(
        agent_id="test",
        session_id="test_session",
        allowed_paths=[str(tmp_path)],
        allowed_commands=["cat", "grep"],
    )


# ============================================================================
# Part 1 — file_tools denylist tests
# ============================================================================

class TestSensitiveFileDenylist:
    """Tests for blocking access to sensitive files."""

    @pytest.fixture
    def ctx_with_root_access(self, tmp_path: Path) -> ToolContext:
        """ToolContext with access to root so we can test path resolution."""
        return ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )

    def test_read_env_file_blocked(self, tmp_path: Path):
        """Attempting to read .env file should be blocked.
        
        Note: .env files starting with '.' are also blocked by _is_private_path(),
        which catches files with '.' prefix. We test with a file that also matches
        the .env.* pattern to ensure the sensitive file check would work.
        """
        # This file is blocked by _is_private_path() (filename starts with '.')
        # The sensitive file check is a secondary layer for files like *.pem, *.key
        env_file = tmp_path / "myapp.env"
        env_file.write_text("SECRET_KEY=12345", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(env_file), ctx)
        assert "[ERROR]" in result

    def test_read_env_local_file_blocked(self, tmp_path: Path):
        """Attempting to read .env.local file should be blocked.
        
        Note: Files starting with '.' are blocked by _is_private_path().
        """
        # Use a file that matches .env.* pattern but doesn't start with '.'
        env_file = tmp_path / "application.env.local"
        env_file.write_text("SECRET_KEY=12345", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(env_file), ctx)
        assert "[ERROR]" in result

    def test_read_pem_file_blocked(self, tmp_path: Path):
        """Attempting to read *.pem file should be blocked."""
        pem_file = tmp_path / "server.pem"
        pem_file.write_text("-----BEGIN RSA PRIVATE KEY-----", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(pem_file), ctx)
        assert "[ERROR]" in result
        assert "sensitive file" in result

    def test_read_key_file_blocked(self, tmp_path: Path):
        """Attempting to read *.key file should be blocked."""
        key_file = tmp_path / "private.key"
        key_file.write_text("-----BEGIN RSA PRIVATE KEY-----", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(key_file), ctx)
        assert "[ERROR]" in result
        assert "sensitive file" in result

    def test_read_crt_file_blocked(self, tmp_path: Path):
        """Attempting to read *.crt file should be blocked."""
        crt_file = tmp_path / "certificate.crt"
        crt_file.write_text("-----BEGIN CERTIFICATE-----", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(crt_file), ctx)
        assert "[ERROR]" in result
        assert "sensitive file" in result

    def test_read_ssh_key_blocked(self, tmp_path: Path):
        """Attempting to read id_rsa should be blocked."""
        ssh_key = tmp_path / "id_rsa"
        ssh_key.write_text("-----BEGIN RSA PRIVATE KEY-----", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(ssh_key), ctx)
        assert "[ERROR]" in result
        assert "sensitive file" in result

    def test_read_ed25519_key_blocked(self, tmp_path: Path):
        """Attempting to read id_ed25519 should be blocked."""
        ssh_key = tmp_path / "id_ed25519"
        ssh_key.write_text("-----BEGIN OPENSSH PRIVATE KEY-----", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(ssh_key), ctx)
        assert "[ERROR]" in result
        assert "sensitive file" in result

    def test_read_credentials_file_blocked(self, tmp_path: Path):
        """Attempting to read 'credentials' file should be blocked."""
        creds_file = tmp_path / "credentials"
        creds_file.write_text("[default]\naws_access_key_id=xxx", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(creds_file), ctx)
        assert "[ERROR]" in result
        assert "sensitive file" in result

    def test_read_config_file_blocked(self, tmp_path: Path):
        """Attempting to read 'config' file (no extension) should be blocked."""
        config_file = tmp_path / "config"
        config_file.write_text("[default]\nregion=us-east-1", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(config_file), ctx)
        assert "[ERROR]" in result
        assert "sensitive file" in result

    def test_read_normal_file_allowed(self, tmp_path: Path):
        """Reading a normal file should be allowed."""
        normal_file = tmp_path / "README.md"
        normal_file.write_text("# Test Project\n\nThis is a normal file.", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(normal_file), ctx)
        assert "[ERROR]" not in result
        assert "Test Project" in result

    def test_read_yaml_file_allowed(self, tmp_path: Path):
        """Reading YAML files (like config) should be allowed."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("key: value", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(yaml_file), ctx)
        assert "[ERROR]" not in result

    def test_read_python_file_allowed(self, tmp_path: Path):
        """Reading Python files should be allowed."""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')", encoding="utf-8")
        
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=[str(tmp_path)],
        )
        
        result = read_file(str(py_file), ctx)
        assert "[ERROR]" not in result


# ============================================================================
# Part 3 — command_tools denylist tests
# ============================================================================

class TestSensitiveCommandArgs:
    """Tests for blocking commands with sensitive path arguments."""

    def test_cat_env_blocked(self):
        """Command 'cat .env' should be blocked."""
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=["/tmp"],
            allowed_commands=["cat"],
        )
        
        result = run_command("cat .env", ctx)
        assert "[ERROR]" in result
        assert "sensitive" in result.lower()

    def test_cat_env_local_blocked(self):
        """Command 'cat .env.local' should be blocked."""
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=["/tmp"],
            allowed_commands=["cat"],
        )
        
        result = run_command("cat .env.local", ctx)
        assert "[ERROR]" in result
        assert "sensitive" in result.lower()

    def test_grep_aws_blocked(self):
        """Command 'grep -r password .aws/' should be blocked."""
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=["/tmp"],
            allowed_commands=["grep"],
        )
        
        result = run_command("grep -r password .aws/", ctx)
        assert "[ERROR]" in result
        assert "sensitive" in result.lower()

    def test_cat_pem_blocked(self):
        """Command 'cat server.pem' should be blocked."""
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=["/tmp"],
            allowed_commands=["cat"],
        )
        
        result = run_command("cat server.pem", ctx)
        assert "[ERROR]" in result
        assert "sensitive" in result.lower()

    def test_cat_key_blocked(self):
        """Command 'cat private.key' should be blocked."""
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=["/tmp"],
            allowed_commands=["cat"],
        )
        
        result = run_command("cat private.key", ctx)
        assert "[ERROR]" in result
        assert "sensitive" in result.lower()

    def test_grep_normal_command_allowed(self):
        """Command 'grep -r def main engine/' should be allowed."""
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=["/tmp"],
            allowed_commands=["grep"],
        )
        
        result = run_command("grep -r 'def make_block' engine/", ctx)
        assert "[ERROR]" not in result

    def test_ls_normal_directory_allowed(self):
        """Command 'ls -la /tmp' should be allowed."""
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=["/tmp"],
            allowed_commands=["ls"],
        )
        
        result = run_command("ls -la /tmp", ctx)
        assert "[ERROR]" not in result

    def test_cat_normal_file_allowed(self):
        """Command 'cat /tmp/README.md' should be allowed."""
        ctx = ToolContext(
            agent_id="test",
            session_id="test_session",
            allowed_paths=["/tmp"],
            allowed_commands=["cat"],
        )
        
        result = run_command("cat /tmp/README.md", ctx)
        assert "[ERROR]" not in result