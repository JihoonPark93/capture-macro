"""
매크로 시퀀스 편집기
"""

import uuid
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QMessageBox,
    QComboBox,
    QTabWidget,
    QWidget,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ..core.macro_engine import MacroEngine
from ..models.macro_models import MacroSequence, MacroAction, ActionType


class SequenceEditor(QDialog):
    """시퀀스 편집기 다이얼로그"""

    sequence_saved = pyqtSignal(str)  # sequence_id

    def __init__(self, parent=None, engine: MacroEngine = None):
        super().__init__(parent)

        self.engine = engine
        self.current_sequence: Optional[MacroSequence] = None
        self.is_new_sequence = False

        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("시퀀스 편집기")
        self.setModal(True)
        self.resize(700, 600)

        layout = QVBoxLayout(self)

        # 시퀀스 기본 정보
        info_group = QGroupBox("시퀀스 정보")
        info_layout = QVBoxLayout(info_group)

        # 이름
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("이름:"))

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("시퀀스 이름을 입력하세요")
        name_layout.addWidget(self.name_edit)

        info_layout.addLayout(name_layout)

        # 설명
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("설명:"))

        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("시퀀스 설명 (선택사항)")
        desc_layout.addWidget(self.description_edit)

        info_layout.addLayout(desc_layout)

        # 활성화 및 루프 설정
        settings_layout = QHBoxLayout()

        self.enabled_checkbox = QCheckBox("활성화")
        self.enabled_checkbox.setChecked(True)
        settings_layout.addWidget(self.enabled_checkbox)

        settings_layout.addWidget(QLabel("루프 횟수:"))

        self.loop_count_spin = QSpinBox()
        self.loop_count_spin.setRange(1, 1000)
        self.loop_count_spin.setValue(1)
        settings_layout.addWidget(self.loop_count_spin)

        settings_layout.addWidget(QLabel("루프 지연:"))

        self.loop_delay_spin = QDoubleSpinBox()
        self.loop_delay_spin.setRange(0.0, 60.0)
        self.loop_delay_spin.setSingleStep(0.1)
        self.loop_delay_spin.setSuffix("초")
        self.loop_delay_spin.setValue(1.0)
        settings_layout.addWidget(self.loop_delay_spin)

        settings_layout.addStretch()

        info_layout.addLayout(settings_layout)
        layout.addWidget(info_group)

        # 액션 목록
        action_group = QGroupBox("액션 목록")
        action_layout = QVBoxLayout(action_group)

        # 액션 리스트
        self.action_list = QListWidget()
        self.action_list.itemSelectionChanged.connect(self.on_action_selected)
        action_layout.addWidget(self.action_list)

        # 액션 버튼들
        action_btn_layout = QHBoxLayout()

        self.add_action_btn = QPushButton("액션 추가")
        self.add_action_btn.clicked.connect(self.add_action)
        action_btn_layout.addWidget(self.add_action_btn)

        self.edit_action_btn = QPushButton("편집")
        self.edit_action_btn.setEnabled(False)
        action_btn_layout.addWidget(self.edit_action_btn)

        self.delete_action_btn = QPushButton("삭제")
        self.delete_action_btn.setEnabled(False)
        self.delete_action_btn.clicked.connect(self.delete_action)
        action_btn_layout.addWidget(self.delete_action_btn)

        action_btn_layout.addStretch()

        self.move_up_btn = QPushButton("위로")
        self.move_up_btn.setEnabled(False)
        self.move_up_btn.clicked.connect(self.move_action_up)
        action_btn_layout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("아래로")
        self.move_down_btn.setEnabled(False)
        self.move_down_btn.clicked.connect(self.move_action_down)
        action_btn_layout.addWidget(self.move_down_btn)

        action_layout.addLayout(action_btn_layout)
        layout.addWidget(action_group)

        # 메인 버튼들
        button_layout = QHBoxLayout()

        self.save_button = QPushButton("저장")
        self.save_button.clicked.connect(self.save_sequence)
        button_layout.addWidget(self.save_button)

        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def new_sequence(self):
        """새 시퀀스 생성"""
        self.current_sequence = MacroSequence(
            id=str(uuid.uuid4()), name="", description=""
        )
        self.is_new_sequence = True
        self.setWindowTitle("새 시퀀스 생성")

        self.load_sequence_data()
        self.name_edit.setFocus()

    def edit_sequence(self, sequence_id: str):
        """기존 시퀀스 편집"""
        if not self.engine:
            return

        sequence = self.engine.config.get_macro_sequence(sequence_id)
        if not sequence:
            QMessageBox.warning(self, "경고", "시퀀스를 찾을 수 없습니다.")
            return

        self.current_sequence = sequence
        self.is_new_sequence = False
        self.setWindowTitle(f"시퀀스 편집: {sequence.name}")

        self.load_sequence_data()

    def load_sequence_data(self):
        """시퀀스 데이터 로드"""
        if not self.current_sequence:
            return

        # 기본 정보
        self.name_edit.setText(self.current_sequence.name)
        self.description_edit.setPlainText(self.current_sequence.description)
        self.enabled_checkbox.setChecked(self.current_sequence.enabled)
        self.loop_count_spin.setValue(self.current_sequence.loop_count)
        self.loop_delay_spin.setValue(self.current_sequence.loop_delay)

        # 액션 목록
        self.refresh_action_list()

    def refresh_action_list(self):
        """액션 목록 새로고침"""
        self.action_list.clear()

        if not self.current_sequence:
            return

        for i, action in enumerate(self.current_sequence.actions):
            item = QListWidgetItem()

            # 액션 설명 생성
            description = self.get_action_description(action)
            text = f"{i+1}. {action.action_type.value}"
            if description:
                text += f" - {description}"

            if not action.enabled:
                text += " (비활성화)"

            item.setText(text)
            item.setData(Qt.ItemDataRole.UserRole, action.id)

            # 비활성화된 액션은 회색으로 표시
            if not action.enabled:
                from PyQt6.QtGui import QColor

                item.setForeground(QColor(128, 128, 128))

            self.action_list.addItem(item)

    def get_action_description(self, action: MacroAction) -> str:
        """액션 설명 생성"""
        if action.action_type == ActionType.FIND_IMAGE:
            if self.engine and action.image_template_id:
                template = self.engine.config.get_image_template(
                    action.image_template_id
                )
                return template.name if template else "알 수 없는 템플릿"
            return "이미지 템플릿 없음"

        elif action.action_type in [
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
        ]:
            if action.click_position:
                return f"위치 ({action.click_position[0]}, {action.click_position[1]})"
            elif action.image_template_id and self.engine:
                template = self.engine.config.get_image_template(
                    action.image_template_id
                )
                return f"이미지: {template.name if template else '알 수 없음'}"
            return "위치 미지정"

        elif action.action_type == ActionType.TYPE_TEXT:
            text = action.text_input or ""
            return text[:30] + ("..." if len(text) > 30 else "")

        elif action.action_type == ActionType.KEY_PRESS:
            keys = action.key_combination or []
            return " + ".join(keys)

        elif action.action_type == ActionType.WAIT:
            return f"{action.wait_seconds}초"

        elif action.action_type == ActionType.SEND_TELEGRAM:
            msg = action.telegram_message or ""
            return msg[:30] + ("..." if len(msg) > 30 else "")

        return ""

    def on_action_selected(self):
        """액션 선택 시"""
        items = self.action_list.selectedItems()
        has_selection = len(items) > 0

        self.edit_action_btn.setEnabled(has_selection)
        self.delete_action_btn.setEnabled(has_selection)

        if has_selection:
            current_row = self.action_list.currentRow()
            total_rows = self.action_list.count()

            self.move_up_btn.setEnabled(current_row > 0)
            self.move_down_btn.setEnabled(current_row < total_rows - 1)
        else:
            self.move_up_btn.setEnabled(False)
            self.move_down_btn.setEnabled(False)

    def add_action(self):
        """액션 추가"""
        # 간단한 액션 타입 선택 다이얼로그
        action_types = [
            ("이미지 찾기", ActionType.FIND_IMAGE),
            ("클릭", ActionType.CLICK),
            ("더블클릭", ActionType.DOUBLE_CLICK),
            ("우클릭", ActionType.RIGHT_CLICK),
            ("텍스트 입력", ActionType.TYPE_TEXT),
            ("키 입력", ActionType.KEY_PRESS),
            ("대기", ActionType.WAIT),
            ("텔레그램 전송", ActionType.SEND_TELEGRAM),
        ]

        from PyQt6.QtWidgets import QInputDialog

        action_names = [name for name, _ in action_types]
        action_name, ok = QInputDialog.getItem(
            self, "액션 추가", "액션 타입을 선택하세요:", action_names, 0, False
        )

        if ok:
            # 선택된 액션 타입 찾기
            action_type = None
            for name, atype in action_types:
                if name == action_name:
                    action_type = atype
                    break

            if action_type:
                # 새 액션 생성
                action = MacroAction(id=str(uuid.uuid4()), action_type=action_type)

                # 기본값 설정
                if action_type == ActionType.WAIT:
                    action.wait_seconds = 1.0
                elif action_type == ActionType.TYPE_TEXT:
                    text, ok = QInputDialog.getText(
                        self, "텍스트 입력", "입력할 텍스트:"
                    )
                    if ok:
                        action.text_input = text
                    else:
                        return

                # 시퀀스에 추가
                if self.current_sequence:
                    self.current_sequence.add_action(action)
                    self.refresh_action_list()

    def delete_action(self):
        """액션 삭제"""
        items = self.action_list.selectedItems()
        if not items or not self.current_sequence:
            return

        action_id = items[0].data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(
            self,
            "액션 삭제",
            "선택한 액션을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.current_sequence.remove_action(action_id)
            self.refresh_action_list()

    def move_action_up(self):
        """액션 위로 이동"""
        current_row = self.action_list.currentRow()
        if current_row <= 0 or not self.current_sequence:
            return

        action_id = self.action_list.currentItem().data(Qt.ItemDataRole.UserRole)
        self.current_sequence.move_action(action_id, current_row - 1)
        self.refresh_action_list()
        self.action_list.setCurrentRow(current_row - 1)

    def move_action_down(self):
        """액션 아래로 이동"""
        current_row = self.action_list.currentRow()
        if current_row >= self.action_list.count() - 1 or not self.current_sequence:
            return

        action_id = self.action_list.currentItem().data(Qt.ItemDataRole.UserRole)
        self.current_sequence.move_action(action_id, current_row + 1)
        self.refresh_action_list()
        self.action_list.setCurrentRow(current_row + 1)

    def save_sequence(self):
        """시퀀스 저장"""
        if not self.current_sequence or not self.engine:
            return

        # 입력 검증
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "경고", "시퀀스 이름을 입력하세요.")
            return

        try:
            # 데이터 업데이트
            self.current_sequence.name = name
            self.current_sequence.description = self.description_edit.toPlainText()
            self.current_sequence.enabled = self.enabled_checkbox.isChecked()
            self.current_sequence.loop_count = self.loop_count_spin.value()
            self.current_sequence.loop_delay = self.loop_delay_spin.value()

            # 새 시퀀스인 경우 엔진에 추가
            if self.is_new_sequence:
                self.engine.config.add_macro_sequence(self.current_sequence)

            # 저장
            self.engine.save_config()

            # 성공 신호 발송
            self.sequence_saved.emit(self.current_sequence.id)

            # 다이얼로그 닫기
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "오류", f"시퀀스 저장 실패: {e}")

