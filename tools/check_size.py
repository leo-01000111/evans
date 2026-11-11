"""
Fail if a built file or folder is over its size budget (MB, 1 MB = 10**6 bytes).

    python tools/check_size.py dist/Evans 395
    python tools/check_size.py dist/Evans-0.25.0-macos-arm64.dmg 126

Budgets are the size of the 0.24.0 release plus 15%, so a dependency that
quietly doubles the download fails CI. Raise a budget on purpose, in
.github/workflows/ci.yml, when growth is intended.
"""

import sys
from pathlib import Path


def size_mb(path: Path) -> float:
    if path.is_file():
        return path.stat().st_size / 1e6
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    path, budget = Path(argv[1]), float(argv[2])
    if not path.exists():
        print(f"{path} does not exist")
        return 2
    size = size_mb(path)
    print(f"{path}: {size:.1f} MB (budget {budget:.0f} MB)")
    if size > budget:
        print("over budget")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
