"""맵 실행의 출력 폴더 소유권과 원자적 JSON 교체를 관리한다."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import time
import uuid


LOCK_NAME = ".gx-map.lock"


class OutputBusyError(ValueError):
    """다른 실행의 출력과 섞지 않기 위해 이번 실행을 시작하지 않았다."""


@contextmanager
def output_lock(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / LOCK_NAME
    token = uuid.uuid4().hex
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError:
        raise OutputBusyError(
            "맵 출력 폴더가 다른 실행에서 사용 중입니다. 실행 종료를 기다리세요. "
            "중단된 잠금은 기존 실행의 종료를 확인한 뒤 제거해야 합니다."
        ) from None
    try:
        with handle:
            json.dump({"pid": os.getpid(), "token": token}, handle)
    except BaseException:
        lock.unlink(missing_ok=True)
        raise
    try:
        yield
    finally:
        try:
            owner = json.loads(lock.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            owner = None
        if isinstance(owner, dict) and owner.get("token") == token:
            lock.unlink(missing_ok=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    pending = Path(name)
    try:
        pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for attempt in range(5):
            try:
                pending.replace(path)
                break
            except PermissionError as error:
                # Windows의 짧은 공유/교체 경합만 제한적으로 재시도한다.
                if getattr(error, "winerror", None) not in {5, 32, 33} or attempt == 4:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        pending.unlink(missing_ok=True)
