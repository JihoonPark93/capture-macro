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
from PyQt6.QtCore import pyqtSignal, Qt, QTimer

from ..models.macro_models import MacroAction, ActionType


class ActionEditor(QDialog):
    """액션 편집기 다이얼로그"""

    action_saved = pyqtSignal(object)  # MacroAction
    capture_requested = pyqtSignal()  # 캡쳐 요청 시그널

    def __init__(self, parent=None, action: Optional[MacroAction] = None):
        super().__init__(parent)

        self.action = action
        self.is_edit_mode = action is not None
        self.current_template_id: Optional[str] = None
        self.captured_keys: List[str] = []

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

        # 액션 설명
        description_group = QGroupBox("액션 설명")
        description_layout = QFormLayout(description_group)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText(
            "액션에 대한 간단한 설명을 입력하세요 (예: 로그인 버튼 클릭)"
        )
        description_layout.addRow("설명:", self.description_input)
        layout.addWidget(description_group)

        # 액션 설정
        self.settings_group = QGroupBox("액션 설정")
        self.settings_layout = QVBoxLayout(self.settings_group)
        layout.addWidget(self.settings_group)

        # 기본값으로 "클릭" 선택
        self.action_type_combo.setCurrentText("클릭")
        self.update_settings_ui()

        # 버튼들
        button_layout = QHBoxLayout()

        save_btn = QPushButton("저장")
        save_btn.clicked.connect(self.save_action)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.on_cancel)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def setup_connections(self):
        """신호 연결"""
        self.action_type_combo.currentTextChanged.connect(self.on_action_type_changed)

        # 부모 윈도우에 현재 에디터 등록 (캡쳐 완료 이벤트 수신용)
        if hasattr(self.parent(), "register_action_editor"):
            self.parent().register_action_editor(self)

    def on_cancel(self):
        """취소 버튼 클릭 시"""
        # 부모 윈도우에서 에디터 등록 해제
        if hasattr(self.parent(), "unregister_action_editor"):
            self.parent().unregister_action_editor(self)
        self.reject()

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

        if action_type in [
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
            self.use_image_check.toggled.connect(self.on_use_image_toggled)
            self.use_image_check.setChecked(True)
            self.on_use_image_toggled(True)
            form_layout.addRow(self.use_image_check)

            # 이미지 캡쳐 영역
            self.image_capture_layout = QHBoxLayout()

            # 캡쳐 버튼
            self.capture_btn = QPushButton("캡쳐")
            self.capture_btn.setObjectName("success_button")
            self.capture_btn.setEnabled(False)
            self.capture_btn.clicked.connect(self.start_capture)
            self.image_capture_layout.addWidget(self.capture_btn)

            # 이미지 미리보기 라벨
            self.image_preview_label = QLabel()
            self.image_preview_label.setFixedSize(100, 60)
            self.image_preview_label.setStyleSheet(
                "border: 1px solid #dee2e6; background-color: #f8f9fa;"
            )
            self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_preview_label.setText("이미지 없음")
            # 클릭 이벤트 활성화
            self.image_preview_label.setMouseTracking(True)
            self.image_preview_label.mousePressEvent = self.on_image_preview_clicked
            self.image_capture_layout.addWidget(self.image_preview_label)

            self.image_capture_layout.addStretch()
            form_layout.addRow("이미지:", self.image_capture_layout)

        elif action_type == ActionType.TYPE_TEXT:
            self.text_input = QTextEdit()
            self.text_input.setMaximumHeight(100)
            form_layout.addRow("입력할 텍스트:", self.text_input)

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

    def start_capture(self):
        """화면 캡쳐 시작"""
        # Signal을 통해 캡쳐 요청
        self.capture_requested.emit()

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

    def on_image_preview_clicked(self, event):
        """이미지 미리보기 클릭 시"""
        if not hasattr(self, "current_template_id") or not self.current_template_id:
            QMessageBox.warning(self, "경고", "먼저 이미지를 캡쳐하세요.")
            return

        # 클릭된 위치 계산 (이미지 좌표로 변환)
        label_pos = event.pos()
        label_size = self.image_preview_label.size()

        # 미리보기 이미지의 실제 크기와 표시 크기의 비율 계산
        if hasattr(self, "current_pixmap") and self.current_pixmap:
            pixmap_size = self.current_pixmap.size()
            scale_x = pixmap_size.width() / label_size.width()
            scale_y = pixmap_size.height() / label_size.height()

            # 실제 이미지 좌표 계산
            image_x = int(label_pos.x() * scale_x)
            image_y = int(label_pos.y() * scale_y)

            # 클릭 위치 저장
            self.selected_click_position = (image_x, image_y)

            # 시각적 피드백 (클릭 위치 표시)
            self.update_click_position_marker()

            if hasattr(self, "click_x_spin") and hasattr(self, "click_y_spin"):
                self.click_x_spin.setValue(image_x)
                self.click_y_spin.setValue(image_y)

    def update_click_position_marker(self):
        """클릭 위치 마커 업데이트"""
        if not hasattr(self, "selected_click_position"):
            return

        # 기존 마커 제거
        if hasattr(self, "position_marker"):
            self.position_marker.hide()
            self.position_marker.deleteLater()

        # 새 마커 생성
        marker_size = 8
        self.position_marker = QLabel(self.image_preview_label)
        self.position_marker.setFixedSize(marker_size, marker_size)
        self.position_marker.setStyleSheet("background-color: red; border-radius: 4px;")

        # 마커 위치 설정 (미리보기 크기에 맞게 조정)
        if hasattr(self, "current_pixmap") and self.current_pixmap:
            pixmap_size = self.current_pixmap.size()
            label_size = self.image_preview_label.size()

            marker_x = (
                int(
                    self.selected_click_position[0]
                    * label_size.width()
                    / pixmap_size.width()
                )
                - marker_size // 2
            )
            marker_y = (
                int(
                    self.selected_click_position[1]
                    * label_size.height()
                    / pixmap_size.height()
                )
                - marker_size // 2
            )

            self.position_marker.move(marker_x, marker_y)
            self.position_marker.show()

    def load_template_image(self, template_id: str):
        """템플릿 이미지 로드 및 표시"""
        if not hasattr(self, "image_preview_label"):
            return

        # QLabel이 유효한지 확인
        try:
            _ = self.image_preview_label.isVisible()
        except (RuntimeError, AttributeError):
            print(f"image_preview_label이 이미 삭제됨")
            return

        try:
            if hasattr(self.parent(), "engine"):
                engine = self.parent().engine
                template = engine.config.get_image_template(template_id)

                if (
                    template
                    and template.file_path
                    and Path(template.file_path).exists()
                ):
                    from PyQt6.QtGui import QPixmap

                    pixmap = QPixmap(template.file_path)
                    if not pixmap.isNull():
                        # 미리보기 크기로 조정
                        scaled_pixmap = pixmap.scaled(
                            100,
                            60,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )

                        # 안전한 QLabel 접근
                        try:
                            self.image_preview_label.setPixmap(scaled_pixmap)
                            self.image_preview_label.setText("")
                        except RuntimeError:
                            print(f"image_preview_label 접근 실패 - 객체가 삭제됨")
                            return

                        # 원본 픽스맵 저장 (좌표 변환용)
                        self.current_pixmap = pixmap

                        return

            # 이미지 로드 실패 시
            try:
                self.image_preview_label.setText("이미지 없음")
            except RuntimeError:
                print(f"image_preview_label setText 실패 - 객체가 삭제됨")

        except Exception as e:
            print(f"템플릿 이미지 로드 실패: {e}")
            try:
                self.image_preview_label.setText("오류")
            except RuntimeError:
                print(f"image_preview_label setText 실패 - 객체가 삭제됨")

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

    def on_use_image_toggled(self, checked):
        """이미지 템플릿 사용 토글"""
        if hasattr(self, "capture_btn"):
            self.capture_btn.setEnabled(checked)
        if hasattr(self, "click_x_spin"):
            self.click_x_spin.setEnabled(not checked)
        if hasattr(self, "click_y_spin"):
            self.click_y_spin.setEnabled(not checked)

    def get_selected_action_type(self) -> Optional[ActionType]:
        """선택된 액션 타입 반환"""
        type_map = {
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

        # 설명 로드
        if hasattr(self, "description_input") and hasattr(self.action, "description"):
            self.description_input.setText(self.action.description or "")

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
                # 템플릿 이미지 표시
                self.load_template_image(self.action.image_template_id)

                # 기존 클릭 위치 표시
                if self.action.click_position:
                    self.selected_click_position = self.action.click_position
                    self.update_click_position_marker()

        elif self.action.action_type == ActionType.TYPE_TEXT:
            if hasattr(self, "text_input"):
                self.text_input.setPlainText(self.action.text_input or "")

        elif self.action.action_type == ActionType.KEY_PRESS:
            if hasattr(self, "key_input"):
                keys = self.action.key_combination or []
                self.key_input.setText("+".join(keys))
                # 로드된 키 조합을 captured_keys에도 저장
                if keys:
                    self.captured_keys = keys

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

        # 설명 저장
        if hasattr(self, "description_input"):
            action.description = self.description_input.text().strip()

        # 액션별 데이터 저장
        if action_type in [
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
        ]:
            if hasattr(self, "use_image_check") and self.use_image_check.isChecked():
                # 이미지 템플릿 사용
                if (
                    not hasattr(self, "current_template_id")
                    or not self.current_template_id
                ):
                    QMessageBox.warning(self, "경고", "먼저 이미지를 캡쳐하세요.")
                    return
                action.image_template_id = self.current_template_id
                # 이미지 템플릿 사용 시에도 클릭 위치 저장
                if (
                    hasattr(self, "selected_click_position")
                    and self.selected_click_position
                ):
                    action.click_position = self.selected_click_position
                else:
                    action.click_position = None
            else:
                # 좌표 사용
                if (
                    hasattr(self, "selected_click_position")
                    and self.selected_click_position
                ):
                    action.click_position = self.selected_click_position
                elif hasattr(self, "click_x_spin"):
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

        # 부모 윈도우에서 에디터 등록 해제
        if hasattr(self.parent(), "unregister_action_editor"):
            self.parent().unregister_action_editor(self)

        # 액션 저장 신호 발송
        self.action_saved.emit(action)
        self.accept()
