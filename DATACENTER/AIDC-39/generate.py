from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from common.data import generate
if __name__ == '__main__':
    generate()
    from refresh_metadata import refresh
    refresh(rebuild_catalog=True)
    print('Generated exactly three independent AIDC-39 cases.')
