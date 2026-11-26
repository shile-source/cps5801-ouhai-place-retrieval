"""Create only the checkout-local parent for the configured pytest temporary tree."""
from pathlib import Path


def pytest_configure(config):
    if config.getoption('basetemp')=='.cache/tmp/pytest':
        (Path(config.rootpath)/'.cache/tmp').mkdir(parents=True,exist_ok=True)
