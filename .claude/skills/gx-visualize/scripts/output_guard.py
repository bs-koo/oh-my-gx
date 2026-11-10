"""맵 실행의 출력 폴더 소유권과 원자적 JSON 교체를 관리한다."""

from contextlib import contextmanager
import json
from datetime import datetime, timezone
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import uuid


LOCK_NAME = ".gx-map.lock"


class OutputBusyError(ValueError):
    """다른 실행의 출력과 섞지 않기 위해 이번 실행을 시작하지 않았다."""


def _pid_alive(pid):
    """살아 있으면 True, 없으면 False, 판정 불가면 None."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return None
    if sys.platform == "win32":
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False if ctypes.get_last_error() == 87 or kernel.GetLastError() == 87 else None
        try:
            code = ctypes.c_ulong()
            if not kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code)):
                return None
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


def _read_owner(lock: Path):
    try:
        owner = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return owner if isinstance(owner, dict) else None


def _reclaim_if_stale(lock: Path) -> bool:
    """같은 호스트에서 소유 pid가 확실히 종료된 잠금만 회수한다."""
    owner = _read_owner(lock)
    if not owner or owner.get("host") != socket.gethostname() or _pid_alive(owner.get("pid")) is not False:
        return False
    current = _read_owner(lock)
    if not current or current.get("token") != owner.get("token"):
        return False
    lock.unlink(missing_ok=True)
    return True


def _busy_message(lock: Path) -> str:
    owner = _read_owner(lock) or {}
    info = (f"소유 pid={owner.get('pid', '알 수 없음')}, 호스트={owner.get('host', '알 수 없음')}, "
            f"시작={owner.get('started_at', '알 수 없음')}")
    return ("맵 출력 폴더가 다른 실행에서 사용 중입니다. 실행 종료를 기다리세요. "
            f"잠금 소유 정보: {info}. 같은 호스트에서 소유 pid가 종료됐으면 다음 실행이 자동 회수합니다. "
            f"다른 호스트이거나 판정이 불확실하면 소유 실행이 끝났음을 직접 확인한 뒤 {lock}만 삭제하고 재실행하세요.")


@contextmanager
def output_lock(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / LOCK_NAME
    token = uuid.uuid4().hex
    try:
        handle = lock.open("x", encoding="utf-8")
    except FileExistsError:
        if not _reclaim_if_stale(lock):
            raise OutputBusyError(_busy_message(lock)) from None
        try:
            handle = lock.open("x", encoding="utf-8")
        except FileExistsError:
            raise OutputBusyError(_busy_message(lock)) from None
    try:
        with handle:
            json.dump({"pid": os.getpid(), "token": token, "host": socket.gethostname(),
                       "started_at": datetime.now(timezone.utc).isoformat()}, handle)
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
