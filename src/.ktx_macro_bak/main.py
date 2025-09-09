"""
KTX Macro V2 메인 애플리케이션 진입점
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

# PyQt6 임포트
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QFont

# 프로젝트 모듈 임포트
from .utils.logger import setup_logger, get_logger
from .utils.system_utils import SystemUtils
from .ui.main_window import MainWindow


def setup_application() -> QApplication:
    """애플리케이션 설정"""

    # Qt 애플리케이션 생성
    app = QApplication(sys.argv)

    # 애플리케이션 메타데이터 설정
    app.setApplicationName("KTX Macro V2")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("KTX Macro Team")
    app.setOrganizationDomain("ktx-macro.com")

    # 애플리케이션 아이콘 설정 (있는 경우)
    icon_path = Path("assets/icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # 기본 폰트 설정
    font = QFont()
    if sys.platform == "win32":
        font.setFamily("맑은 고딕")
        font.setPointSize(9)
    elif sys.platform == "darwin":
        font.setFamily("Apple SD Gothic Neo")
        font.setPointSize(13)
    else:
        font.setFamily("Noto Sans CJK KR")
        font.setPointSize(10)

    app.setFont(font)

    # 스타일 설정
    app.setStyle("Fusion")

    return app


def check_dependencies() -> bool:
    """의존성 확인"""
    logger = get_logger(__name__)

    try:
        # 필수 의존성 확인
        dependencies = SystemUtils.check_dependencies()

        missing_deps = [dep for dep, available in dependencies.items() if not available]

        if missing_deps:
            error_msg = (
                "다음 필수 패키지가 설치되지 않았습니다:\n\n"
                + "\n".join(f"• {dep}" for dep in missing_deps)
                + "\n\n설치 명령어:\n"
                + f"uv add {' '.join(missing_deps)}"
            )

            logger.error(f"의존성 확인 실패: {missing_deps}")

            # GUI가 사용 가능한 경우에만 메시지박스 표시
            try:
                QMessageBox.critical(None, "의존성 오류", error_msg)
            except:
                print(f"오류: {error_msg}")

            return False

        logger.info("모든 의존성이 확인되었습니다")
        return True

    except Exception as e:
        logger.error(f"의존성 확인 중 오류: {e}")
        return False


def show_splash_screen(app: QApplication) -> Optional[QSplashScreen]:
    """스플래시 스크린 표시"""
    try:
        # 스플래시 이미지 경로
        splash_path = Path("assets/splash.png")

        if splash_path.exists():
            # 스플래시 이미지가 있는 경우
            pixmap = QPixmap(str(splash_path))
        else:
            # 기본 스플래시 이미지 생성
            pixmap = QPixmap(400, 300)
            pixmap.fill(Qt.GlobalColor.white)

        splash = QSplashScreen(pixmap)
        splash.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint
        )

        # 로딩 메시지 표시
        splash.showMessage(
            "KTX Macro V2 로딩 중...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.black,
        )

        splash.show()
        app.processEvents()

        return splash

    except Exception as e:
        logger = get_logger(__name__)
        logger.warning(f"스플래시 스크린 생성 실패: {e}")
        return None


def setup_directories():
    """필요한 디렉토리 생성"""
    logger = get_logger(__name__)

    try:
        # 기본 디렉토리들
        directories = ["config", "logs", "assets/screenshots", "assets/backups"]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

        logger.debug("필요한 디렉토리들이 생성되었습니다")

    except Exception as e:
        logger.error(f"디렉토리 생성 실패: {e}")


def setup_exception_handler():
    """전역 예외 처리기 설정"""
    logger = get_logger(__name__)

    def handle_exception(exc_type, exc_value, exc_traceback):
        """처리되지 않은 예외 핸들러"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Ctrl+C는 정상 종료로 처리
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # 로그에 기록
        logger.critical(
            "처리되지 않은 예외 발생", exc_info=(exc_type, exc_value, exc_traceback)
        )

        # GUI 오류 다이얼로그 표시
        try:
            error_msg = (
                f"예상치 못한 오류가 발생했습니다:\n\n{exc_type.__name__}: {exc_value}"
            )
            QMessageBox.critical(None, "오류", error_msg)
        except:
            print(f"Fatal Error: {exc_type.__name__}: {exc_value}")

    sys.excepthook = handle_exception


def main():
    """메인 함수"""

    # 로깅 설정
    logger = setup_logger(
        name="ktx_macro", level=logging.DEBUG, enable_console=True, enable_file=True
    )

    logger.info("=" * 60)
    logger.info("KTX Macro V2 시작")
    logger.info("=" * 60)

    try:
        # 시스템 정보 로깅
        system_info = SystemUtils.get_system_info()
        logger.info(
            f"시스템: {system_info.get('platform')} {system_info.get('platform_release')}"
        )
        logger.info(f"Python: {system_info.get('python_version')}")
        logger.info(
            f"메모리: {system_info.get('memory', {}).get('total_gb', 'Unknown')}GB"
        )

        # 필요한 디렉토리 생성
        setup_directories()

        # Qt 애플리케이션 생성
        app = setup_application()

        # 의존성 확인
        if not check_dependencies():
            logger.error("의존성 확인 실패로 애플리케이션을 종료합니다")
            return 1

        # 전역 예외 처리기 설정
        setup_exception_handler()

        # 스플래시 스크린 표시
        splash = show_splash_screen(app)

        # 메인 윈도우 생성
        logger.info("메인 윈도우 생성 중...")

        if splash:
            splash.showMessage(
                "메인 윈도우 로딩 중...",
                Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                Qt.GlobalColor.black,
            )
            app.processEvents()

        main_window = MainWindow()

        # 스플래시 스크린 숨기기
        if splash:

            def hide_splash():
                splash.finish(main_window)
                main_window.show()
                main_window.raise_()
                main_window.activateWindow()

            # 2초 후 스플래시 숨기기
            QTimer.singleShot(2000, hide_splash)
        else:
            main_window.show()

        logger.info("애플리케이션 초기화 완료")

        # 애플리케이션 실행
        exit_code = app.exec()

        logger.info(f"애플리케이션 종료됨 (코드: {exit_code})")
        return exit_code

    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨 (Ctrl+C)")
        return 0

    except Exception as e:
        logger.critical(f"애플리케이션 시작 실패: {e}", exc_info=True)

        # 콘솔에도 출력
        print(f"Fatal Error: {e}")

        try:
            QMessageBox.critical(
                None, "치명적 오류", f"애플리케이션을 시작할 수 없습니다:\n\n{e}"
            )
        except:
            pass

        return 1


def cli_main():
    """CLI 진입점 (설치된 패키지에서 호출)"""
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n애플리케이션이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"치명적 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
