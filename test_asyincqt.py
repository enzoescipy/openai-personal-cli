import sys

print("Attempting to import PyQt6 and its core components...")
pyqt_imported_successfully = False
q_application_class = None
try:
    # PyQt6의 핵심 모듈들을 먼저 임포트
    import PyQt6.QtCore
    import PyQt6.QtGui
    import PyQt6.QtWidgets

    # 그 다음 QApplication 가져오기
    from PyQt6.QtWidgets import QApplication
    q_application_class = QApplication # 나중에 qasync 테스트에 사용하기 위해 저장

    print(f"PyQt6.QtCore: {PyQt6.QtCore}")
    print(f"PyQt6.QtGui: {PyQt6.QtGui}")
    print(f"PyQt6.QtWidgets: {PyQt6.QtWidgets}")
    print(f"PyQt6.QtWidgets.QApplication: {q_application_class}")
    pyqt_imported_successfully = True

except Exception as e:
    print(f"Error importing PyQt6 components: {e}")
    print("--- PyQt6 Import Test Failed ---")
    exit()

if not pyqt_imported_successfully:
    print("PyQt6 import failed, cannot proceed to qasync test.")
    exit()

print("\nPre-setting sys.modules for qasync (just in case)...")
# qasync가 sys.modules를 참고할 경우를 대비
if 'PyQt6' not in sys.modules:
    sys.modules['PyQt6'] = PyQt6
if 'PyQt6.QtCore' not in sys.modules:
    sys.modules['PyQt6.QtCore'] = PyQt6.QtCore
if 'PyQt6.QtGui' not in sys.modules:
    sys.modules['PyQt6.QtGui'] = PyQt6.QtGui
if 'PyQt6.QtWidgets' not in sys.modules:
    sys.modules['PyQt6.QtWidgets'] = PyQt6.QtWidgets

print(f"PyQt6 in sys.modules: {'PyQt6' in sys.modules}")


print("\nAttempting to import qasync...")
try:
    # ***** 여기가 중요! qasync 임포트 직전에 PyQt6 관련 심볼들이 확실히 로드되도록 함 *****
    import qasync
    print("qasync imported successfully.")
    print(f"qasync: {qasync}")

    # qasync가 QEventLoop를 만들 수 있는지 확인
    # 이 테스트를 하려면 QApplication 인스턴스가 필요.
    # print("\nAttempting to create QApplication instance for QEventLoop test...")
    # app_instance = q_application_class(sys.argv) # QApplication 인스턴스 생성
    # print("QApplication instance created.")
    # loop = qasync.QEventLoop(app_instance)
    # print(f"qasync.QEventLoop created successfully: {loop}")

except ImportError as e:
    if "No Qt implementations found" in str(e):
        print(f"Error importing qasync: {e}")
        print(">>> This is the known 'No Qt implementations found' error. <<<")
    else:
        print(f"Error importing qasync (different error): {e}")
except Exception as e:
    print(f"An unexpected error occurred while importing or testing qasync: {e}")

print("\n--- Test Complete ---")