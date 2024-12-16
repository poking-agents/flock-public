from pathlib import Path

import pytest

from handlers.bash import bash_hooks
from type_defs.operations import BashParams


@pytest.fixture
def test_env(monkeypatch, tmp_path):
    """Setup a controlled environment for the test for storing environment data."""
    # Setting a test environment variable that the code references for environment directories
    monkeypatch.setenv("TEST_ENVIRONMENT", str(tmp_path))
    # Ensure the test environment directory is clean
    yield
    # Cleanup doesn't do anything: `tmp_path` fixture does automatically


@pytest.mark.asyncio
async def test_bash_hooks_simple_command(test_env):
    params = BashParams(command='echo "Hello, world!"')
    dependencies = {"hooks_client": None}

    output = await bash_hooks(params, dependencies)

    assert output.status == 0
    assert "Hello, world!" in output.stdout
    assert output.stderr == ""


@pytest.mark.asyncio
async def test_bash_hooks_failing_command(test_env):
    params = BashParams(command="ls non_existent_file")
    dependencies = {"hooks_client": None}

    output = await bash_hooks(params, dependencies)

    assert output.status != 0
    assert output.stdout == ""
    # On a typical system: `ls: cannot access 'non_existent_file': No such file or directory`
    # We confirm some part of a "no such file" message
    assert "No such file" in output.stderr or "cannot access" in output.stderr.lower()


@pytest.mark.asyncio
async def test_bash_hooks_with_timeout(test_env):
    params = BashParams(command="sleep 2", timeout=1)
    dependencies = {"hooks_client": None}

    output = await bash_hooks(params, dependencies)

    # In this updated code, a timed out command sets the status to 124 and `stderr` to a specific string
    assert output.status == 124
    assert "timed out after 1 seconds" in output.stderr


@pytest.mark.asyncio
async def test_bash_hooks_subagent_execution(test_env):
    agent_id = "agent_1"
    params = BashParams(command='echo "Hello from subagent!"', agent_id=agent_id)
    dependencies = {"hooks_client": None}

    output = await bash_hooks(params, dependencies)

    assert output.status == 0
    assert "Hello from subagent!" in output.stdout
    assert output.stderr == ""
    # Check that the environment directories for the subagent have been created
    assert (Path("subagents") / agent_id / ".cache").exists()
