from importlib.metadata import version

import arbiter


def test_installed_version_matches_package() -> None:
    assert arbiter.__version__ == version("arbiter")
