> gx-setup/SKILL.md의 이번 실행에서 Java 계열 타입이 감지된 경우만 읽는다. 소비 프로젝트 경로·변수는 상위 스킬을 유지하고 번들 상대경로는 이 파일 위치 기준이다.

# JDK 확인

신규 등록·기존 유지 여부와 무관하게 이번 프로젝트의 detect가 매칭된 Java 계열만 확인한다. `java-spring`·`java-maven` 등 Gradle/Maven 기반이며 build/test에 `gradlew` 또는 `mvn`이 포함된 타입이 대상이다. config에 항목만 있고 이번 detect가 매칭되지 않았으면 이 참조를 읽거나 도구를 실행하지 않는다.

1. `uname -s`로 OS를 감지한다. 실제 셸은 상위 하네스 규약을 따른다.
2. `java -version`과 `javac -version`을 각각 실행해 런타임과 컴파일러의 존재·종료코드·버전을 확인한다. `java`만 성공하면 JRE만 확인된 것이므로 JDK 완료로 표시하지 않는다. `1.8` 표기는 주 버전 8로 해석한다.
3. 두 명령이 모두 성공하고 주 버전이 일치하며 JDK 8 이상(프로젝트에 더 높은 요구 버전이 있으면 그 버전)을 만족하면 → `JDK : 완료 ✅ (java {버전}, javac {버전})` 출력. 버전이 다르면 `JDK : 미확인 (java/javac 버전 불일치)`로 표시하고 `JAVA_HOME`·PATH 확인을 안내한다. 환경을 자동 변경하지 않는다.
4. 컴파일러가 없거나 버전이 낮으면 → `JDK : 미설정 (컴파일러 부재 또는 요구 버전 미충족)`으로 표시하고 OS별 설치 안내를 제공한다. 이 단계에서 설치·네트워크 명령은 실행하지 않는다:
   - **Linux**: `sudo apt install openjdk-17-jdk` 또는 `sudo yum install java-17-openjdk-devel`
   - **macOS**: `brew install openjdk@17`
   - **Windows (MSYS/Git Bash)**: https://adoptium.net 에서 다운로드 안내

확인한 상태를 유지하고 상위 스킬의 2단계로 진행한다.
