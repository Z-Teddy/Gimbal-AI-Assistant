import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.voice.asr_runner import decode_wav

if len(sys.argv) < 2:
    print("Usage: python scripts/decode_wav.py /path/to/file.wav")
    sys.exit(1)

wav = Path(sys.argv[1])
print(decode_wav(str(wav)))
