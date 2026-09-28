"""元のノートブックを PuLP 3.3.2 で実行して比較基準を保存する。"""
import json
import platform
import sys

import pulp

from notebook_support import BASELINE, CASES, SOURCE_COMMIT, run_case


if __name__ == '__main__':
    assert pulp.__version__ == '3.3.2'
    data = json.loads(BASELINE.read_text()) if BASELINE.exists() else {
        'source_commit': SOURCE_COMMIT, 'pulp': pulp.__version__,
        'python': platform.python_version(), 'solver': 'CBC 2.10.3', 'cases': {}}
    for case in sys.argv[1:] or CASES:
        print(case, flush=True)
        data['cases'][case] = run_case(case, original=True)
        BASELINE.write_text(json.dumps(data, indent=2) + '\n')
        print(f"  {len(data['cases'][case])} solves", flush=True)
