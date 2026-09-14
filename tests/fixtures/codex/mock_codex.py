"""A process-level Codex stand-in; never contacts a model."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

args = sys.argv[1:]
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')
prompt = sys.stdin.read()
final = Path(args[args.index('--output-last-message') + 1])
case = os.environ.get('GX_CODEX_MOCK_CASE', 'success')
if case == 'child':
    subprocess.Popen([sys.executable, '-c',
        "import time; time.sleep(2); open('child-survived', 'w').write('bad')"])
    time.sleep(10)
if case != 'empty':
    final.write_text('<ralph>BLOCKED: fixture</ralph>\n' if case == 'blocked'
                     else '검증 완료\n', encoding='utf-8')
if case == 'failure':
    raise SystemExit(9)
print(json.dumps({'type': 'probe', 'args': args, 'prompt': prompt,
                  'text': '<ralph>COMPLETE</ralph>'}, ensure_ascii=False))
print('mock diagnostic', file=sys.stderr)
