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


class MousePositionOverlay(QWidget):
    """마우스 위치 캡쳐를 위한 전체 화면 오버레이"""

    position_selected = pyqtSignal(QPoint)  # 선택된 위치 신호
    capture_cancelled = pyqtSignal()  # 캡쳐 취소 신호

    def __init__(self, screenshot: QPixmap):
        super().__init__()

        self.screenshot = screenshot
        self.cursor_pos = QPoint()

        # 스케일 팩터 계산 (스크린샷 크기 vs 실제 화면 크기)
        screen = QApplication.primaryScreen()
        self.screen_geometry = screen.geometry()
        self.screenshot_size = screenshot.size()

        # 스케일 팩터 계산
        self.scale_x = self.screenshot_size.width() / self.screen_geometry.width()
        self.scale_y = self.screenshot_size.height() / self.screen_geometry.height()

        print(
            f"[MousePositionOverlay] Screen: {self.screen_geometry.width()}x{self.screen_geometry.height()}"
        )
        print(
            f"[MousePositionOverlay] Screenshot: {self.screenshot_size.width()}x{self.screenshot_size.height()}"
        )
        print(
            f"[MousePositionOverlay] Scale factors: x={self.scale_x:.3f}, y={self.scale_y:.3f}"
        )

        # 부모 없는 독립 윈도우로 설정
        self.setParent(None)

        # 전체 화면 크기로 설정
        self.setGeometry(self.screen_geometry)

        # 윈도우 플래그 설정
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
            | Qt.WindowType.X11BypassWindowManagerHint
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

        # 윈도우 표시
        self.show()
        self.raise_()
        self.activateWindow()

        # 이벤트 처리 실행
        QApplication.processEvents()

        # 포커스 설정
        self.setFocus(Qt.FocusReason.OtherFocusReason)

        # 입력 캡처 설정을 지연 실행
        QTimer.singleShot(100, self._force_focus)
        QTimer.singleShot(150, self._setup_input_capture)

    def _force_focus(self):
        """강제 포커스 설정"""
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def _setup_input_capture(self):
        """입력 장치 캡처 설정"""
        try:
            self.grabMouse()
            self.grabKeyboard()
        except Exception as e:
            logger.warning(f"입력 장치 캡처 실패: {e}")
            self._setup_event_filter()

    def _setup_event_filter(self):
        """이벤트 필터 설정 (그랩 실패 시 대안)"""
        try:
            QApplication.instance().installEventFilter(self)
        except Exception as e:
            logger.warning(f"이벤트 필터 설정 실패: {e}")

    def eventFilter(self, obj, event):
        """전역 이벤트 필터"""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QMouseEvent, QKeyEvent

        if isinstance(event, QMouseEvent):
            if event.type() == QEvent.Type.MouseButtonPress:
                self.mousePressEvent(event)
                return True
            elif event.type() == QEvent.Type.MouseMove:
                self.mouseMoveEvent(event)
                return True
        elif isinstance(event, QKeyEvent):
            if event.type() == QEvent.Type.KeyPress:
                self.keyPressEvent(event)
                return True

        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        """윈도우 닫기 시 리소스 정리"""
        try:
            self.releaseMouse()
            self.releaseKeyboard()
            QApplication.instance().removeEventFilter(self)
        except Exception as e:
            logger.warning(f"리소스 정리 실패: {e}")
        event.accept()

    def keyPressEvent(self, event):
        """키보드 이벤트 처리"""
        if event.key() == Qt.Key.Key_Escape:
            try:
                self.releaseMouse()
                self.releaseKeyboard()
                QApplication.instance().removeEventFilter(self)
            except Exception as e:
                logger.warning(f"ESC 시 입력 장치 해제 실패: {e}")

            self.capture_cancelled.emit()
        event.accept()

    def paintEvent(self, event):
        """그리기 이벤트"""
        painter = QPainter(self)
        try:
            # 전체 화면에 원본 스크린샷 표시
            painter.drawPixmap(self.rect(), self.screenshot, self.screenshot.rect())

            # 반투명 오버레이
            overlay_color = QColor(0, 0, 0, 64)
            painter.fillRect(self.rect(), overlay_color)

            # 십자선 그리기
            self.draw_crosshair(painter)

            # 도움말 텍스트 표시
            self.draw_help_text(painter)

        finally:
            painter.end()

    def draw_crosshair(self, painter: QPainter):
        """십자선 그리기"""
        if self.cursor_pos.isNull():
            return

        # 십자선 색상 설정
        pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)

        # 세로선
        painter.drawLine(self.cursor_pos.x(), 0, self.cursor_pos.x(), self.height())
        # 가로선
        painter.drawLine(0, self.cursor_pos.y(), self.width(), self.cursor_pos.y())

        # 중심점 원
        painter.setBrush(QColor(255, 0, 0))
        painter.drawEllipse(self.cursor_pos.x() - 3, self.cursor_pos.y() - 3, 6, 6)

    def draw_help_text(self, painter: QPainter):
        """도움말 텍스트 표시"""
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))

        help_text = "클릭할 위치를 선택하세요 (ESC: 취소)"

        # 좌표 정보 텍스트 (실제 스크린샷 좌표 표시)
        if not self.cursor_pos.isNull():
            # 위젯 좌표와 실제 스크린샷 좌표 모두 표시
            screenshot_pos = self._convert_to_screenshot_coordinates(self.cursor_pos)
            coord_text = f"화면: ({self.cursor_pos.x()}, {self.cursor_pos.y()}) → 실제: ({screenshot_pos.x()}, {screenshot_pos.y()})"
            help_text += f"\n{coord_text}"

        # 텍스트 배경
        text_rect = painter.fontMetrics().boundingRect(help_text)
        bg_rect = QRect(10, 10, text_rect.width() + 20, text_rect.height() + 20)
        painter.fillRect(bg_rect, QColor(0, 0, 0, 180))

        # 텍스트 그리기
        painter.drawText(20, 30, help_text)

    def _convert_to_screenshot_coordinates(self, widget_pos: QPoint) -> QPoint:
        """위젯 좌표를 스크린샷 좌표로 변환"""
        # 위젯 좌표 (화면 표시 좌표)를 실제 스크린샷 좌표로 변환
        screenshot_x = int(widget_pos.x() * self.scale_x)
        screenshot_y = int(widget_pos.y() * self.scale_y)

        print(
            f"[MousePositionOverlay] 좌표 변환: 위젯({widget_pos.x()}, {widget_pos.y()}) -> 스크린샷({screenshot_x}, {screenshot_y})"
        )

        return QPoint(screenshot_x, screenshot_y)

    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트"""
        self.cursor_pos = event.pos()
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        """마우스 클릭 이벤트"""
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                self.releaseMouse()
                self.releaseKeyboard()
                QApplication.instance().removeEventFilter(self)
            except Exception as e:
                logger.warning(f"입력 장치 해제 실패: {e}")

            # 위젯 좌표를 실제 스크린샷 좌표로 변환하여 신호 발송
            screenshot_pos = self._convert_to_screenshot_coordinates(event.pos())
            self.position_selected.emit(screenshot_pos)
        event.accept()


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
                padding = 3
                draw_rect = self.selection_rect.adjusted(
                    -padding, -padding, padding, padding
                )

                # 선택 영역을 제외한 나머지 영역에만 오버레이 적용
                # 선택 영역 위쪽
                if draw_rect.top() > 0:
                    top_rect = QRect(0, 0, self.width(), draw_rect.top())
                    painter.fillRect(top_rect, overlay_color)

                # 선택 영역 아래쪽
                if draw_rect.bottom() < self.height():
                    bottom_rect = QRect(
                        0,
                        draw_rect.bottom(),
                        self.width(),
                        self.height() - draw_rect.bottom(),
                    )
                    painter.fillRect(bottom_rect, overlay_color)

                # 선택 영역 왼쪽
                if draw_rect.left() > 0:
                    left_rect = QRect(
                        0,
                        draw_rect.top(),
                        draw_rect.left(),
                        draw_rect.height(),
                    )
                    painter.fillRect(left_rect, overlay_color)

                # 선택 영역 오른쪽
                if draw_rect.right() < self.width():
                    right_rect = QRect(
                        draw_rect.right(),
                        draw_rect.top(),
                        self.width() - draw_rect.right(),
                        draw_rect.height(),
                    )
                    painter.fillRect(right_rect, overlay_color)

                # 선택 영역 테두리 그리기
                # FIXME: 빨간 테두리가 캡쳐되는 문제 수정 테두리 그리기 전 패딩 추가
                pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)
                painter.setPen(pen)
                painter.drawRect(draw_rect)

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


class MacroStatusOverlay(QWidget):
    """매크로 동작 중 상태를 표시하는 오버레이"""

    def __init__(self):
        super().__init__()

        # 부모 없는 독립 윈도우로 설정
        self.setParent(None)

        # 윈도우 플래그 설정
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
            | Qt.WindowType.X11BypassWindowManagerHint
        )

        # 투명도 및 배경 설정
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # 포커스 정책 설정 (이벤트를 받지 않도록)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # 크기 설정 (고정 크기)
        self.setFixedSize(300, 120)

        # 화면 우측 하단에 위치 설정
        self._position_window()

        # 윈도우 표시
        self.show()
        self.raise_()

    def _position_window(self):
        """화면 우측 하단에 윈도우 위치 설정"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        # 우측 하단 좌표 계산
        x = screen_geometry.width() - self.width() - 20  # 오른쪽에서 20px 여백
        y = screen_geometry.height() - self.height() - 20  # 아래쪽에서 20px 여백

        self.move(x, y)

    def paintEvent(self, event):
        """그리기 이벤트"""
        painter = QPainter(self)
        try:
            # 검은 배경 그리기 (반투명)
            bg_color = QColor(0, 0, 0, 200)  # 검은색, 200/255 투명도
            painter.fillRect(self.rect(), bg_color)

            # 테두리 그리기 (빨간색)
            pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

            # 폰트 설정
            font = QFont()
            font.setPointSize(18)
            font.setBold(True)
            painter.setFont(font)

            # 빨간 글씨로 텍스트 그리기
            painter.setPen(QColor(255, 0, 0))

            # 메인 텍스트
            main_text = "매크로 동작 중..."
            painter.drawText(20, 35, main_text)

            # 중단 방법 안내 텍스트
            font.setPointSize(16)
            font.setBold(False)
            painter.setFont(font)

            stop_text = "중단: F11"
            painter.drawText(20, 55, stop_text)

        finally:
            painter.end()

    def update_status(self, is_running: bool):
        """매크로 상태 업데이트"""
        if is_running:
            self.show()
            self.raise_()
        else:
            self.hide()

    def closeEvent(self, event):
        """윈도우 닫기 시 정리"""
        event.accept()
