"""Exercise asynchronous page interactions with the existing Node runtime."""
from pathlib import Path
import shutil
import subprocess
import pytest


@pytest.mark.parametrize('script', ['demo_ui_checks.js', 'annotation_ui_checks.js','adjudication_ui_checks.js'])
def test_demo_interaction_regressions(script):
    node = shutil.which('node')
    if not node:
        pytest.skip('Existing Node runtime is unavailable; no dependency is installed')
    result = subprocess.run([node, str(Path(__file__).with_name(script))],
                            capture_output=True, text=True, encoding='utf-8', timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
