> gx-setup/SKILL.md의 `--inspect` 또는 "설정 진단만" 분기에서만 읽는다. 소비 프로젝트 경로·변수는 상위 스킬을 유지하고 번들 상대경로는 이 파일 위치 기준이다.

# 설정 진단만

현재 프로젝트 루트를 확인하고 설치된 [gx-setup-scan.py](../../../../scripts/gx-setup-scan.py)를 `python "<GX_PLUGIN_ROOT>/scripts/gx-setup-scan.py" --cwd "<PROJECT_ROOT>"`로 실행한다. `GX_PLUGIN_ROOT`는 상위 SKILL.md의 실제 설치 경로에서 확인한 값이다. 소비 프로젝트 cwd를 설치 위치로 가정하지 않는다. Bash는 `python3`, Windows PowerShell은 `python`과 공통 UTF-8 입출력 규약을 사용하며 `PYTHONDONTWRITEBYTECODE=1`로 둔다.

config 부재도 정상 진단 입력이며 생성하지 않는다. 기존 config가 잘못됐으면 오류·경로를 보고하며 복구하거나 덮어쓰지 않는다. helper 실패나 불완전한 스캔을 프로젝트 없음·정상 설정으로 바꾸지 않는다.

반환값으로 등록 상태, 발견 프로젝트의 마커·루트, 미등록 스택과 확인할 명령·`roots` 보완점을 대화에 보여주고 종료한다. 기존 명령이 실제 동작한다고 단정하지 않는다. config·`.gitignore`·질문/승인 기록을 쓰지 않고 설치·네트워크·빌드·테스트를 실행하지 않는다. 진단 뒤 초기 설정 절차로 진입하지 않는다.
