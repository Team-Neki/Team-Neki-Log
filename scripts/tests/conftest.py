import sys
from pathlib import Path

# scripts/ 를 import 경로에 추가 (producer 모듈은 단일 디렉토리에 위치).
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
