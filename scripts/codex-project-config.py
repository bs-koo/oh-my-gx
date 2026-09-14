#!/usr/bin/env python3
"""Safely merge explicit Codex setup choices into a project's GX config."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import sys


def reject_constant(value):
    raise ValueError(f'non-JSON number: {value}')


def read_object(path):
    value = json.loads(path.read_text(encoding='utf-8-sig'), parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError(f'JSON object required: {path}')
    return value


def merge(base, updates):
    result = dict(base)
    for key, value in updates.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def update_config(cwd, template, updates_file):
    root = Path(cwd).resolve()
    if not root.is_dir():
        raise ValueError(f'project directory does not exist: {root}')
    config = root / '.claude/config.json'
    existing = config.is_file()
    base = read_object(config if existing else Path(template))
    updates = read_object(Path(updates_file))
    merged = merge(base, updates)
    if not existing or canonical(base) != canonical(merged):
        rendered = json.dumps(merged, ensure_ascii=False, indent=2,
                              allow_nan=False) + '\n'
        # Validate serialization before touching the target directory.
        json.loads(rendered, parse_constant=reject_constant)
        config.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            fd, name = tempfile.mkstemp(prefix='.config-', suffix='.tmp', dir=config.parent)
            temporary = Path(name)
            with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
                stream.write(rendered)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, config)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    if canonical(read_object(config)) != canonical(merged):
        raise ValueError(f'config verification failed: {config}')
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cwd', required=True, type=Path)
    parser.add_argument('--template', required=True, type=Path)
    parser.add_argument('--updates', required=True, type=Path)
    args = parser.parse_args()
    try:
        config = update_config(args.cwd, args.template, args.updates)
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        sys.stderr.buffer.write(f'config update failed: {exc}\n'.encode('utf-8'))
        return 1
    sys.stdout.buffer.write((str(config) + '\n').encode('utf-8'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
