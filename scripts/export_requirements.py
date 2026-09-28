"""uv.lock から pip 用の依存ファイルを生成・検査する。"""
import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = {
    'requirements.txt': ['--no-dev'],
    '6.api/requirements.txt': ['--no-default-groups', '--group', 'api'],
    'requirements-test.txt': [],
    'requirements-alternatives.txt': ['--no-dev', '--group', 'alternatives'],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale = []
    for name, groups in EXPORTS.items():
        result = subprocess.run(
            ['uv', 'export', '--locked', '--no-hashes', '--no-emit-project',
             '--no-header', '--no-annotate', *groups],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        content = '# Generated from uv.lock: python scripts/export_requirements.py\n' + result.stdout
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                stale.append(name)
        else:
            path.write_text(content)
    if stale:
        print('Regenerate requirements: ' + ', '.join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
