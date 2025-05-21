# 프로젝트 파일 구조 분석 (openai-personal-cli)

## 1. 최상위 디렉토리

*   `main.py`, `main_macos.py`: 애플리케이션 진입점 (CLI/GUI 실행 스크립트 포함 가능성)
*   `launch_*.sh`, `launch_*.bat`: 플랫폼별 실행 스크립트
*   `settings.json`: 애플리케이션 설정을 담고 있는 JSON 파일
*   `requirements.txt`: Python 의존성 목록
*   `README.md`: 프로젝트 설명 및 사용법 안내
*   `src/`: 핵심 소스 코드가 위치하는 디렉토리
*   `spec/`: 분석 및 명세 문서 디렉토리

## 2. `src/` 디렉토리 구조

### 2.1. `src/core/`

*   **`api_client.py`**: OpenAI 등 외부 API와의 통신을 담당. 채팅, 이미지 생성, 비전 API 호출 로직 포함. (네트워크 I/O 발생, `asyncio` 전환 시 주요 대상)
*   **`settings.py`**: `settings.json` 파일을 로드하고, 설정값을 쉽게 가져올 수 있는 인터페이스 제공.

### 2.2. `src/features/`

*   **`chat.py` (`ChatManager`)**: 대화 내용 관리, 사용자 입력에 대한 AI 응답 생성 요청. `APIClient`를 통해 채팅 API 호출.
*   **`image.py` (`ImageManager`)**: 이미지 생성 및 분석 요청 처리. 대화 맥락을 활용한 프롬프트 구성, `APIClient`를 통해 이미지/비전 API 호출.
*   **`controllers.py` (`MainController`)**: 애플리케이션의 주요 로직 흐름 제어. 사용자 입력을 받아 `ChatManager` 또는 `ImageManager`에 전달하고 결과 반환.

### 2.3. `src/gui/`

*   **`app.py` (`App`)**: PyQt6 `QApplication` 초기화 및 실행. `MainController`, `MainWindow` 등 주요 객체 생성.
*   **`main_window.py` (`MainWindow`)**: 메인 GUI 윈도우 구성 (채팅창, 입력 필드 등). `GuiHandler`와 상호작용하여 UI 업데이트 및 사용자 이벤트 처리.
*   **`gui_handler.py` (`GuiHandler`)**: GUI 이벤트와 백그라운드 작업(워커 스레드) 간의 중재자. 사용자 명령에 따라 워커 스레드 생성 및 관리, 워커 결과를 받아 `MainWindow`에 UI 업데이트 요청. (스레딩 관리 핵심, `asyncio` 전환 시 가장 큰 변화 예상)
*   **`workers.py` (`APIWorker`, `ChatWorker`, 등)**: `QThread`를 상속받아 API 호출 등 오래 걸리는 작업을 백그라운드에서 비동기적으로 처리. (현재 스레딩 구현의 핵심, `asyncio` 태스크로 대체될 부분)
*   **`dialogs.py` (`ProcessingDialog`)**: 처리 중 상태를 표시하는 다이얼로그. 사용자 취소 요청을 받아 `GuiHandler`에 전달.

### 2.4. `src/utils/`

*   **`text_formatter.py` (`TextFormatter`)**: 텍스트 포맷팅 유틸리티. 마크다운/LaTeX를 HTML로 변환, HTML 특수문자 이스케이프 처리.

## 3. 중복 의심 파일

*   `src/chat.py`: `src/features/chat.py`와 내용이 거의 동일하며, 현재 `MainController`에서는 `src/features/chat.py`를 사용하는 것으로 보임. 추후 정리 필요.

## 4. 주요 스레딩 의존성

*   현재 스레딩은 PyQt6의 `QThread`를 사용하여 `src/gui/workers.py`에서 구현됨.
*   `src/gui/gui_handler.py`가 이 워커 스레드들을 생성하고 관리하며, GUI의 반응성을 유지하면서 `src/core/api_client.py`를 통해 외부 API를 호출.
*   `src/features/`의 `ChatManager`, `ImageManager`, `MainController`는 `APIClient`를 사용하므로, 간접적으로 스레드 환경에서 실행됨.
