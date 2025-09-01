"""
액션 편집기 다이얼로그
"""

import uuid
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QMessageBox,
    QFormLayout,
    QGroupBox,
    QTextEdit,
    QWidget,
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer

from ..models.macro_models import MacroAction, ActionType


class ActionEditor(QDialog):
    """액션 편집기 다이얼로그"""

    action_saved = pyqtSignal(object)  # MacroAction

    def __init__(self, parent=None, action: Optional[MacroAction] = None):
        super().__init__(parent)

        self.action = action
        self.is_edit_mode = action is not None

        # UI 요소들
        self.action_type_combo: Optional[QComboBox] = None
        self.settings_group: Optional[QGroupBox] = None
        self.settings_layout: Optional[QVBoxLayout] = None

        # 메모리 관리를 위한 설정
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.init_ui()
        self.setup_connections()

        if self.is_edit_mode:
            # UI 업데이트를 다음 이벤트 루프에서 실행
            QTimer.singleShot(0, self.load_action_data)

    def init_ui(self):
        """UI 초기화"""
        title = "액션 편집" if self.is_edit_mode else "액션 추가"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # 액션 타입 선택
        type_group = QGroupBox("액션 타입")
        type_layout = QFormLayout(type_group)

        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(
            [
                "이미지 찾기",
                "클릭",
                "더블클릭",
                "우클릭",
                "텍스트 입력",
                "키 입력",
                "대기",
                "텔레그램 전송",
            ]
        )
        type_layout.addRow("타입:", self.action_type_combo)
        layout.addWidget(type_group)

        # 액션 설정
        self.settings_group = QGroupBox("액션 설정")
        self.settings_layout = QVBoxLayout(self.settings_group)
        layout.addWidget(self.settings_group)

        # 버튼들
        button_layout = QHBoxLayout()

        save_btn = QPushButton("저장")
        save_btn.clicked.connect(self.save_action)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def setup_connections(self):
        """신호 연결"""
        self.action_type_combo.currentTextChanged.connect(self.on_action_type_changed)

    def on_action_type_changed(self):
        """액션 타입 변경 시"""
        self.update_settings_ui()

    def update_settings_ui(self):
        """설정 UI 업데이트"""
        # 기존 위젯들 안전하게 제거
        for i in reversed(range(self.settings_layout.count())):
            child = self.settings_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
                self.settings_layout.removeWidget(child)

        action_type = self.get_selected_action_type()
        if not action_type:
            return

        form_layout = QFormLayout()

        if action_type == ActionType.FIND_IMAGE:
            # 이미지 찾기는 별도 구현 필요
            label = QLabel("이미지 템플릿은 화면 캡쳐 기능을 사용하세요")
            form_layout.addRow(label)

        elif action_type in [
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
        ]:
            # 클릭 위치 설정
            self.click_x_spin = QSpinBox()
            self.click_x_spin.setRange(0, 9999)
            form_layout.addRow("X 좌표:", self.click_x_spin)

            self.click_y_spin = QSpinBox()
            self.click_y_spin.setRange(0, 9999)
            form_layout.addRow("Y 좌표:", self.click_y_spin)

            # 이미지 템플릿 사용 여부
            self.use_image_check = QCheckBox("이미지 템플릿 사용")
            form_layout.addRow(self.use_image_check)

            self.image_template_combo = QComboBox()
            self.image_template_combo.setEnabled(False)
            form_layout.addRow("이미지 템플릿:", self.image_template_combo)

            # 이미지 템플릿 목록 로드
            self.load_image_templates()

            self.use_image_check.toggled.connect(self.on_use_image_toggled)

        elif action_type == ActionType.TYPE_TEXT:
            self.text_input = QTextEdit()
            self.text_input.setMaximumHeight(100)
            form_layout.addRow("입력할 텍스트:", self.text_input)

        elif action_type == ActionType.KEY_PRESS:
            self.key_input = QLineEdit()
            self.key_input.setPlaceholderText("예: Ctrl+C, Alt+Tab, Enter")
            form_layout.addRow("키 조합:", self.key_input)

        elif action_type == ActionType.WAIT:
            self.wait_seconds = QDoubleSpinBox()
            self.wait_seconds.setRange(0.1, 60.0)
            self.wait_seconds.setValue(1.0)
            self.wait_seconds.setSuffix(" 초")
            form_layout.addRow("대기 시간:", self.wait_seconds)

        elif action_type == ActionType.SEND_TELEGRAM:
            self.telegram_message = QTextEdit()
            self.telegram_message.setMaximumHeight(100)
            form_layout.addRow("메시지:", self.telegram_message)

        # 공통 설정
        self.enabled_check = QCheckBox("활성화")
        self.enabled_check.setChecked(True)
        form_layout.addRow(self.enabled_check)

        # 메모리 누수 방지를 위해 제대로 된 부모-자식 관계 설정
        widget = QWidget(self.settings_group)
        widget.setLayout(form_layout)
        self.settings_layout.addWidget(widget)

    def load_image_templates(self):
        """이미지 템플릿 목록 로드"""
        if hasattr(self.parent(), "engine"):
            engine = self.parent().engine
            self.image_template_combo.clear()
            self.image_template_combo.addItem("선택하세요", "")

            for template in engine.config.image_templates:
                self.image_template_combo.addItem(template.name, template.id)

    def on_use_image_toggled(self, checked):
        """이미지 템플릿 사용 토글"""
        if hasattr(self, "image_template_combo"):
            self.image_template_combo.setEnabled(checked)
            if hasattr(self, "click_x_spin"):
                self.click_x_spin.setEnabled(not checked)
            if hasattr(self, "click_y_spin"):
                self.click_y_spin.setEnabled(not checked)

    def get_selected_action_type(self) -> Optional[ActionType]:
        """선택된 액션 타입 반환"""
        type_map = {
            "이미지 찾기": ActionType.FIND_IMAGE,
            "클릭": ActionType.CLICK,
            "더블클릭": ActionType.DOUBLE_CLICK,
            "우클릭": ActionType.RIGHT_CLICK,
            "텍스트 입력": ActionType.TYPE_TEXT,
            "키 입력": ActionType.KEY_PRESS,
            "대기": ActionType.WAIT,
            "텔레그램 전송": ActionType.SEND_TELEGRAM,
        }

        text = self.action_type_combo.currentText()
        return type_map.get(text)

    def load_action_data(self):
        """액션 데이터 로드 (편집 모드)"""
        if not self.action:
            return

        # 액션 타입 설정
        type_map = {
            ActionType.FIND_IMAGE: "이미지 찾기",
            ActionType.CLICK: "클릭",
            ActionType.DOUBLE_CLICK: "더블클릭",
            ActionType.RIGHT_CLICK: "우클릭",
            ActionType.TYPE_TEXT: "텍스트 입력",
            ActionType.KEY_PRESS: "키 입력",
            ActionType.WAIT: "대기",
            ActionType.SEND_TELEGRAM: "텔레그램 전송",
        }

        type_text = type_map.get(self.action.action_type, "")
        if type_text:
            index = self.action_type_combo.findText(type_text)
            if index >= 0:
                self.action_type_combo.setCurrentIndex(index)

        # UI 업데이트 후 데이터 로드
        self.update_settings_ui()

        # 액션별 데이터 로드
        if self.action.action_type in [
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
        ]:
            if hasattr(self, "click_x_spin") and self.action.click_position:
                self.click_x_spin.setValue(self.action.click_position[0])
                self.click_y_spin.setValue(self.action.click_position[1])

            if hasattr(self, "use_image_check") and self.action.image_template_id:
                self.use_image_check.setChecked(True)
                # 템플릿 선택
                for i in range(self.image_template_combo.count()):
                    if (
                        self.image_template_combo.itemData(i)
                        == self.action.image_template_id
                    ):
                        self.image_template_combo.setCurrentIndex(i)
                        break

        elif self.action.action_type == ActionType.TYPE_TEXT:
            if hasattr(self, "text_input"):
                self.text_input.setPlainText(self.action.text_input or "")

        elif self.action.action_type == ActionType.KEY_PRESS:
            if hasattr(self, "key_input"):
                keys = self.action.key_combination or []
                self.key_input.setText("+".join(keys))

        elif self.action.action_type == ActionType.WAIT:
            if hasattr(self, "wait_seconds"):
                self.wait_seconds.setValue(self.action.wait_seconds or 1.0)

        elif self.action.action_type == ActionType.SEND_TELEGRAM:
            if hasattr(self, "telegram_message"):
                self.telegram_message.setPlainText(self.action.telegram_message or "")

        # 활성화 상태
        if hasattr(self, "enabled_check"):
            self.enabled_check.setChecked(self.action.enabled)

    def save_action(self):
        """액션 저장"""
        action_type = self.get_selected_action_type()
        if not action_type:
            QMessageBox.warning(self, "경고", "액션 타입을 선택하세요.")
            return

        # 새 액션 생성 또는 기존 액션 업데이트
        if self.is_edit_mode:
            action = self.action
        else:
            action = MacroAction(id=str(uuid.uuid4()), action_type=action_type)

        action.action_type = action_type
        action.enabled = (
            self.enabled_check.isChecked() if hasattr(self, "enabled_check") else True
        )

        # 액션별 데이터 저장
        if action_type in [
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
        ]:
            if hasattr(self, "use_image_check") and self.use_image_check.isChecked():
                # 이미지 템플릿 사용
                template_id = self.image_template_combo.currentData()
                if not template_id:
                    QMessageBox.warning(self, "경고", "이미지 템플릿을 선택하세요.")
                    return
                action.image_template_id = template_id
                action.click_position = None
            else:
                # 좌표 사용
                if hasattr(self, "click_x_spin"):
                    action.click_position = (
                        self.click_x_spin.value(),
                        self.click_y_spin.value(),
                    )
                action.image_template_id = None

        elif action_type == ActionType.TYPE_TEXT:
            if hasattr(self, "text_input"):
                text = self.text_input.toPlainText().strip()
                if not text:
                    QMessageBox.warning(self, "경고", "입력할 텍스트를 작성하세요.")
                    return
                action.text_input = text

        elif action_type == ActionType.KEY_PRESS:
            if hasattr(self, "key_input"):
                key_text = self.key_input.text().strip()
                if not key_text:
                    QMessageBox.warning(self, "경고", "키 조합을 입력하세요.")
                    return
                action.key_combination = [k.strip() for k in key_text.split("+")]

        elif action_type == ActionType.WAIT:
            if hasattr(self, "wait_seconds"):
                action.wait_seconds = self.wait_seconds.value()

        elif action_type == ActionType.SEND_TELEGRAM:
            if hasattr(self, "telegram_message"):
                message = self.telegram_message.toPlainText().strip()
                if not message:
                    QMessageBox.warning(self, "경고", "전송할 메시지를 작성하세요.")
                    return
                action.telegram_message = message

        elif action_type == ActionType.FIND_IMAGE:
            QMessageBox.information(
                self,
                "안내",
                "이미지 찾기 액션은 화면 캡쳐 기능을 통해 이미지 템플릿을 먼저 생성하세요.",
            )
            return

        # 액션 저장 신호 발송
        self.action_saved.emit(action)
        self.accept()
