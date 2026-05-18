import os
import subprocess
import time

import pytest

_integration = pytest.mark.skipif(
    os.getenv("QUILL_INTEGRATION") != "1",
    reason="requires QUILL_INTEGRATION=1",
)


@_integration
def test_quickstart_starts_daemons():
    subprocess.run(
        ["bash", "scripts/calliope_quickstart.sh"],
        timeout=30,
        check=True,
    )
    time.sleep(10)
    result = subprocess.run(
        ["curl", "-sf", "http://localhost:5000/health"],
        timeout=5,
    )
    assert result.returncode == 0


@_integration
def test_stop_kills_daemons():
    subprocess.run(
        ["bash", "scripts/calliope_quickstart.sh"],
        timeout=30,
        check=True,
    )
    time.sleep(10)
    subprocess.run(
        ["bash", "scripts/stop_all_calliope_daemons.sh"],
        timeout=15,
        check=True,
    )
    time.sleep(3)
    result = subprocess.run(
        ["curl", "-sf", "http://localhost:5000/health"],
        timeout=3,
    )
    assert result.returncode != 0
