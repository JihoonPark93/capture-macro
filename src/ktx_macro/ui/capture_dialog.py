"""
화면 캡쳐 다이얼로그
"""

import uuid
from pathlib import Path
from typing import Optional, Tuple
import logging

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QGroupBox,
    QMessageBox,
    QWidget,
    QApplication,
    QFrame,
)
from PyQt6.QtCore import QThread, Qt, QRect, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QScreen, QCursor, QFont

from ..models.macro_models import CaptureRegion, ImageTemplate
from ..core.macro_engine import MacroEngine

logger = logging.getLogger(__name__)


class ScreenOverlay(QWidget):
    """전체 화면을 덮는 오버레이"""

    selection_completed = pyqtSignal(QRect)

    def __init__(self, screenshot: QPixmap):
        super().__init__()

        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_selecting = False
        self.selection_rect = QRect()

        # 미리 캡쳐된 스크린샷 사용
        self.screenshot = screenshot

        # 전체 화면 크기로 설정
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        # 윈도우 플래그 설정
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # 반투명 배경
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 커서 설정
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.show()

    def paintEvent(self, event):
        """그리기 이벤트 (QPainter 리소스 안전 관리)"""
        painter = QPainter(self)
        try:
            # 배경을 어둡게 오버레이
            overlay_color = QColor(0, 0, 0, 128)  # 반투명 검은색
            painter.fillRect(self.rect(), overlay_color)

            # 선택 영역이 있으면 원본 이미지 표시
            if not self.selection_rect.isEmpty():
                # 선택 영역만 원본 이미지로 표시
                painter.drawPixmap(
                    self.selection_rect, self.screenshot, self.selection_rect
                )

                # 선택 영역 테두리 그리기
                pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)
                painter.setPen(pen)
                painter.drawRect(self.selection_rect)

                # 선택 영역 정보 표시
                self.draw_selection_info(painter)
        finally:
            # QPainter 리소스 명시적 해제
            painter.end()

    def draw_selection_info(self, painter: QPainter):
        """선택 영역 정보 표시"""
        if self.selection_rect.isEmpty():
            return

        # 폰트 설정
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)

        # 텍스트 색상
        painter.setPen(QColor(255, 255, 255))

        # 선택 영역 크기 정보
        width = self.selection_rect.width()
        height = self.selection_rect.height()
        info_text = f"{width} x {height}"

        # 텍스트 위치 계산 (선택 영역 위쪽)
        text_x = self.selection_rect.x()
        text_y = self.selection_rect.y() - 5

        # 화면 위쪽 경계를 벗어나면 아래쪽에 표시
        if text_y < 20:
            text_y = self.selection_rect.bottom() + 20

        # 배경 사각형 그리기
        text_rect = painter.fontMetrics().boundingRect(info_text)
        bg_rect = QRect(
            text_x - 5,
            text_y - text_rect.height() - 5,
            text_rect.width() + 10,
            text_rect.height() + 10,
        )

        painter.fillRect(bg_rect, QColor(0, 0, 0, 180))

        # 텍스트 그리기
        painter.drawText(text_x, text_y, info_text)

    def mousePressEvent(self, event):
        """마우스 누르기 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.is_selecting = True
            self.selection_rect = QRect()
            self.update()

    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트"""
        if self.is_selecting:
            self.end_point = event.pos()

            # 선택 영역 계산
            self.selection_rect = QRect(
                min(self.start_point.x(), self.end_point.x()),
                min(self.start_point.y(), self.end_point.y()),
                abs(self.end_point.x() - self.start_point.x()),
                abs(self.end_point.y() - self.start_point.y()),
            )

            self.update()

    def mouseReleaseEvent(self, event):
        """마우스 릴리즈 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False

            # 최소 크기 검사
            if self.selection_rect.width() > 10 and self.selection_rect.height() > 10:
                self.selection_completed.emit(self.selection_rect)
            else:
                # 너무 작은 선택은 무시
                self.selection_rect = QRect()
                self.update()

    def keyPressEvent(self, event):
        """키 이벤트"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)


class CaptureSettingsDialog(QDialog):
    """캡쳐 설정 다이얼로그"""

    def __init__(self, parent=None, initial_rect: Optional[QRect] = None):
        super().__init__(parent)

        self.capture_rect = initial_rect or QRect()
        self.template_name = ""
        self.threshold = 0.8

        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("캡쳐 설정")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # 템플릿 이름
        name_group = QGroupBox("템플릿 이름")
        name_layout = QVBoxLayout(name_group)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("이미지 템플릿 이름을 입력하세요")
        name_layout.addWidget(self.name_edit)

        layout.addWidget(name_group)

        # 캡쳐 영역 정보
        region_group = QGroupBox("캡쳐 영역")
        region_layout = QVBoxLayout(region_group)

        if not self.capture_rect.isEmpty():
            region_info = QLabel(
                f"위치: ({self.capture_rect.x()}, {self.capture_rect.y()})\n"
                f"크기: {self.capture_rect.width()} x {self.capture_rect.height()}"
            )
            region_layout.addWidget(region_info)

        layout.addWidget(region_group)

        # 매칭 설정
        matching_group = QGroupBox("매칭 설정")
        matching_layout = QVBoxLayout(matching_group)

        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("신뢰도 임계값:"))

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(50, 100)
        self.threshold_spin.setSuffix("%")
        self.threshold_spin.setValue(80)
        threshold_layout.addWidget(self.threshold_spin)

        matching_layout.addLayout(threshold_layout)
        layout.addWidget(matching_group)

        # 버튼
        button_layout = QHBoxLayout()

        self.ok_button = QPushButton("확인")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)

        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # 포커스 설정
        self.name_edit.setFocus()

    def get_template_data(self) -> Tuple[str, float]:
        """템플릿 데이터 반환"""
        return self.name_edit.text().strip(), self.threshold_spin.value() / 100.0


class CaptureDialog(QDialog):
    """캡쳐 메인 다이얼로그"""

    capture_completed = pyqtSignal(str, str)  # template_id, template_name

    def __init__(self, parent=None):
        super().__init__(parent)

        self.engine: Optional[MacroEngine] = None
        self.overlay: Optional[ScreenOverlay] = None

        # 부모가 MainWindow인 경우 엔진 참조
        if hasattr(parent, "engine"):
            self.engine = parent.engine

        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("화면 캡쳐")
        self.setModal(True)
        self.resize(500, 300)

        layout = QVBoxLayout(self)

        # 안내 텍스트
        info_label = QLabel(
            "화면 캡쳐를 위한 단계:\n\n"
            "1. '캡쳐 시작' 버튼을 클릭합니다\n"
            "2. 화면이 어두워지면 마우스로 원하는 영역을 드래그합니다\n"
            "3. 영역 선택이 완료되면 설정 창이 나타납니다\n"
            "4. 템플릿 이름과 설정을 입력하고 저장합니다\n\n"
            "ESC 키를 누르면 캡쳐를 취소할 수 있습니다."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "QLabel { padding: 15px; background-color: #f0f8ff; border: 1px solid #ccc; border-radius: 5px; }"
        )
        layout.addWidget(info_label)

        # 버튼
        button_layout = QHBoxLayout()

        self.capture_button = QPushButton("캡쳐 시작")
        self.capture_button.clicked.connect(self.start_screen_capture)
        button_layout.addWidget(self.capture_button)

        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # 스타일 적용
        self.capture_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """
        )

    def start_capture(self):
        """캡쳐 시작 (외부 호출용)"""
        self.show()

        # 잠시 후 자동으로 화면 캡쳐 시작
        QTimer.singleShot(500, self.start_screen_capture)

    def start_screen_capture(self):
        """화면 캡쳐 시작"""
        try:
            # 현재 다이얼로그 숨기기
            self.hide()

            # 부모 윈도우(메인 윈도우)도 숨기기
            if self.parent():
                self.parent().hide()

            for _ in range(5):
                QApplication.processEvents()
                QThread.msleep(50)  # 약간의 지연

            # 화면이 업데이트되기를 잠시 기다림
            QApplication.processEvents()
            QTimer.singleShot(200, self._create_overlay)

            logger.debug("화면 캡쳐 오버레이 시작됨")

        except Exception as e:
            logger.error(f"화면 캡쳐 시작 실패: {e}")
            QMessageBox.critical(self, "오류", f"화면 캡쳐를 시작할 수 없습니다: {e}")
            self.show()
            if self.parent():
                self.parent().show()

    def _create_overlay(self):
        """오버레이 생성 (지연 실행)"""
        try:
            # 현재 화면 스크린샷 캡쳐 (윈도우들이 숨겨진 상태에서)
            screen = QApplication.primaryScreen()
            screenshot = screen.grabWindow(0)

            # 오버레이 생성
            self.overlay = ScreenOverlay(screenshot)
            self.overlay.selection_completed.connect(self.on_selection_completed)
        except Exception as e:
            logger.error(f"오버레이 생성 실패: {e}")
            if self.parent():
                self.parent().show()
            self.show()

    def on_selection_completed(self, rect: QRect):
        """영역 선택 완료"""
        try:
            # 오버레이 닫기
            if self.overlay:
                self.overlay.close()
                self.overlay = None

            # 부모 윈도우(메인 윈도우) 다시 표시
            if self.parent():
                self.parent().show()

            # 다이얼로그 다시 표시
            self.show()

            # 선택 영역이 유효한지 확인
            if rect.isEmpty() or rect.width() < 10 or rect.height() < 10:
                QMessageBox.warning(self, "경고", "선택한 영역이 너무 작습니다.")
                return

            # 설정 다이얼로그 표시
            self.show_capture_settings(rect)

        except Exception as e:
            logger.error(f"영역 선택 처리 실패: {e}")
            QMessageBox.critical(self, "오류", f"영역 선택을 처리할 수 없습니다: {e}")
            # 오류 발생 시에도 부모 윈도우 복원
            if self.parent():
                self.parent().show()

    def show_capture_settings(self, rect: QRect):
        """캡쳐 설정 다이얼로그 표시"""
        try:
            settings_dialog = CaptureSettingsDialog(self, rect)

            if settings_dialog.exec() == QDialog.DialogCode.Accepted:
                template_name, threshold = settings_dialog.get_template_data()

                if not template_name:
                    QMessageBox.warning(self, "경고", "템플릿 이름을 입력하세요.")
                    return

                # 캡쳐 실행
                self.capture_and_save(rect, template_name, threshold)

        except Exception as e:
            logger.error(f"캡쳐 설정 표시 실패: {e}")
            QMessageBox.critical(self, "오류", f"설정을 표시할 수 없습니다: {e}")

    def capture_and_save(self, rect: QRect, template_name: str, threshold: float):
        """캡쳐 및 저장"""
        try:
            if not self.engine:
                QMessageBox.critical(self, "오류", "매크로 엔진이 연결되지 않았습니다.")
                return

            # 스크린샷 캡쳐
            screen = QApplication.primaryScreen()
            screenshot = screen.grabWindow(
                0, rect.x(), rect.y(), rect.width(), rect.height()
            )

            if screenshot.isNull():
                QMessageBox.critical(self, "오류", "스크린샷 캡쳐에 실패했습니다.")
                return

            # 파일 저장
            template_id = str(uuid.uuid4())
            screenshot_dir = Path(self.engine.config.screenshot_save_path)
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            file_name = f"{template_name}_{template_id[:8]}.png"
            file_path = screenshot_dir / file_name

            if not screenshot.save(str(file_path), "PNG"):
                QMessageBox.critical(self, "오류", "이미지 저장에 실패했습니다.")
                return

            # 캡쳐 영역 생성
            capture_region = CaptureRegion(
                x=rect.x(), y=rect.y(), width=rect.width(), height=rect.height()
            )

            # 이미지 템플릿 생성
            template = ImageTemplate(
                id=template_id,
                name=template_name,
                file_path=str(file_path),
                capture_region=capture_region,
                threshold=threshold,
            )

            # 엔진에 추가
            self.engine.config.add_image_template(template)
            self.engine.save_config()

            logger.info(f"이미지 템플릿 생성됨: {template_name} ({file_path})")

            # 성공 신호 발송
            self.capture_completed.emit(template_id, template_name)

            # 성공 메시지
            QMessageBox.information(
                self,
                "성공",
                f"이미지 템플릿이 성공적으로 생성되었습니다.\n\n"
                f"이름: {template_name}\n"
                f"크기: {rect.width()} x {rect.height()}\n"
                f"파일: {file_path.name}",
            )

            # 다이얼로그 닫기
            self.close()

        except Exception as e:
            logger.error(f"캡쳐 및 저장 실패: {e}")
            QMessageBox.critical(self, "오류", f"캡쳐를 저장할 수 없습니다: {e}")

    def closeEvent(self, event):
        """다이얼로그 닫기 시"""
        # 오버레이가 있으면 닫기
        if self.overlay:
            self.overlay.close()
            self.overlay = None

        event.accept()

    def keyPressEvent(self, event):
        """키 이벤트"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)
