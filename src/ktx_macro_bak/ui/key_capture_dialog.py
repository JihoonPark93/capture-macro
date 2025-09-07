"""
키 입력 캡처 다이얼로그
"""

from typing import List

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent


class KeyCaptureDialog(QDialog):
    """키 입력 캡처 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.captured_keys: List[str] = []
        self.is_capturing = False

        self.init_ui()
        self.start_capture()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("키 입력 캡처")
        self.setModal(True)
        self.setMinimumSize(300, 200)

        # 메인 레이아웃
        layout = QVBoxLayout(self)

        # 안내 메시지
        self.info_label = QLabel(
            "키 입력을 시작합니다.\n\n"
            "원하는 키 조합을 누르세요.\n"
            "(예: Ctrl+C, Alt+Tab)\n\n"
            "입력이 완료되면 Enter 키를 누르거나 확인 버튼을 클릭하세요."
        )
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(
            "font-size: 12px; padding: 20px; background-color: #f8f9fa; border-radius: 5px;"
        )
        layout.addWidget(self.info_label)

        # 캡처된 키 표시
        self.keys_label = QLabel("캡처된 키: 없음")
        self.keys_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.keys_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #007bff; padding: 10px;"
        )
        layout.addWidget(self.keys_label)

        # 버튼 레이아웃
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton("초기화")
        self.clear_btn.clicked.connect(self.clear_keys)
        button_layout.addWidget(self.clear_btn)

        self.ok_btn = QPushButton("확인")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        # 키보드 포커스 설정
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def start_capture(self):
        """키 캡처 시작"""
        self.is_capturing = True
        self.captured_keys = []
        self.update_keys_display()

    def clear_keys(self):
        """캡처된 키 초기화"""
        self.captured_keys = []
        self.update_keys_display()

    def update_keys_display(self):
        """캡처된 키 표시 업데이트"""
        if self.captured_keys:
            keys_text = " + ".join(self.captured_keys)
            self.keys_label.setText(f"캡처된 키: {keys_text}")
        else:
            self.keys_label.setText("캡처된 키: 없음")

    def keyPressEvent(self, event: QKeyEvent):
        """키 입력 이벤트 처리"""
        if not self.is_capturing:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()
        # PyQt6에서는 modifiers가 Qt.KeyboardModifiers 타입임

        # Enter 키는 확인으로 처리
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.accept()
            return

        # Escape 키는 취소로 처리
        if key == Qt.Key.Key_Escape:
            self.reject()
            return

        # Backspace 키는 마지막 키 삭제
        if key == Qt.Key.Key_Backspace:
            if self.captured_keys:
                self.captured_keys.pop()
                self.update_keys_display()
            return

        # 이미 캡처된 키인지 확인 (중복 방지)
        key_name = self._key_to_name(key, modifiers, event)
        if key_name and key_name not in self.captured_keys:
            self.captured_keys.append(key_name)
            self.update_keys_display()

        # 이벤트 소비 (기본 동작 방지)
        event.accept()

    def _key_to_name(self, key: int, modifiers, event: QKeyEvent) -> str:
        """키 코드를 이름으로 변환"""
        # 특수 키 매핑
        special_keys = {
            Qt.Key.Key_Space: "Space",
            Qt.Key.Key_Tab: "Tab",
            Qt.Key.Key_Return: "Enter",
            Qt.Key.Key_Enter: "Enter",
            Qt.Key.Key_Backspace: "Backspace",
            Qt.Key.Key_Delete: "Delete",
            Qt.Key.Key_Insert: "Insert",
            Qt.Key.Key_Home: "Home",
            Qt.Key.Key_End: "End",
            Qt.Key.Key_PageUp: "PageUp",
            Qt.Key.Key_PageDown: "PageDown",
            Qt.Key.Key_Up: "Up",
            Qt.Key.Key_Down: "Down",
            Qt.Key.Key_Left: "Left",
            Qt.Key.Key_Right: "Right",
            Qt.Key.Key_F1: "F1",
            Qt.Key.Key_F2: "F2",
            Qt.Key.Key_F3: "F3",
            Qt.Key.Key_F4: "F4",
            Qt.Key.Key_F5: "F5",
            Qt.Key.Key_F6: "F6",
            Qt.Key.Key_F7: "F7",
            Qt.Key.Key_F8: "F8",
            Qt.Key.Key_F9: "F9",
            Qt.Key.Key_F10: "F10",
            Qt.Key.Key_F11: "F11",
            Qt.Key.Key_F12: "F12",
        }

        # 함수 키
        if key in special_keys:
            key_name = special_keys[key]
        else:
            # 일반 키 - 현재 이벤트에서 텍스트 가져오기
            # QKeyEvent 생성 대신 현재 이벤트 사용
            key_name = event.text()
            if not key_name:
                return None

        # 수정자 키들
        modifier_names = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            modifier_names.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            modifier_names.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifier_names.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            modifier_names.append("Meta")

        # 수정자 키와 함께 반환
        if modifier_names:
            return " + ".join(modifier_names + [key_name])

        return key_name

    def closeEvent(self, event):
        """다이얼로그 닫힘 이벤트"""
        self.is_capturing = False
        super().closeEvent(event)
