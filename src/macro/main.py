import sys
from pathlib import Path
from typing import Optional

# PyQt6 임포트
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QPixmap

from .ui.main_window import MainWindow


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
        print(f"스플래시 스크린 생성 실패: {e}")
        return None


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


def setup_directories():
    """필요한 디렉토리 생성"""
    try:
        # 기본 디렉토리들
        directories = ["config", "logs", "assets/screenshots", "assets/backups"]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

        print("필요한 디렉토리들이 생성되었습니다")

    except Exception as e:
        print(f"디렉토리 생성 실패: {e}")


def main():
    setup_directories()
    app = setup_application()
    # 스플래시 스크린 표시
    splash = show_splash_screen(app)

    # 메인 윈도우 생성
    print("메인 윈도우 생성 중...")

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
        splash.finish(main_window)
        main_window.show()
        main_window.raise_()
        main_window.activateWindow()

    main_window.show()

    exit_code = app.exec()
    print(f"애플리케이션 종료됨 (코드: {exit_code})")
    return exit_code


def cli_main():
    """CLI 진입점 (설치된 패키지에서 호출)"""
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n애플리케이션이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"치명적 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
