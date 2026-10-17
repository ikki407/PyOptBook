import sys
from importlib.metadata import version
from pathlib import Path

import pulp


def test_readme_environment_and_cbc():
    readme = (Path(__file__).resolve().parents[1] / 'README.md').read_text(encoding='utf-8')
    for line in readme.splitlines():
        if not line.startswith('| '):
            continue
        _, _, package, expected, _ = (part.strip() for part in line.split('|'))
        if package == 'Python3':
            assert '.'.join(map(str, sys.version_info[:2])) == expected
        elif expected[:1].isdigit():
            assert version(package) == expected, package
    assert version('pulp') == '3.2.2'
    assert pulp.PULP_CBC_CMD().available()
