"""
화면 캡쳐 관련 컴포넌트들

ScreenOverlay: 화면 전체를 덮는 오버레이로 영역 선택 처리
"""

import logging

from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
)
from PyQt6.QtCore import Qt, QRect, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont

logger = logging.getLogger(__name__)


class ScreenOverlay(QWidget):
    """전체 화면을 덮는 오버레이"""

    selection_completed = pyqtSignal(QRect)
    capture_cancelled = pyqtSignal()  # 캡쳐 취소 신호

    def __init__(self, screenshot: QPixmap):
        super().__init__()

        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_selecting = False
        self.selection_rect = QRect()

        # 미리 캡쳐된 스크린샷 사용
        self.screenshot = screenshot

        # 디버그: 스크린샷 정보 출력
        print(f"[DEBUG] Screenshot size: {screenshot.size()}")
        print(f"[DEBUG] Screenshot device pixel ratio: {screenshot.devicePixelRatio()}")
        print(f"[DEBUG] Screen geometry: {QApplication.primaryScreen().geometry()}")

        # 부모 없는 독립 윈도우로 설정
        self.setParent(None)

        # 전체 화면 크기로 설정
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        # 윈도우 플래그 설정 - 이벤트 수신을 위한 최적화
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window  # Window 타입으로 변경 (Tool보다 이벤트 처리에 안정적)
            | Qt.WindowType.X11BypassWindowManagerHint  # 윈도우 매니저 우회 (Linux/X11)
        )

        # 투명도 및 배경 설정
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # 포커스 정책 설정
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 커서 설정
        self.setCursor(Qt.CursorShape.CrossCursor)

        # 마우스 추적 활성화
        self.setMouseTracking(True)

        # 위젯이 마우스 이벤트를 받을 수 있도록 설정
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        print(f"[DEBUG] ScreenOverlay: Before show - geometry: {self.geometry()}")

        # 윈도우 표시
        self.show()
        self.raise_()
        self.activateWindow()

        # 이벤트 처리 실행
        QApplication.processEvents()

        # 포커스 설정 (여러 번 시도)
        self.setFocus(Qt.FocusReason.OtherFocusReason)

        # 좀 더 강력한 포커스 설정과 마우스 그랩을 지연 실행
        QTimer.singleShot(100, self._force_focus)
        QTimer.singleShot(150, self._setup_input_capture)

        print(f"[DEBUG] ScreenOverlay: After show - geometry: {self.geometry()}")
        print(f"[DEBUG] ScreenOverlay: window flags = {self.windowFlags()}")
        print(f"[DEBUG] ScreenOverlay: is visible = {self.isVisible()}")
        print(f"[DEBUG] ScreenOverlay: has focus = {self.hasFocus()}")
        print(f"[DEBUG] ScreenOverlay: is active = {self.isActiveWindow()}")

    def _force_focus(self):
        """강제 포커스 설정"""
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

        print(f"[DEBUG] _force_focus: has focus = {self.hasFocus()}")
        print(f"[DEBUG] _force_focus: is active = {self.isActiveWindow()}")

    def _setup_input_capture(self):
        """입력 장치 캡처 설정 (지연 실행)"""
        try:
            # 마우스 그랩 시도
            self.grabMouse()
            print(f"[DEBUG] Mouse grab successful")

            # 키보드 그랩 시도
            self.grabKeyboard()
            print(f"[DEBUG] Keyboard grab successful")

        except Exception as e:
            logger.warning(f"입력 장치 캡처 실패: {e}")
            print(f"[DEBUG] Input capture failed: {e}")

            # 그랩 실패 시 대안으로 이벤트 필터 설정
            self._setup_event_filter()

    def _setup_event_filter(self):
        """이벤트 필터 설정 (그랩 실패 시 대안)"""
        try:
            # 전역 이벤트 필터 설정
            from PyQt6.QtWidgets import QApplication

            QApplication.instance().installEventFilter(self)
            print(f"[DEBUG] Event filter installed as fallback")
        except Exception as e:
            logger.warning(f"이벤트 필터 설정 실패: {e}")

    def eventFilter(self, obj, event):
        """전역 이벤트 필터 (그랩 실패 시 대안)"""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QMouseEvent, QKeyEvent

        # 마우스 이벤트를 이 위젯으로 전달
        if isinstance(event, QMouseEvent):
            if event.type() == QEvent.Type.MouseButtonPress:
                self.mousePressEvent(event)
                return True
            elif event.type() == QEvent.Type.MouseMove:
                self.mouseMoveEvent(event)
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self.mouseReleaseEvent(event)
                return True

        # 키보드 이벤트를 이 위젯으로 전달
        elif isinstance(event, QKeyEvent):
            if event.type() == QEvent.Type.KeyPress:
                self.keyPressEvent(event)
                return True

        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """윈도우 닫기 시 리소스 정리"""
        try:
            # 입력 장치 해제
            self.releaseMouse()
            self.releaseKeyboard()

            # 이벤트 필터 제거
            from PyQt6.QtWidgets import QApplication

            QApplication.instance().removeEventFilter(self)

            print(f"[DEBUG] Resources cleaned up on close")
        except Exception as e:
            logger.warning(f"리소스 정리 실패: {e}")
        event.accept()

    def keyPressEvent(self, event):
        """키보드 이벤트 처리"""
        print(f"[DEBUG] Key press detected: {event.key()}")

        if event.key() == Qt.Key.Key_Escape:
            # 마우스 캡처 해제
            try:
                self.releaseMouse()
                self.releaseKeyboard()

                # 이벤트 필터 제거
                from PyQt6.QtWidgets import QApplication

                QApplication.instance().removeEventFilter(self)

                print(f"[DEBUG] ESC pressed - input devices released")
            except Exception as e:
                logger.warning(f"ESC 시 입력 장치 해제 실패: {e}")

            # 캡쳐 취소 신호 발송
            self.capture_cancelled.emit()
        event.accept()

    def paintEvent(self, event):
        """그리기 이벤트 (QPainter 리소스 안전 관리)"""
        painter = QPainter(self)
        try:
            # 전체 화면에 원본 스크린샷 표시
            painter.drawPixmap(self.rect(), self.screenshot, self.screenshot.rect())

            # 선택 영역이 있으면 선택 영역 외부를 어둡게 처리
            if not self.selection_rect.isEmpty():
                # 전체 화면을 어둡게 오버레이
                overlay_color = QColor(0, 0, 0, 128)  # 반투명 검은색

                # 선택 영역을 제외한 나머지 영역에만 오버레이 적용
                # 선택 영역 위쪽
                if self.selection_rect.top() > 0:
                    top_rect = QRect(0, 0, self.width(), self.selection_rect.top())
                    painter.fillRect(top_rect, overlay_color)

                # 선택 영역 아래쪽
                if self.selection_rect.bottom() < self.height():
                    bottom_rect = QRect(
                        0,
                        self.selection_rect.bottom(),
                        self.width(),
                        self.height() - self.selection_rect.bottom(),
                    )
                    painter.fillRect(bottom_rect, overlay_color)

                # 선택 영역 왼쪽
                if self.selection_rect.left() > 0:
                    left_rect = QRect(
                        0,
                        self.selection_rect.top(),
                        self.selection_rect.left(),
                        self.selection_rect.height(),
                    )
                    painter.fillRect(left_rect, overlay_color)

                # 선택 영역 오른쪽
                if self.selection_rect.right() < self.width():
                    right_rect = QRect(
                        self.selection_rect.right(),
                        self.selection_rect.top(),
                        self.width() - self.selection_rect.right(),
                        self.selection_rect.height(),
                    )
                    painter.fillRect(right_rect, overlay_color)

                # 선택 영역 테두리 그리기
                pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)
                painter.setPen(pen)
                painter.drawRect(self.selection_rect)

                # 선택 영역 정보 표시
                self.draw_selection_info(painter)
            else:
                # 선택 영역이 없으면 전체를 살짝 어둡게 처리
                overlay_color = QColor(0, 0, 0, 64)  # 더 투명한 검은색
                painter.fillRect(self.rect(), overlay_color)
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
        print(f"[DEBUG] Mouse press detected: {event.button()} at {event.pos()}")

        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.is_selecting = True
            self.selection_rect = QRect()
            self.update()
            print(f"[DEBUG] Selection started at {self.start_point}")
        event.accept()

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
        event.accept()

    def mouseReleaseEvent(self, event):
        """마우스 릴리즈 이벤트"""
        print(f"[DEBUG] Mouse release detected: {event.button()} at {event.pos()}")

        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False

            # 최소 크기 검사
            if self.selection_rect.width() > 10 and self.selection_rect.height() > 10:
                print(f"[DEBUG] Selection completed: {self.selection_rect}")

                # 입력 장치 해제 (선택 완료 전)
                try:
                    self.releaseMouse()
                    self.releaseKeyboard()

                    # 이벤트 필터 제거
                    from PyQt6.QtWidgets import QApplication

                    QApplication.instance().removeEventFilter(self)
                except Exception as e:
                    logger.warning(f"입력 장치 해제 실패: {e}")

                # 선택 완료 신호 발송
                self.selection_completed.emit(self.selection_rect)
            else:
                # 너무 작은 선택은 무시
                print(f"[DEBUG] Selection too small: {self.selection_rect}")
                self.selection_rect = QRect()
                self.update()
        event.accept()
