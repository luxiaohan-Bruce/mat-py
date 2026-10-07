from pathlib import Path
import sys
CASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CASE.parent))
from common.runner import main
if __name__ == "__main__":
    raise SystemExit(main(CASE))
