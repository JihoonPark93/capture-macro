"""
액션 편집기 다이얼로그
"""

import uuid
from typing import Optional, List
from pathlib import Path

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
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QPoint
from PyQt6.QtGui import QPixmap
from ..models.macro_models import (
    MacroAction,
    ActionType,
    ImageSearchFailureAction,
    ConditionType,
)
from ..core.macro_engine import MacroEngine


STR_ACTION_MAP = {
    "마우스 클릭": ActionType.CLICK,
    "이미지 클릭": ActionType.IMAGE_CLICK,
    "텍스트 입력": ActionType.TYPE_TEXT,
    # "키 입력": ActionType.KEY_PRESS,
    "스크롤": ActionType.SCROLL,
    "대기": ActionType.WAIT,
    "텔레그램 전송": ActionType.SEND_TELEGRAM,
    "조건문 (IF)": ActionType.IF,
    "조건문 (ELSE)": ActionType.ELSE,
}
# 액션 타입 설정
ACTION_STR_MAP = {
    ActionType.CLICK: "마우스 클릭",
    ActionType.IMAGE_CLICK: "이미지 클릭",
    ActionType.TYPE_TEXT: "텍스트 입력",
    ActionType.KEY_PRESS: "키 입력",
    ActionType.SCROLL: "스크롤",
    ActionType.WAIT: "대기",
    ActionType.SEND_TELEGRAM: "텔레그램 전송",
    ActionType.IF: "조건문 (IF)",
    ActionType.ELSE: "조건문 (ELSE)",
}


class ActionEditor(QDialog):
    """액션 편집기 다이얼로그"""

    action_saved = pyqtSignal(object)  # MacroAction
    capture_requested = pyqtSignal()  # 캡쳐 요청 시그널
    mouse_capture_requested = pyqtSignal()  # 마우스 캡쳐 요청 시그널

    def __init__(self, engine: MacroEngine, parent=None):
        super().__init__(parent)

        self.engine = engine
        self.action = None
        self.current_template_id: Optional[str] = None
        self.captured_keys: List[str] = []

        # UI 요소들
        self.action_type_combo: Optional[QComboBox] = None
        self.settings_group: Optional[QGroupBox] = None
        self.settings_layout: Optional[QVBoxLayout] = None

        # 현재 상태 보존을 위한 변수들
        self._preserved_state: dict = {}

        # 영역 선택을 위한 변수들
        self.is_dragging = False
        self.drag_start_pos = None
        self.region_overlay = None

        self.is_edit_mode = False
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """UI 초기화"""
        title = "액션 편집" if self.is_edit_mode else "액션 추가"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(800, 600)  # 더 큰 창 크기

        # 메인 레이아웃 (수평 분할)
        main_layout = QHBoxLayout(self)

        # 왼쪽 패널 (설정들)
        left_panel = QWidget()
        left_panel.setFixedWidth(350)  # 고정 너비
        layout = QVBoxLayout(left_panel)

        # 액션 설명
        description_group = QGroupBox("액션 설명")
        description_layout = QFormLayout(description_group)
        description_group.setMinimumHeight(50)  # 최소 높이 지정
        description_group.setMaximumHeight(120)  # 최대 높이 지정

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText(
            "액션에 대한 간단한 설명을 입력하세요 (예: 로그인 버튼 클릭)"
        )
        description_layout.addRow("설명:", self.description_input)
        layout.addWidget(description_group)

        # 액션 타입 선택
        type_group = QGroupBox("액션 타입")
        type_layout = QFormLayout(type_group)
        type_group.setMinimumHeight(50)  # 최소 높이 지정
        type_group.setMaximumHeight(120)  # 최대 높이 지정

        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(
            [
                "마우스 클릭",
                "이미지 클릭",
                # "더블클릭",
                # "우클릭",
                "텍스트 입력",
                # "키 입력",
                "스크롤",
                "대기",
                "텔레그램 전송",
                # "조건문 (IF)",
                # "조건문 (ELSE)",
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
        cancel_btn.clicked.connect(self.on_cancel)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # 왼쪽 패널을 메인 레이아웃에 추가
        main_layout.addWidget(left_panel)

        # 오른쪽 패널 (이미지 미리보기)
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)

        # 이미지 미리보기 제목
        self.image_title = QLabel("이미지 미리보기 및 클릭 위치 설정")
        self.image_title.setStyleSheet(
            "font-weight: bold; font-size: 14px; margin-bottom: 10px;"
        )
        right_layout.addWidget(self.image_title)

        self.current_template_id = None
        # 이미지 미리보기 라벨 (오른쪽 패널 전체 사용)
        self.large_image_preview = QLabel()
        self.large_image_preview.setMinimumSize(400, 300)
        self.large_image_preview.setStyleSheet(
            "border: 2px solid #dee2e6; background-color: #f8f9fa; border-radius: 8px;"
        )
        self.large_image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.large_image_preview.setText(
            "이미지를 캡쳐하면 여기에 표시됩니다.\n클릭할 위치를 선택하세요.\nShift+드래그로 영역을 선택할 수 있습니다."
        )
        self.large_image_preview.setMouseTracking(True)
        self.large_image_preview.mousePressEvent = (
            self.on_large_image_preview_mouse_press
        )
        self.large_image_preview.mouseMoveEvent = self.on_large_image_preview_mouse_move
        self.large_image_preview.mouseReleaseEvent = (
            self.on_large_image_preview_mouse_release
        )
        right_layout.addWidget(self.large_image_preview)

        # 클릭 위치 정보 표시
        self.click_info_label = QLabel("클릭 위치: 미설정")
        self.click_info_label.setStyleSheet(
            "color: #6c757d; font-size: 12px; margin-top: 10px;"
        )
        right_layout.addWidget(self.click_info_label)

        # 영역 선택 정보 표시
        self.region_info_label = QLabel("선택 영역: 없음")
        self.region_info_label.setStyleSheet(
            "color: #6c757d; font-size: 12px; margin-top: 5px;"
        )
        right_layout.addWidget(self.region_info_label)

        main_layout.addWidget(self.right_panel)

    def init_ui_values(self):
        title = "액션 편집" if self.is_edit_mode else "액션 추가"
        self.setWindowTitle(title)

        self.description_input.setText("")
        self.action_type_combo.setCurrentText("마우스 클릭")

        self.current_template_id = None
        self.large_image_preview.setPixmap(QPixmap())
        self.large_image_preview.setText(
            "이미지를 캡쳐하면 여기에 표시됩니다.\n클릭할 위치를 선택하세요.\nShift+드래그로 영역을 선택할 수 있습니다."
        )
        self.region_overlay.hide()
        self.large_position_marker.hide()

        self.click_info_label.setVisible(False)
        self.region_info_label.setText("선택 영역: 없음")
        self.hide_region_overlay()

    def setup_connections(self):
        """신호 연결"""
        self.action_type_combo.currentTextChanged.connect(self.on_action_type_changed)

    def on_cancel(self):
        """취소 버튼 클릭 시"""
        self.hide()

    def on_action_type_changed(self):
        """액션 타입 변경 시"""
        # 현재 템플릿 정보 임시 보존
        preserved_template_id = getattr(self, "current_template_id", None)
        preserved_click_position = getattr(self, "selected_click_position", None)

        self.update_settings_ui()
        # 템플릿 정보 복원 (액션 타입이 이미지 사용 타입인 경우)
        action_type = self.get_selected_action_type()
        if action_type in [
            ActionType.IMAGE_CLICK,
            ActionType.IF,
        ]:
            if preserved_template_id:
                self.current_template_id = preserved_template_id
                # 이미지 다시 로드
                QTimer.singleShot(
                    50, lambda: self._safe_load_template_image(preserved_template_id)
                )

            if preserved_click_position and action_type in [
                ActionType.IMAGE_CLICK,
            ]:
                self.selected_click_position = preserved_click_position
                # 클릭 위치 복원
                QTimer.singleShot(100, self._restore_click_position_after_type_change)

        self.update_settings_ui()

    def update_settings_ui(self):
        """설정 UI 업데이트 - self.action 값이 있으면 해당 값으로 설정, 없으면 기본값으로 설정"""
        # 기존 위젯들 안전하게 제거
        for i in reversed(range(self.settings_layout.count())):
            child = self.settings_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
                self.settings_layout.removeWidget(child)

        action_type = self.get_selected_action_type()
        if not action_type:
            return

        # 오른쪽 패널 표시/숨김 결정 (이미지를 사용하는 액션들)
        is_image_action = action_type in [
            ActionType.IMAGE_CLICK,
            ActionType.IF,  # IF 액션도 이미지 사용
        ]

        if hasattr(self, "right_panel"):
            self.right_panel.setVisible(is_image_action)

            # 오른쪽 패널 제목과 텍스트를 액션 타입에 맞게 업데이트
            if is_image_action:
                if action_type == ActionType.IF:
                    # IF 액션: 클릭 위치 설정 불필요
                    if hasattr(self, "image_title"):
                        self.image_title.setText("조건 이미지 미리보기")
                    if hasattr(self, "large_image_preview") and not hasattr(
                        self, "current_template_id"
                    ):
                        self.large_image_preview.setText(
                            "조건 확인에 사용할 이미지를 캡쳐하세요."
                        )
                    if hasattr(self, "click_info_label"):
                        self.click_info_label.setVisible(False)
                else:
                    # 클릭 액션들: 클릭 위치 설정 필요
                    if hasattr(self, "image_title"):
                        self.image_title.setText("이미지 미리보기 및 클릭 위치 설정")
                    if hasattr(self, "large_image_preview") and not hasattr(
                        self, "current_template_id"
                    ):
                        self.large_image_preview.setText(
                            "이미지를 캡쳐하면 여기에 표시됩니다.\n클릭할 위치를 선택하세요."
                        )
                    if hasattr(self, "click_info_label"):
                        self.click_info_label.setVisible(True)

        form_layout = QFormLayout()

        if action_type == ActionType.CLICK:
            # 좌표 표시
            self.click_x_spin = QSpinBox()
            self.click_x_spin.setRange(0, 9999)
            self.click_x_spin.setReadOnly(True)
            self.click_x_spin.setStyleSheet("background-color: #f8f9fa;")
            form_layout.addRow("X 좌표:", self.click_x_spin)

            self.click_y_spin = QSpinBox()
            self.click_y_spin.setRange(0, 9999)
            self.click_y_spin.setReadOnly(True)
            self.click_y_spin.setStyleSheet("background-color: #f8f9fa;")
            form_layout.addRow("Y 좌표:", self.click_y_spin)

            # 마우스 위치 캡쳐 버튼
            self.mouse_capture_btn = QPushButton("마우스 위치 캡쳐")
            self.mouse_capture_btn.setObjectName("success_button")
            self.mouse_capture_btn.clicked.connect(self.request_mouse_capture)
            form_layout.addRow("위치 캡쳐:", self.mouse_capture_btn)

            # 안내 텍스트
            mouse_info_label = QLabel(
                "※ 버튼을 클릭하면 전체화면 오버레이가 표시됩니다"
            )
            mouse_info_label.setStyleSheet("color: #6c757d; font-size: 12px;")
            form_layout.addRow(mouse_info_label)

            # 액션 데이터가 있으면 클릭 위치 설정
            if self.action and self.action.click_position:
                self.click_x_spin.setValue(self.action.click_position[0])
                self.click_y_spin.setValue(self.action.click_position[1])
                self.selected_click_position = self.action.click_position

        if action_type in [
            ActionType.IMAGE_CLICK,
        ]:
            # 안내 텍스트
            self.coordinate_info_label = QLabel(
                "※ 좌표는 우측 이미지를 좌클릭하여 설정하세요"
            )
            self.coordinate_info_label.setStyleSheet("color: #6c757d; font-size: 12px;")
            form_layout.addRow(self.coordinate_info_label)

            # 캡쳐 버튼
            self.capture_btn = QPushButton("이미지 캡쳐")
            self.capture_btn.setObjectName("success_button")
            self.capture_btn.clicked.connect(self.start_capture)
            form_layout.addRow("이미지 캡쳐:", self.capture_btn)

            # 이미지 탐색 실패 시 처리 옵션
            self.failure_action_combo = QComboBox()
            self.failure_action_combo.addItems(
                [
                    "실행 중단",
                    "매크로 처음부터 재실행",
                    "무시하고 다음 단계",
                ]
            )
            form_layout.addRow("이미지 탐색 실패 시:", self.failure_action_combo)

            # 액션 데이터가 있으면 설정값 로드
            if self.action:
                # 실패 처리 옵션 설정
                if hasattr(self.action, "on_image_not_found"):
                    self.set_failure_action(self.action.on_image_not_found)
                else:
                    self.failure_action_combo.setCurrentText("실행 중단")

                # 이미지 템플릿 로드
                if self.action.image_template_id:
                    self.current_template_id = self.action.image_template_id
                    self.load_template_image(self.action.image_template_id)

                    # 클릭 위치 설정
                    if self.action.click_position:
                        self.selected_click_position = self.action.click_position
                        self.update_large_click_position_marker()
                        if hasattr(self, "click_info_label"):
                            x, y = self.action.click_position
                            self.click_info_label.setText(f"클릭 위치: ({x}, {y})")

                    # 선택된 영역 정보 로드
                    if self.action.selected_region:
                        x1, y1, x2, y2 = self.action.selected_region
                        width = x2 - x1
                        height = y2 - y1
                        self.region_info_label.setText(
                            f"선택 영역: ({x1}, {y1}) ~ ({x2}, {y2}) [{width}x{height}]"
                        )
                        # 이미지 좌표를 라벨 좌표로 변환
                        start_label_pos = self.convert_image_pos_to_label_pos((x1, y1))
                        end_label_pos = self.convert_image_pos_to_label_pos((x2, y2))

                        if start_label_pos and end_label_pos:
                            self.update_region_overlay(
                                QPoint(start_label_pos[0], start_label_pos[1]),
                                QPoint(end_label_pos[0], end_label_pos[1]),
                            )
                        else:
                            self.hide_region_overlay()
                    else:
                        self.hide_region_overlay()
                        self.region_info_label.setText("선택 영역: 없음")
            else:
                # 기본값 설정
                self.failure_action_combo.setCurrentText("실행 중단")

        elif action_type == ActionType.TYPE_TEXT:
            self.text_input = QTextEdit()
            self.text_input.setMaximumHeight(100)
            form_layout.addRow("입력할 텍스트:", self.text_input)

            # 액션 데이터가 있으면 텍스트 설정
            if self.action and hasattr(self.action, "text_input"):
                self.text_input.setPlainText(self.action.text_input or "")

        elif action_type == ActionType.KEY_PRESS:
            # 키 입력 캡처를 위한 위젯
            self.key_input_widget = QWidget()
            key_input_layout = QHBoxLayout(self.key_input_widget)

            self.key_input = QLineEdit()
            self.key_input.setPlaceholderText("키를 눌러 입력하세요")
            self.key_input.setReadOnly(True)  # 직접 입력 방지
            self.key_input.setStyleSheet("background-color: #f8f9fa;")
            key_input_layout.addWidget(self.key_input)

            # 키 캡처 버튼
            self.capture_key_btn = QPushButton("키 입력")
            self.capture_key_btn.clicked.connect(self.start_key_capture)
            key_input_layout.addWidget(self.capture_key_btn)

            # 초기화 버튼
            self.clear_key_btn = QPushButton("초기화")
            self.clear_key_btn.clicked.connect(self.clear_key_input)
            key_input_layout.addWidget(self.clear_key_btn)

            form_layout.addRow("키 조합:", self.key_input_widget)

            # 액션 데이터가 있으면 키 조합 설정
            if self.action and hasattr(self.action, "key_combination"):
                keys = self.action.key_combination or []
                self.key_input.setText("+".join(keys))
                if keys:
                    self.captured_keys = keys

        elif action_type == ActionType.SCROLL:
            # 스크롤 방향 선택
            self.scroll_direction_combo = QComboBox()
            self.scroll_direction_combo.addItems(
                ["위쪽으로", "아래쪽으로", "왼쪽으로", "오른쪽으로"]
            )
            form_layout.addRow("스크롤 방향:", self.scroll_direction_combo)

            # 스크롤 픽셀 수
            self.scroll_amount_spin = QSpinBox()
            self.scroll_amount_spin.setRange(1, 100)
            self.scroll_amount_spin.setSuffix(" 회")
            form_layout.addRow("스크롤 횟수:", self.scroll_amount_spin)

            # 안내 텍스트
            scroll_info_label = QLabel(
                "※ 마우스 휠이나 페이지 스크롤을 시뮬레이션합니다"
            )
            scroll_info_label.setStyleSheet("color: #6c757d; font-size: 12px;")
            form_layout.addRow(scroll_info_label)

            # 액션 데이터가 있으면 스크롤 설정값 로드
            if self.action:
                # 스크롤 방향 설정
                if (
                    hasattr(self.action, "scroll_direction")
                    and self.action.scroll_direction
                ):
                    direction_map = {
                        "up": "위쪽으로",
                        "down": "아래쪽으로",
                        "left": "왼쪽으로",
                        "right": "오른쪽으로",
                    }
                    direction_text = direction_map.get(
                        self.action.scroll_direction, "아래쪽으로"
                    )
                    index = self.scroll_direction_combo.findText(direction_text)
                    if index >= 0:
                        self.scroll_direction_combo.setCurrentIndex(index)
                else:
                    self.scroll_direction_combo.setCurrentText("아래쪽으로")

                # 스크롤 횟수 설정
                if hasattr(self.action, "scroll_amount"):
                    self.scroll_amount_spin.setValue(self.action.scroll_amount or 10)
                else:
                    self.scroll_amount_spin.setValue(10)
            else:
                # 기본값 설정
                self.scroll_direction_combo.setCurrentText("아래쪽으로")
                self.scroll_amount_spin.setValue(10)

        elif action_type == ActionType.WAIT:
            self.wait_seconds = QDoubleSpinBox()
            self.wait_seconds.setRange(0.1, 60.0)
            self.wait_seconds.setSuffix(" 초")
            form_layout.addRow("대기 시간:", self.wait_seconds)

            # 액션 데이터가 있으면 대기 시간 설정
            if self.action and hasattr(self.action, "wait_seconds"):
                self.wait_seconds.setValue(self.action.wait_seconds or 1.0)
            else:
                self.wait_seconds.setValue(1.0)

        elif action_type == ActionType.SEND_TELEGRAM:
            self.telegram_message = QTextEdit()
            self.telegram_message.setMaximumHeight(100)
            form_layout.addRow("메시지:", self.telegram_message)

            # 액션 데이터가 있으면 메시지 설정
            if self.action and hasattr(self.action, "telegram_message"):
                self.telegram_message.setPlainText(self.action.telegram_message or "")

        elif action_type == ActionType.IF:
            # 조건 타입 선택
            self.condition_type_combo = QComboBox()
            self.condition_type_combo.addItems(
                ["이미지 발견", "이미지 미발견", "항상 실행"]
            )
            form_layout.addRow("조건 타입:", self.condition_type_combo)

            # 조건 이미지 선택 (이미지 기반 조건일 때만)
            condition_image_widget = QWidget()
            condition_image_layout = QHBoxLayout(condition_image_widget)

            self.condition_image_input = QLineEdit()
            self.condition_image_input.setPlaceholderText("조건 확인에 사용할 이미지")
            self.condition_image_input.setReadOnly(True)
            condition_image_layout.addWidget(self.condition_image_input)

            self.condition_capture_btn = QPushButton("이미지 캡쳐")
            self.condition_capture_btn.clicked.connect(self.start_capture)
            condition_image_layout.addWidget(self.condition_capture_btn)

            form_layout.addRow("조건 이미지:", condition_image_widget)

            # 조건 타입 변경 시 이미지 선택 활성화/비활성화
            self.condition_type_combo.currentTextChanged.connect(
                self.on_condition_type_changed
            )

            # 액션 데이터가 있으면 조건 설정값 로드
            if self.action:
                # 조건 타입 설정
                if (
                    hasattr(self.action, "condition_type")
                    and self.action.condition_type
                ):
                    condition_text_map = {
                        ConditionType.IMAGE_FOUND: "이미지 발견",
                        ConditionType.IMAGE_NOT_FOUND: "이미지 미발견",
                        ConditionType.ALWAYS: "항상 실행",
                    }
                    text = condition_text_map.get(
                        self.action.condition_type, "항상 실행"
                    )
                    index = self.condition_type_combo.findText(text)
                    if index >= 0:
                        self.condition_type_combo.setCurrentIndex(index)
                else:
                    self.condition_type_combo.setCurrentText("항상 실행")

                # 이미지 템플릿 로드
                if self.action.image_template_id:
                    self.current_template_id = self.action.image_template_id
                    self.load_template_image(self.action.image_template_id)

                    # 조건 이미지 입력 필드에 템플릿 이름 표시
                    if hasattr(self, "engine"):
                        engine = self.engine
                        template = engine.config.get_image_template(
                            self.action.image_template_id
                        )
                        if template:
                            self.condition_image_input.setText(template.name)
            else:
                # 기본값 설정
                self.condition_type_combo.setCurrentText("항상 실행")

            # 초기 설정 적용
            self.on_condition_type_changed()

        elif action_type == ActionType.ELSE:
            # ELSE는 별도 설정이 필요 없음
            info_label = QLabel("ELSE 조건은 앞의 IF 조건이 거짓일 때 실행됩니다.")
            info_label.setStyleSheet("color: #6c757d; font-style: italic;")
            form_layout.addRow(info_label)

        # 공통 설정
        self.enabled_check = QCheckBox("활성화")
        form_layout.addRow(self.enabled_check)

        # 액션 데이터가 있으면 활성화 상태 설정
        if self.action and hasattr(self.action, "enabled"):
            self.enabled_check.setChecked(self.action.enabled)
        else:
            self.enabled_check.setChecked(True)

        # 설명 설정 (공통)
        if hasattr(self, "description_input"):
            if self.action and hasattr(self.action, "description"):
                self.description_input.setText(self.action.description or "")
            else:
                self.description_input.setText("")

        # 메모리 누수 방지를 위해 제대로 된 부모-자식 관계 설정
        widget = QWidget(self.settings_group)
        widget.setLayout(form_layout)
        self.settings_layout.addWidget(widget)

    def start_capture(self):
        """화면 캡쳐 시작"""
        # Signal을 통해 캡쳐 요청
        self.capture_requested.emit()

    def request_mouse_capture(self):
        """마우스 위치 캡쳐 요청"""
        # Signal을 통해 마우스 캡쳐 요청
        self.mouse_capture_requested.emit()

    def on_condition_type_changed(self):
        """조건 타입 변경 시 처리"""
        if not hasattr(self, "condition_type_combo"):
            return

        condition_text = self.condition_type_combo.currentText()
        is_image_based = condition_text in ["이미지 발견", "이미지 미발견"]

        if hasattr(self, "condition_image_input"):
            self.condition_image_input.setEnabled(is_image_based)
        if hasattr(self, "condition_capture_btn"):
            self.condition_capture_btn.setEnabled(is_image_based)

    def start_key_capture(self):
        """키 입력 캡처 시작"""
        from .key_capture_dialog import KeyCaptureDialog

        dialog = KeyCaptureDialog(self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted and dialog.captured_keys:
            key_text = " + ".join(dialog.captured_keys)
            self.key_input.setText(key_text)
            self.captured_keys = dialog.captured_keys

    def clear_key_input(self):
        """키 입력 초기화"""
        self.key_input.clear()
        if hasattr(self, "captured_keys"):
            self.captured_keys = []

    def create_region_overlay(self):
        """영역 선택을 위한 overlay 위젯 생성"""
        if self.region_overlay:
            self.region_overlay.hide()
            self.region_overlay.deleteLater()

        self.region_overlay = QLabel(self.large_image_preview)
        self.region_overlay.setStyleSheet(
            "background-color: rgba(0, 123, 255, 100); border: 2px solid #007bff;"
        )
        self.region_overlay.hide()

    def update_region_overlay(self, start_pos, end_pos):
        """영역 overlay 업데이트"""
        if not self.region_overlay:
            self.create_region_overlay()

        # 시작점과 끝점 사이의 사각형 계산
        x1 = min(start_pos.x(), end_pos.x())
        y1 = min(start_pos.y(), end_pos.y())
        width = abs(end_pos.x() - start_pos.x())
        height = abs(end_pos.y() - start_pos.y())

        if width > 5 and height > 5:  # 최소 크기 제한
            self.region_overlay.setGeometry(x1, y1, width, height)
            self.region_overlay.show()
        else:
            self.region_overlay.hide()

    def hide_region_overlay(self):
        """영역 overlay 숨김"""
        if self.region_overlay:
            self.region_overlay.hide()

    def convert_label_pos_to_image_pos(self, label_pos):
        """라벨 좌표를 이미지 좌표로 변환"""
        label_size = self.large_image_preview.size()

        if not hasattr(self, "current_pixmap") or not self.current_pixmap:
            return None

        pixmap_size = self.current_pixmap.size()

        # 라벨 크기에 맞춰 스케일링된 이미지 크기 계산
        label_ratio = label_size.width() / label_size.height()
        image_ratio = pixmap_size.width() / pixmap_size.height()

        if image_ratio > label_ratio:
            # 이미지가 더 넓음 - 너비에 맞춤
            displayed_width = label_size.width()
            displayed_height = int(displayed_width / image_ratio)
            offset_x = 0
            offset_y = (label_size.height() - displayed_height) // 2
        else:
            # 이미지가 더 높음 - 높이에 맞춤
            displayed_height = label_size.height()
            displayed_width = int(displayed_height * image_ratio)
            offset_x = (label_size.width() - displayed_width) // 2
            offset_y = 0

        # 클릭된 위치가 실제 이미지 영역 내부인지 확인
        click_x = label_pos.x() - offset_x
        click_y = label_pos.y() - offset_y

        if 0 <= click_x <= displayed_width and 0 <= click_y <= displayed_height:
            # 실제 이미지 좌표로 변환
            scale_x = pixmap_size.width() / displayed_width
            scale_y = pixmap_size.height() / displayed_height

            image_x = int(click_x * scale_x)
            image_y = int(click_y * scale_y)
            return (image_x, image_y)

        return None

    def convert_image_pos_to_label_pos(self, image_pos):
        """이미지 좌표를 라벨 좌표로 변환"""
        if not image_pos or len(image_pos) != 2:
            return None

        label_size = self.large_image_preview.size()

        if not hasattr(self, "current_pixmap") or not self.current_pixmap:
            return None

        pixmap_size = self.current_pixmap.size()
        image_x, image_y = image_pos

        # 이미지 좌표가 유효한 범위 내에 있는지 확인
        if not (
            0 <= image_x < pixmap_size.width() and 0 <= image_y < pixmap_size.height()
        ):
            return None

        # 라벨 크기에 맞춰 스케일링된 이미지 크기 계산
        label_ratio = label_size.width() / label_size.height()
        image_ratio = pixmap_size.width() / pixmap_size.height()

        if image_ratio > label_ratio:
            # 이미지가 더 넓음 - 너비에 맞춤
            displayed_width = label_size.width()
            displayed_height = int(displayed_width / image_ratio)
            offset_x = 0
            offset_y = (label_size.height() - displayed_height) // 2
        else:
            # 이미지가 더 높음 - 높이에 맞춤
            displayed_height = label_size.height()
            displayed_width = int(displayed_height * image_ratio)
            offset_x = (label_size.width() - displayed_width) // 2
            offset_y = 0

        # 이미지 좌표를 표시된 이미지 좌표로 변환
        scale_x = displayed_width / pixmap_size.width()
        scale_y = displayed_height / pixmap_size.height()

        displayed_x = image_x * scale_x
        displayed_y = image_y * scale_y

        # 라벨 좌표로 변환 (오프셋 추가)
        label_x = int(displayed_x + offset_x)
        label_y = int(displayed_y + offset_y)

        # 라벨 범위 내에 있는지 확인
        if 0 <= label_x < label_size.width() and 0 <= label_y < label_size.height():
            return (label_x, label_y)

        return None

    def on_large_image_preview_mouse_press(self, event):
        """큰 이미지 미리보기 마우스 누름 이벤트"""
        if not hasattr(self, "current_template_id") or not self.current_template_id:
            QMessageBox.warning(self, "경고", "먼저 이미지를 캡쳐하세요.")
            return

        modifiers = event.modifiers()

        if modifiers == Qt.KeyboardModifier.ShiftModifier:
            # Shift + 클릭: 영역 선택 시작
            self.is_dragging = True
            self.drag_start_pos = event.pos()
            self.hide_region_overlay()
            self.create_region_overlay()
        else:
            # 일반 클릭: 클릭 위치 설정
            self.on_large_image_preview_clicked(event)

    def on_large_image_preview_mouse_move(self, event):
        """큰 이미지 미리보기 마우스 이동 이벤트"""
        if self.is_dragging and self.drag_start_pos:
            # 드래그 중 영역 표시 업데이트
            self.update_region_overlay(self.drag_start_pos, event.pos())

    def on_large_image_preview_mouse_release(self, event):
        """큰 이미지 미리보기 마우스 놓음 이벤트"""
        if self.is_dragging and self.drag_start_pos:
            # 드래그 종료: 영역 선택 완료
            end_pos = event.pos()

            # 시작점과 끝점을 이미지 좌표로 변환
            start_image_pos = self.convert_label_pos_to_image_pos(self.drag_start_pos)
            end_image_pos = self.convert_label_pos_to_image_pos(end_pos)

            if start_image_pos and end_image_pos:
                # 선택된 영역 저장 (x1, y1, x2, y2)
                x1 = min(start_image_pos[0], end_image_pos[0])
                y1 = min(start_image_pos[1], end_image_pos[1])
                x2 = max(start_image_pos[0], end_image_pos[0])
                y2 = max(start_image_pos[1], end_image_pos[1])

                self.selected_region = (x1, y1, x2, y2)

                # 영역 정보 표시 업데이트
                width = x2 - x1
                height = y2 - y1
                self.region_info_label.setText(
                    f"선택 영역: ({x1}, {y1}) ~ ({x2}, {y2}) [{width}x{height}]"
                )

                # 영역 표시 유지
                self.update_region_overlay(self.drag_start_pos, end_pos)
            else:
                self.hide_region_overlay()

            self.is_dragging = False
            self.drag_start_pos = None

    def on_large_image_preview_clicked(self, event):
        """큰 이미지 미리보기 클릭 시 (일반 클릭용)"""
        if not hasattr(self, "current_template_id") or not self.current_template_id:
            QMessageBox.warning(self, "경고", "먼저 이미지를 캡쳐하세요.")
            return

        # 클릭된 위치 계산 (이미지 좌표로 변환)
        image_pos = self.convert_label_pos_to_image_pos(event.pos())

        if image_pos:
            image_x, image_y = image_pos

            # 클릭 위치 저장
            self.selected_click_position = (image_x, image_y)

            # 시각적 피드백 (클릭 위치 표시)
            self.update_large_click_position_marker()

            # 클릭 위치 정보 업데이트
            if hasattr(self, "click_info_label"):
                self.click_info_label.setText(f"클릭 위치: ({image_x}, {image_y})")
        else:
            QMessageBox.information(self, "알림", "이미지 영역 내에서 클릭해주세요.")

    def update_large_click_position_marker(self):
        """큰 이미지 미리보기의 클릭 위치 마커 업데이트"""
        if not hasattr(self, "selected_click_position"):
            return

        # 기존 마커 제거
        if hasattr(self, "large_position_marker"):
            self.large_position_marker.hide()
            self.large_position_marker.deleteLater()

        # 새 마커 생성
        marker_size = 12  # 큰 이미지이므로 마커도 크게
        self.large_position_marker = QLabel(self.large_image_preview)
        self.large_position_marker.setFixedSize(marker_size, marker_size)
        self.large_position_marker.setStyleSheet(
            "background-color: #ff0000; border: 2px solid #ffffff; border-radius: 6px;"
        )

        # 마커 위치 설정 (큰 미리보기 크기에 맞게 조정)
        if hasattr(self, "current_pixmap") and self.current_pixmap:
            pixmap_size = self.current_pixmap.size()
            label_size = self.large_image_preview.size()

            # aspect ratio를 고려한 실제 표시 영역 계산
            label_ratio = label_size.width() / label_size.height()
            image_ratio = pixmap_size.width() / pixmap_size.height()

            if image_ratio > label_ratio:
                # 너비에 맞춤
                displayed_width = label_size.width()
                displayed_height = int(displayed_width / image_ratio)
                offset_x = 0
                offset_y = (label_size.height() - displayed_height) // 2
            else:
                # 높이에 맞춤
                displayed_height = label_size.height()
                displayed_width = int(displayed_height * image_ratio)
                offset_x = (label_size.width() - displayed_width) // 2
                offset_y = 0

            # 마커 위치 계산
            marker_x = (
                offset_x
                + int(
                    self.selected_click_position[0]
                    * displayed_width
                    / pixmap_size.width()
                )
                - marker_size // 2
            )
            marker_y = (
                offset_y
                + int(
                    self.selected_click_position[1]
                    * displayed_height
                    / pixmap_size.height()
                )
                - marker_size // 2
            )

            self.large_position_marker.move(marker_x, marker_y)
            self.large_position_marker.show()

    def update_click_position_marker(self):
        """기존 작은 이미지 미리보기의 클릭 위치 마커 업데이트 (호환성 유지)"""
        # 큰 이미지 미리보기 마커도 함께 업데이트
        self.update_large_click_position_marker()

    def load_template_image(self, template_id: str):
        """템플릿 이미지 로드 및 표시"""
        print(f"템플릿 이미지 로드 및 표시: {template_id}")
        try:
            engine = self.engine
            template = engine.config.get_image_template(template_id)

            if template and template.file_path and Path(template.file_path).exists():
                pixmap = QPixmap(template.file_path)
                if not pixmap.isNull():
                    # 원본 픽스맵 저장 (좌표 변환용)
                    self.current_pixmap = pixmap

                    # 큰 이미지 미리보기에 표시
                    if hasattr(self, "large_image_preview"):
                        # 큰 미리보기에는 더 큰 크기로 표시
                        large_scaled_pixmap = pixmap.scaled(
                            self.large_image_preview.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        self.large_image_preview.setPixmap(large_scaled_pixmap)
                        self.large_image_preview.setText("")

                    return

            # 이미지 로드 실패 시
            if hasattr(self, "large_image_preview"):
                self.large_image_preview.setText("이미지 로드 실패")

        except Exception as e:
            print(f"템플릿 이미지 로드 실패: {e}")
            if hasattr(self, "large_image_preview"):
                self.large_image_preview.setText("이미지 로드 오류")

    def on_mouse_capture_completed(self, point: QPoint):
        """마우스 캡쳐 완료 시"""
        self.click_x_spin.setValue(point.x())
        self.click_y_spin.setValue(point.y())
        self.selected_click_position = (point.x(), point.y())

    def on_capture_completed(self, template_id: str, template_name: str):
        """캡쳐 완료 시 호출되는 메소드"""
        try:
            # 다이얼로그가 여전히 유효한지 확인
            if not self._is_dialog_valid():
                return

            self.current_template_id = template_id

            # 안전한 이미지 로드
            QTimer.singleShot(0, lambda: self._safe_load_template_image(template_id))

            # 로그 표시
            print(f"액션 에디터에서 이미지 템플릿 설정됨: {template_name}")

        except Exception as e:
            print(f"캡쳐 완료 처리 중 오류: {e}")

    def _is_dialog_valid(self) -> bool:
        """다이얼로그가 유효한지 확인"""
        try:
            # 기본 속성들에 접근해보기
            _ = self.isVisible()
            _ = self.parent()
            return True
        except (RuntimeError, AttributeError):
            return False

    def _safe_load_template_image(self, template_id: str):
        """안전한 템플릿 이미지 로드"""
        try:
            if self._is_dialog_valid():
                self.load_template_image(template_id)
        except Exception as e:
            print(f"안전한 이미지 로드 실패: {e}")

    def get_selected_action_type(self) -> Optional[ActionType]:
        """선택된 액션 타입 반환"""

        text = self.action_type_combo.currentText()
        return STR_ACTION_MAP.get(text)

    def get_selected_failure_action(self) -> ImageSearchFailureAction:
        """선택된 실패 처리 옵션 반환"""
        failure_map = {
            "실행 중단": ImageSearchFailureAction.STOP_EXECUTION,
            "매크로 처음부터 재실행": ImageSearchFailureAction.RESTART_SEQUENCE,
            "무시하고 다음 단계": ImageSearchFailureAction.SKIP_TO_NEXT,
        }

        if hasattr(self, "failure_action_combo"):
            text = self.failure_action_combo.currentText()
            return failure_map.get(text, ImageSearchFailureAction.STOP_EXECUTION)

        return ImageSearchFailureAction.STOP_EXECUTION

    def get_selected_condition_type(self) -> ConditionType:
        """선택된 조건 타입 반환"""
        condition_map = {
            "이미지 발견": ConditionType.IMAGE_FOUND,
            "이미지 미발견": ConditionType.IMAGE_NOT_FOUND,
            "항상 실행": ConditionType.ALWAYS,
        }

        if hasattr(self, "condition_type_combo"):
            text = self.condition_type_combo.currentText()
            return condition_map.get(text, ConditionType.ALWAYS)

        return ConditionType.ALWAYS

    def set_failure_action(self, failure_action: ImageSearchFailureAction):
        """실패 처리 옵션 설정"""
        if not hasattr(self, "failure_action_combo"):
            return

        failure_text_map = {
            ImageSearchFailureAction.STOP_EXECUTION: "실행 중단",
            ImageSearchFailureAction.RESTART_SEQUENCE: "매크로 처음부터 재실행",
            ImageSearchFailureAction.SKIP_TO_NEXT: "무시하고 다음 단계",
        }

        text = failure_text_map.get(failure_action, "실행 중단")
        index = self.failure_action_combo.findText(text)
        if index >= 0:
            self.failure_action_combo.setCurrentIndex(index)

    def load_action_data(self, action: Optional[MacroAction]):
        """액션 데이터 로드 (편집 모드)"""
        self.action = action
        self.is_edit_mode = self.action is not None
        title = "액션 편집" if self.is_edit_mode else "액션 추가"
        self.setWindowTitle(title)

        if not self.action:
            self.init_ui_values()
        else:
            type_text = ACTION_STR_MAP.get(self.action.action_type, "")
            if type_text:
                index = self.action_type_combo.findText(type_text)
                if index >= 0:
                    self.action_type_combo.setCurrentIndex(index)

        # UI 업데이트 (self.action이 설정된 상태에서 호출)
        self.update_settings_ui()

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

        # 설명 저장
        if hasattr(self, "description_input"):
            action.description = self.description_input.text().strip()

        # 액션별 데이터 저장
        if action_type == ActionType.CLICK:
            # 좌표는 필수
            if (
                not hasattr(self, "selected_click_position")
                or not self.selected_click_position
            ):
                QMessageBox.warning(self, "경고", "마우스 위치를 먼저 캡쳐하세요.")
                return

            action.click_position = self.selected_click_position

        elif action_type in [
            ActionType.IMAGE_CLICK,
        ]:
            # 이미지 템플릿은 필수
            if not hasattr(self, "current_template_id") or not self.current_template_id:
                QMessageBox.warning(self, "경고", "먼저 이미지를 캡쳐하세요.")
                return

            # 클릭 위치도 필수
            if (
                not hasattr(self, "selected_click_position")
                or not self.selected_click_position
            ):
                QMessageBox.warning(
                    self, "경고", "이미지에서 클릭할 위치를 선택하세요."
                )
                return

            action.image_template_id = self.current_template_id
            action.click_position = self.selected_click_position
            # 선택된 영역 정보 저장
            if hasattr(self, "selected_region") and self.selected_region:
                action.selected_region = self.selected_region

            # 실패 처리 옵션 저장
            action.on_image_not_found = self.get_selected_failure_action()

        elif action_type == ActionType.TYPE_TEXT:
            if hasattr(self, "text_input"):
                text = self.text_input.toPlainText().strip()
                if not text:
                    QMessageBox.warning(self, "경고", "입력할 텍스트를 작성하세요.")
                    return
                action.text_input = text

        elif action_type == ActionType.KEY_PRESS:
            if hasattr(self, "key_input"):
                # 캡처된 키가 있으면 그것을 사용
                if hasattr(self, "captured_keys") and self.captured_keys:
                    action.key_combination = self.captured_keys
                else:
                    # 텍스트 입력 방식으로 폴백
                    key_text = self.key_input.text().strip()
                    if not key_text:
                        QMessageBox.warning(self, "경고", "키 조합을 입력하세요.")
                        return
                    action.key_combination = [k.strip() for k in key_text.split("+")]

        elif action_type == ActionType.SCROLL:
            # 스크롤 방향 저장
            if hasattr(self, "scroll_direction_combo"):
                direction_map = {
                    "위쪽으로": "up",
                    "아래쪽으로": "down",
                    "왼쪽으로": "left",
                    "오른쪽으로": "right",
                }
                direction_text = self.scroll_direction_combo.currentText()
                action.scroll_direction = direction_map.get(direction_text, "down")

            # 스크롤 픽셀 수 저장
            if hasattr(self, "scroll_amount_spin"):
                action.scroll_amount = self.scroll_amount_spin.value()

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

        elif action_type == ActionType.IF:
            # 조건 타입 저장
            action.condition_type = self.get_selected_condition_type()

            # 이미지 기반 조건인 경우 이미지 템플릿 필수
            if action.condition_type in [
                ConditionType.IMAGE_FOUND,
                ConditionType.IMAGE_NOT_FOUND,
            ]:
                if (
                    not hasattr(self, "current_template_id")
                    or not self.current_template_id
                ):
                    QMessageBox.warning(
                        self, "경고", "조건 확인에 사용할 이미지를 캡쳐하세요."
                    )
                    return
                action.image_template_id = self.current_template_id

        elif action_type == ActionType.ELSE:
            # ELSE는 별도 설정이 필요 없음
            pass

        self.hide()
        # 액션 저장 신호 발송
        self.action_saved.emit(action)

    def _restore_click_position_after_type_change(self):
        """액션 타입 변경 후 클릭 위치 복원"""
        try:
            if (
                hasattr(self, "selected_click_position")
                and self.selected_click_position
            ):
                # 좌표 스핀박스에 값 설정
                if hasattr(self, "click_x_spin") and self.click_x_spin:
                    self.click_x_spin.setValue(self.selected_click_position[0])
                if hasattr(self, "click_y_spin") and self.click_y_spin:
                    self.click_y_spin.setValue(self.selected_click_position[1])

                # 클릭 위치 마커 업데이트
                self.update_large_click_position_marker()

                # 클릭 위치 정보 업데이트
                if hasattr(self, "click_info_label"):
                    x, y = self.selected_click_position
                    self.click_info_label.setText(f"클릭 위치: ({x}, {y})")

        except Exception as e:
            print(f"클릭 위치 복원 실패: {e}")
