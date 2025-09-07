"""
설정 다이얼로그
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QGroupBox,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from ..core.macro_engine import MacroEngine


class SettingsDialog(QDialog):
    """설정 다이얼로그"""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None, engine: MacroEngine = None):
        super().__init__(parent)

        self.engine = engine
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("설정")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 탭 위젯
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # 일반 설정 탭
        general_tab = self.create_general_tab()
        tab_widget.addTab(general_tab, "일반")

        # 매칭 설정 탭
        matching_tab = self.create_matching_tab()
        tab_widget.addTab(matching_tab, "매칭")

        # 버튼
        button_layout = QHBoxLayout()

        self.ok_button = QPushButton("확인")
        self.ok_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.ok_button)

        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def create_general_tab(self):
        """일반 설정 탭"""
        tab = QTabWidget()
        layout = QVBoxLayout(tab)

        # 경로 설정
        path_group = QGroupBox("경로 설정")
        path_layout = QVBoxLayout(path_group)

        # 스크린샷 저장 경로
        screenshot_layout = QHBoxLayout()
        screenshot_layout.addWidget(QLabel("스크린샷 저장:"))

        self.screenshot_path_edit = QLineEdit()
        screenshot_layout.addWidget(self.screenshot_path_edit)

        browse_btn = QPushButton("찾아보기")
        browse_btn.clicked.connect(self.browse_screenshot_path)
        screenshot_layout.addWidget(browse_btn)

        path_layout.addLayout(screenshot_layout)
        layout.addWidget(path_group)

        # 자동 저장 설정
        auto_save_group = QGroupBox("자동 저장")
        auto_save_layout = QVBoxLayout(auto_save_group)

        auto_save_interval_layout = QHBoxLayout()
        auto_save_interval_layout.addWidget(QLabel("자동 저장 간격:"))

        self.auto_save_spin = QSpinBox()
        self.auto_save_spin.setRange(10, 300)
        self.auto_save_spin.setSuffix("초")
        auto_save_interval_layout.addWidget(self.auto_save_spin)

        auto_save_layout.addLayout(auto_save_interval_layout)
        layout.addWidget(auto_save_group)

        layout.addStretch()
        return tab

    def create_matching_tab(self):
        """매칭 설정 탭"""
        tab = QTabWidget()
        layout = QVBoxLayout(tab)

        # 매칭 임계값
        threshold_group = QGroupBox("매칭 임계값")
        threshold_layout = QVBoxLayout(threshold_group)

        threshold_value_layout = QHBoxLayout()
        threshold_value_layout.addWidget(QLabel("기본 신뢰도:"))

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(50, 100)
        self.threshold_spin.setSuffix("%")
        threshold_value_layout.addWidget(self.threshold_spin)

        threshold_layout.addLayout(threshold_value_layout)
        layout.addWidget(threshold_group)

        # 액션 지연
        delay_group = QGroupBox("실행 지연")
        delay_layout = QVBoxLayout(delay_group)

        action_delay_layout = QHBoxLayout()
        action_delay_layout.addWidget(QLabel("액션 간 지연:"))

        self.action_delay_spin = QDoubleSpinBox()
        self.action_delay_spin.setRange(0.0, 5.0)
        self.action_delay_spin.setSingleStep(0.1)
        self.action_delay_spin.setSuffix("초")
        action_delay_layout.addWidget(self.action_delay_spin)

        delay_layout.addLayout(action_delay_layout)
        layout.addWidget(delay_group)

        layout.addStretch()
        return tab

    def browse_screenshot_path(self):
        """스크린샷 경로 찾아보기"""
        path = QFileDialog.getExistingDirectory(self, "스크린샷 저장 폴더 선택")
        if path:
            self.screenshot_path_edit.setText(path)

    def load_settings(self):
        """설정 로드"""
        if not self.engine:
            return

        config = self.engine.config

        # 경로 설정
        self.screenshot_path_edit.setText(config.screenshot_save_path)

        # 자동 저장
        self.auto_save_spin.setValue(config.auto_save_interval)

        # 매칭 설정
        threshold_percent = int(config.match_confidence_threshold * 100)
        self.threshold_spin.setValue(threshold_percent)

        # 액션 지연
        self.action_delay_spin.setValue(config.action_delay)

    def save_settings(self):
        """설정 저장"""
        if not self.engine:
            return

        try:
            config = self.engine.config

            # 경로 설정
            config.screenshot_save_path = self.screenshot_path_edit.text()

            # 자동 저장
            config.auto_save_interval = self.auto_save_spin.value()

            # 매칭 설정
            config.match_confidence_threshold = self.threshold_spin.value() / 100.0

            # 액션 지연
            config.action_delay = self.action_delay_spin.value()

            # 저장
            self.engine.save_config()

            self.settings_changed.emit()
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 실패: {e}")

