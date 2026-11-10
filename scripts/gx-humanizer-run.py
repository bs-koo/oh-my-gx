#!/usr/bin/env python3
"""윤문 실행을 배타 예약하고 입력·fidelity 라운드를 불변 파일로 보존한다."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def write_once(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


def checked(folder, path):
    if not path.resolve().is_relative_to(folder.resolve()):
        raise ValueError('실행 디렉터리 밖 경로는 사용할 수 없습니다')
    current = path
    while current != folder:
        if current.is_symlink():
            raise ValueError('실행 산출물의 symlink는 사용할 수 없습니다')
        current = current.parent
    return path


def base_path(cwd):
    root = Path(cwd).resolve(strict=True)
    base = root / '.humanize'
    if base.is_symlink() or not base.resolve().is_relative_to(root):
        raise ValueError('.humanize 경로가 프로젝트 밖으로 이어집니다')
    return base


def run_path(cwd, run_id):
    if not isinstance(run_id, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}-\d{3,}', run_id):
        raise ValueError('올바른 run-id가 필요합니다')
    folder = base_path(cwd) / run_id
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('예약된 실행 디렉터리가 없습니다')
    value = json.loads(checked(folder, folder / 'run.json').read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('run_id') != run_id:
        raise ValueError('실행 메타데이터의 run-id가 다릅니다')
    return folder


def reserve(cwd, metadata, today=None):
    if not isinstance(metadata, dict):
        raise ValueError('실행 메타데이터가 필요합니다')
    for key in ('genre', 'tone', 'scope'):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError('확정된 genre/tone/scope가 필요합니다')
    if metadata.get('mode') not in ('audit', 'rewrite', 'strict'):
        raise ValueError('확정된 모드가 필요합니다')
    if not isinstance(metadata.get('sources'), list) or not metadata['sources'] or any(
            not isinstance(source, str) or not source.strip() for source in metadata['sources']):
        raise ValueError('입력 sources 목록이 필요합니다')
    today = today or date.today().isoformat()
    if date.fromisoformat(today).isoformat() != today:
        raise ValueError('날짜는 YYYY-MM-DD여야 합니다')
    base = base_path(cwd)
    base.mkdir(exist_ok=True)
    pattern = re.compile(re.escape(today) + r'-(\d{3,})')
    used = [int(match.group(1)) for child in base.iterdir()
            if (match := pattern.fullmatch(child.name))]
    sequence = max(used, default=0) + 1
    while True:
        run_id = f'{today}-{sequence:03d}'
        folder = base / run_id
        try:
            folder.mkdir()
            break
        except FileExistsError:
            sequence += 1
    # 메타 저장 실패도 예약 디렉터리는 남긴다. 다음 실행이 이 ID를 재사용하지 않는다.
    value = {'schema': 1, 'run_id': run_id, 'metadata': metadata}
    write_once(folder / 'run.json', encoded(value))
    return {'run_id': run_id, 'directory': str(folder), 'metadata': metadata}


def freeze_input(cwd, run_id, raw):
    folder = run_path(cwd, run_id)
    if not isinstance(raw, bytes):
        raise ValueError('원문은 UTF-8 바이트여야 합니다')
    if not raw.decode('utf-8').strip():
        raise ValueError('원문이 비어 있습니다. 원문 없이 윤문 실행을 동결하지 않습니다')
    write_once(folder / '01_input.txt', raw)
    write_once(folder / 'input.json', encoded({'sha256': sha(raw),
               'metadata_sha256': sha((folder / 'run.json').read_bytes())}))
    return {'input_sha256': sha(raw)}


def frozen_input(folder):
    raw = checked(folder, folder / '01_input.txt').read_bytes()
    saved = json.loads(checked(folder, folder / 'input.json').read_text(encoding='utf-8'))
    if sha(raw) != saved['sha256'] or sha((folder / 'run.json').read_bytes()) != saved['metadata_sha256']:
        raise ValueError('동결한 원문 입력이 변경됐습니다')
    return raw


def archive_round(cwd, run_id, round_number, rewrite_sha256):
    folder = run_path(cwd, run_id)
    original = frozen_input(folder)
    if type(round_number) is not int or not 0 <= round_number <= 2:
        raise ValueError('재윤문은 최대 2회이며 최초 라운드는 0입니다')
    rewrite = checked(folder, folder / '03_rewrite.md').read_bytes()
    if sha(rewrite) != rewrite_sha256:
        raise ValueError('검증 요청 이후 윤문본이 변경됐습니다')
    fidelity = checked(folder, folder / '04_fidelity.json').read_bytes()
    report = json.loads(fidelity.decode('utf-8'))
    meta = report['meta']
    if meta.get('run_id') != run_id or meta.get('audit_verdict') not in ('full_pass', 'conditional_pass', 'fail'):
        raise ValueError('현재 run의 fidelity 판정이 필요합니다')
    if meta.get('round') != round_number or meta.get('rewrite_sha256') != rewrite_sha256:
        raise ValueError('fidelity 판정이 현재 윤문본·라운드와 다릅니다')
    safe = meta['audit_verdict'] == 'full_pass'
    if safe and (meta.get('edits_rollback') != 0 or any(
            item.get('action') == 'rollback' for item in report.get('flagged_edits', []))):
        raise ValueError('미해결 rollback이 있는 판정은 안전본이 아닙니다')
    rounds = checked(folder, folder / 'rounds')
    if round_number and not (rounds / f'{round_number - 1:03d}' / 'checkpoint.json').is_file():
        raise ValueError('직전 라운드 기록을 먼저 보존해야 합니다')
    rounds.mkdir(exist_ok=True)
    target = rounds / f'{round_number:03d}'
    target.mkdir()
    write_once(target / '03_rewrite.md', rewrite)
    write_once(target / '04_fidelity.json', fidelity)
    checkpoint = {'schema': 1, 'run_id': run_id, 'round': round_number, 'safe': safe,
                  'input_sha256': sha(original), 'rewrite_sha256': sha(rewrite),
                  'fidelity_sha256': sha(fidelity)}
    # 체크포인트는 마지막에 쓴다. 중단된 부분 복사본을 안전본으로 취급하지 않는다.
    write_once(target / 'checkpoint.json', encoded(checkpoint))
    return checkpoint | {'directory': str(target)}


def select_safe(cwd, run_id, *, require_naturalness=False, round_number=None, rewrite_sha256=None):
    folder = run_path(cwd, run_id)
    original = frozen_input(folder)
    candidates = sorted((folder / 'rounds').glob('*/checkpoint.json'), reverse=True)
    for path in candidates:
        checked(folder, path)
        checkpoint = json.loads(path.read_text(encoding='utf-8'))
        rewrite, fidelity = path.parent / '03_rewrite.md', path.parent / '04_fidelity.json'
        checked(folder, rewrite)
        checked(folder, fidelity)
        if (checkpoint.get('run_id') != run_id or checkpoint.get('input_sha256') != sha(original)
                or checkpoint.get('rewrite_sha256') != sha(rewrite.read_bytes())
                or checkpoint.get('fidelity_sha256') != sha(fidelity.read_bytes())):
            raise ValueError('보존한 fidelity 라운드의 지문이 변경됐습니다')
        if checkpoint.get('safe'):
            meta = json.loads(fidelity.read_text(encoding='utf-8'))['meta']
            if meta.get('audit_verdict') != 'full_pass' or meta.get('edits_rollback') != 0:
                raise ValueError('안전본에 유효한 fidelity 통과 증거가 없습니다')
            result = {'source': str(rewrite), 'round': checkpoint['round'], 'run_id': run_id,
                      'rewrite_sha256': checkpoint['rewrite_sha256']}
            if require_naturalness:
                if round_number != result['round'] or rewrite_sha256 != result['rewrite_sha256']:
                    raise ValueError('최종 선택과 검수한 round/rewrite_sha256이 다릅니다')
                receipt_path = checked(folder, path.parent / 'naturalness.json')
                receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
                report_path = checked(folder, path.parent / '05_naturalness.json')
                raw = report_path.read_bytes()
                report = naturalness_meta(raw, run_id, round_number, rewrite_sha256)
                if (receipt.get('run_id') != run_id or receipt.get('round') != round_number
                        or receipt.get('rewrite_sha256') != rewrite_sha256
                        or receipt.get('naturalness_sha256') != sha(raw)
                        or receipt.get('accepted') is not True or report.get('verdict') != 'accept'
                        or report.get('human_intervention_required') is not False):
                    raise ValueError('같은 안전본의 naturalness accept 증거가 없습니다')
                result['naturalness_accepted'] = True
            return result
    if require_naturalness:
        raise ValueError('양쪽 검수를 통과한 안전본이 없습니다')
    return {'source': str(folder / '01_input.txt'), 'round': None, 'run_id': run_id,
            'rewrite_sha256': sha(original)}


def naturalness_meta(raw, run_id, round_number, rewrite_sha256):
    report = json.loads(raw.decode('utf-8'))
    if not isinstance(report, dict) or not isinstance(report.get('meta'), dict):
        raise ValueError('naturalness 판정 meta가 필요합니다')
    meta = report['meta']
    if (meta.get('run_id') != run_id or meta.get('round') != round_number
            or meta.get('rewrite_sha256') != rewrite_sha256
            or meta.get('verdict') not in ('accept', 'rewrite_round', 'rollback')
            or type(meta.get('human_intervention_required')) is not bool):
        raise ValueError('naturalness 판정이 현재 run·round·rewrite SHA와 다릅니다')
    next_action = report.get('next_action')
    if next_action is not None and (not isinstance(next_action, dict)
                                   or next_action.get('verdict') != meta['verdict']):
        raise ValueError('naturalness 판정 필드가 서로 다릅니다')
    return meta


def archive_naturalness(cwd, run_id, round_number, rewrite_sha256):
    folder = run_path(cwd, run_id)
    selected = select_safe(cwd, run_id)
    if round_number != selected['round'] or rewrite_sha256 != selected['rewrite_sha256']:
        raise ValueError('naturalness 대상과 fidelity 안전본이 다릅니다')
    raw = checked(folder, folder / '05_naturalness.json').read_bytes()
    meta = naturalness_meta(raw, run_id, round_number, rewrite_sha256)
    target = Path(selected['source']).parent
    write_once(target / '05_naturalness.json', raw)
    receipt = {'schema': 1, 'run_id': run_id, 'round': round_number,
               'rewrite_sha256': rewrite_sha256, 'naturalness_sha256': sha(raw),
               'accepted': meta['verdict'] == 'accept' and not meta['human_intervention_required']}
    write_once(target / 'naturalness.json', encoded(receipt))
    return receipt


def history(cwd, run_id=None, limit=20):
    """메타·파일 존재만 조회한다. 입력·윤문·요약 본문을 읽거나 쓰지 않는다."""
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('조회 개수는 1~1000이어야 합니다')
    pattern = re.compile(r'(\d{4}-\d{2}-\d{2})-(\d{3,})')
    if run_id is not None and not pattern.fullmatch(run_id):
        raise ValueError('올바른 run-id가 필요합니다')
    base = base_path(cwd)
    if not base.exists():
        return {'runs': []}
    folders = [folder for folder in base.iterdir()
               if pattern.fullmatch(folder.name) and (run_id is None or folder.name == run_id)]
    folders.sort(key=lambda folder: (pattern.fullmatch(folder.name).group(1),
                                    int(pattern.fullmatch(folder.name).group(2))), reverse=True)
    rows = []
    for folder in folders[:limit]:
        if folder.is_symlink() or not folder.is_dir():
            rows.append({'run_id': folder.name, 'status': 'incomplete', 'verification': 'unverified',
                         'genre': None, 'mode': None, 'final_path': None, 'summary_path': None})
            continue
        final, summary = folder / 'final.md', folder / 'summary.md'
        row = {'run_id': folder.name, 'status': 'legacy_unverified', 'verification': 'unverified',
               'genre': None, 'mode': None,
               'final_path': str(final) if final.is_file() and not final.is_symlink() else None,
               'summary_path': str(summary) if summary.is_file() and not summary.is_symlink() else None}
        meta_path = folder / 'run.json'
        if meta_path.exists():
            try:
                meta = json.loads(checked(folder, meta_path).read_text(encoding='utf-8'))
                known = meta['metadata']
                if (not isinstance(meta, dict) or not isinstance(known, dict)
                        or meta.get('schema') != 1 or meta.get('run_id') != folder.name
                        or not all(isinstance(known.get(key), str) and known[key].strip()
                                   for key in ('genre', 'tone', 'scope'))
                        or known.get('mode') not in ('audit', 'rewrite', 'strict')):
                    raise ValueError('invalid metadata')
                row.update(genre=known['genre'], mode=known['mode'], status='reserved')
                if (folder / '01_input.txt').is_file():
                    row['status'] = 'in_progress' if (folder / 'input.json').is_file() else 'incomplete'
                if row['final_path'] or row['summary_path']:
                    ready = row['summary_path'] and (known['mode'] == 'audit' or row['final_path'])
                    row['status'] = 'outputs_present' if ready else 'incomplete'
            except (OSError, ValueError, TypeError, KeyError):
                row['status'] = 'incomplete'
        rows.append(row)
    return {'runs': rows}


def emit(value):
    # Windows 파이프의 기본 stdout은 cp949라 한글·이모지가 깨지거나 인코딩 오류가 난다. 항상 UTF-8로 쓴다.
    sys.stdout.buffer.write((json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8'))
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['reserve', 'freeze-input', 'archive-round',
                                         'archive-naturalness', 'safe', 'history'])
    parser.add_argument('--cwd', required=True)
    parser.add_argument('--run-id')
    parser.add_argument('--date')
    parser.add_argument('--mode', choices=['audit', 'rewrite', 'strict'])
    parser.add_argument('--genre')
    parser.add_argument('--tone')
    parser.add_argument('--scope')
    parser.add_argument('--source', action='append')
    parser.add_argument('--input-file')
    parser.add_argument('--round', type=int)
    parser.add_argument('--rewrite-sha256')
    parser.add_argument('--require-naturalness', action='store_true')
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    try:
        if args.action == 'reserve':
            result = reserve(args.cwd, {'mode': args.mode, 'genre': args.genre, 'tone': args.tone,
                                       'scope': args.scope, 'sources': args.source}, args.date)
        elif args.action == 'freeze-input':
            raw = Path(args.input_file).read_bytes() if args.input_file else sys.stdin.buffer.read()
            result = freeze_input(args.cwd, args.run_id, raw)
        elif args.action == 'archive-round':
            result = archive_round(args.cwd, args.run_id, args.round, args.rewrite_sha256)
        elif args.action == 'archive-naturalness':
            result = archive_naturalness(args.cwd, args.run_id, args.round, args.rewrite_sha256)
        elif args.action == 'safe':
            result = select_safe(args.cwd, args.run_id, require_naturalness=args.require_naturalness,
                                 round_number=args.round, rewrite_sha256=args.rewrite_sha256)
        else:
            result = history(args.cwd, args.run_id, args.limit)
    except (OSError, ValueError, TypeError, KeyError) as error:
        emit({'blocked': True, 'reason': str(error)})
        return 2
    emit(result)
    return 0


if __name__ == '__main__':
    sys.exit(main())
