"""
메인 윈도우 GUI
"""

import uuid
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .settings_dialog import SettingsDialog
    from .telegram_settings import TelegramSettingsDialog

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QPushButton,
    QLabel,
    QTextEdit,
    QPlainTextEdit,
    QMessageBox,
    QFileDialog,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QDialog,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QKeySequence,
)

from ..core.macro_engine import MacroEngine, MacroExecutionResult
from ..models.macro_models import ActionType
from ..utils.logger import get_logger

# 다이얼로그 import는 실제 사용 시점에서 동적으로 import

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """메인 애플리케이션 윈도우"""

    def __init__(self):
        super().__init__()

        # 매크로 엔진 초기화
        self.engine = MacroEngine()

        # 상태 변수
        self.is_capturing = False

        # UI 컴포넌트
        self.action_table: Optional[QTableWidget] = None
        self.log_text: Optional[QTextEdit] = None
        self.status_label: Optional[QLabel] = None

        # 액션 에디터 목록 (캡쳐 이벤트 전달용)
        self.action_editors: List = []

        # 캡쳐 시 숨겨진 윈도우 목록
        self.hidden_windows: List = []

        # 캡쳐 관련
        self.capture_overlay = None

        # 다이얼로그
        self.settings_dialog: Optional["SettingsDialog"] = None
        self.telegram_dialog: Optional["TelegramSettingsDialog"] = None

        # UI 초기화
        self.init_ui()
        self.setup_connections()
        self.load_data()

        # 상태 업데이트 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # 1초마다 업데이트

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("KTX Macro V2 - 이미지 기반 매크로 도구")
        self.setMinimumSize(600, 1000)
        self.resize(600, 1000)

        # 전역 스타일시트 설정
        self.setStyleSheet(self.get_global_stylesheet())

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)

        # 메뉴바 생성
        self.create_menu_bar()

        # 툴바 생성
        self.create_toolbar()

        # 메인 분할기
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        # 메인 패널 (액션 목록/로그)
        main_panel = self.create_main_panel()
        main_splitter.addWidget(main_panel)

        # 상태바 생성
        self.create_status_bar()

        # 스타일 적용
        self.apply_styles()

    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()

        # 파일 메뉴
        file_menu = menubar.addMenu("파일(&F)")

        new_action = QAction("새 설정(&N)", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_config)
        file_menu.addAction(new_action)

        open_action = QAction("설정 열기(&O)", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_config)
        file_menu.addAction(open_action)

        save_action = QAction("설정 저장(&S)", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_config)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("종료(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 편집 메뉴
        edit_menu = menubar.addMenu("편집(&E)")

        capture_action = QAction("화면 캡쳐(&C)", self)
        capture_action.setShortcut("Ctrl+Shift+C")
        capture_action.triggered.connect(self.start_capture)
        edit_menu.addAction(capture_action)

        edit_menu.addSeparator()

        settings_action = QAction("설정(&P)", self)
        settings_action.triggered.connect(self.open_settings)
        edit_menu.addAction(settings_action)

        # 실행 메뉴
        run_menu = menubar.addMenu("실행(&R)")

        self.run_action = QAction("매크로 실행(&R)", self)
        self.run_action.setShortcut("F5")
        self.run_action.triggered.connect(self.run_main_sequence)
        run_menu.addAction(self.run_action)

        self.stop_action = QAction("실행 중지(&S)", self)
        self.stop_action.setShortcut("F6")
        self.stop_action.setEnabled(False)
        self.stop_action.triggered.connect(self.stop_execution)
        run_menu.addAction(self.stop_action)

        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말(&H)")

        about_action = QAction("정보(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        """툴바 생성"""
        toolbar = self.addToolBar("메인")
        toolbar.setMovable(False)

        # 텔레그램 설정 버튼
        telegram_btn = QPushButton("텔레그램 설정")
        telegram_btn.setToolTip("텔레그램 밇 설정 및 연결")
        telegram_btn.clicked.connect(self.open_telegram_settings)
        toolbar.addWidget(telegram_btn)

        toolbar.addSeparator()

        # 실행 버튼
        self.run_btn = QPushButton("실행")
        self.run_btn.setObjectName("primary_button")
        self.run_btn.setToolTip("매크로 실행")
        self.run_btn.setEnabled(True)  # 항상 활성화
        self.run_btn.clicked.connect(self.run_main_sequence)
        toolbar.addWidget(self.run_btn)

        # 중지 버튼
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setObjectName("danger_button")
        self.stop_btn.setToolTip("매크로 실행 중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_execution)
        toolbar.addWidget(self.stop_btn)

    def create_main_panel(self) -> QWidget:
        """메인 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 액션 그룹
        action_group = QGroupBox("매크로 액션")
        action_group_layout = QVBoxLayout(action_group)

        # 액션 테이블
        self.action_table = QTableWidget()
        self.action_table.setColumnCount(4)
        self.action_table.setHorizontalHeaderLabels(["순서", "타입", "설명", "활성화"])

        # 테이블 편집 방지 및 행 선택 설정
        self.action_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.action_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.action_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # 시그널 연결
        self.action_table.itemSelectionChanged.connect(self.on_action_selected)
        self.action_table.itemDoubleClicked.connect(self.on_action_double_clicked)

        # 헤더 설정
        header = self.action_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 순서
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 타입
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 설명
        header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )  # 활성화

        # 행 높이 설정 (썸네일을 위해)
        self.action_table.verticalHeader().setDefaultSectionSize(30)

        action_group_layout.addWidget(self.action_table)

        # 액션 버튼들
        action_btn_layout = QHBoxLayout()

        self.add_action_btn = QPushButton("액션 추가")
        self.add_action_btn.setObjectName("success_button")
        self.add_action_btn.clicked.connect(self.add_action)
        action_btn_layout.addWidget(self.add_action_btn)

        self.edit_action_btn = QPushButton("액션 편집")
        self.edit_action_btn.setEnabled(False)
        self.edit_action_btn.clicked.connect(self.edit_action)
        action_btn_layout.addWidget(self.edit_action_btn)

        self.delete_action_btn = QPushButton("액션 삭제")
        self.delete_action_btn.setObjectName("danger_button")
        self.delete_action_btn.setEnabled(False)
        self.delete_action_btn.clicked.connect(self.delete_action)
        action_btn_layout.addWidget(self.delete_action_btn)

        # 구분선
        separator = QLabel(" | ")
        separator.setStyleSheet("color: #dee2e6; font-weight: bold;")
        action_btn_layout.addWidget(separator)

        # 순서 변경 버튼들
        self.move_up_btn = QPushButton("▲")
        self.move_up_btn.setToolTip("선택된 액션을 위로 이동")
        self.move_up_btn.setMaximumWidth(30)
        self.move_up_btn.setEnabled(False)
        self.move_up_btn.clicked.connect(self.move_action_up)
        action_btn_layout.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("▼")
        self.move_down_btn.setToolTip("선택된 액션을 아래로 이동")
        self.move_down_btn.setMaximumWidth(30)
        self.move_down_btn.setEnabled(False)
        self.move_down_btn.clicked.connect(self.move_action_down)
        action_btn_layout.addWidget(self.move_down_btn)

        action_btn_layout.addStretch()
        action_group_layout.addLayout(action_btn_layout)

        layout.addWidget(action_group)

        # 로그 그룹
        log_group = QGroupBox("실행 로그")
        log_group_layout = QVBoxLayout(log_group)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)  # 최대 1000줄
        log_group_layout.addWidget(self.log_text)

        # 로그 제어 버튼
        log_btn_layout = QHBoxLayout()

        clear_log_btn = QPushButton("로그 지우기")
        clear_log_btn.clicked.connect(self.clear_log)
        log_btn_layout.addWidget(clear_log_btn)

        save_log_btn = QPushButton("로그 저장")
        save_log_btn.clicked.connect(self.save_log)
        log_btn_layout.addWidget(save_log_btn)

        log_btn_layout.addStretch()
        log_group_layout.addLayout(log_btn_layout)

        layout.addWidget(log_group)

        return panel

    def create_status_bar(self):
        """상태바 생성"""
        status_bar = self.statusBar()

        # 상태 레이블
        self.status_label = QLabel("준비됨")
        status_bar.addWidget(self.status_label)

        # 통계 정보
        self.stats_label = QLabel()
        status_bar.addPermanentWidget(self.stats_label)

        self.update_stats()

    def apply_styles(self):
        """스타일 적용"""
        # 다크 테마 스타일 (선택사항)
        style = """
        QMainWindow {
            background-color: #f0f0f0;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        
        QPushButton {
            background-color: #e0e0e0;
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 5px 15px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #888888;
        }
        
        QListWidget::item {
            padding: 5px;
            border-bottom: 1px solid #eeeeee;
        }
        
        QListWidget::item:selected {
            background-color: #3498db;
            color: white;
        }
        
        QTableWidget {
            gridline-color: #dddddd;
            selection-background-color: #3498db;
        }
        """

        self.setStyleSheet(style)

    def setup_connections(self):
        """시그널/슬롯 연결"""
        # 매크로 엔진 시그널 연결 (스레드 안전)
        self.engine.sequence_started.connect(self.on_sequence_start)
        self.engine.sequence_completed.connect(self.on_sequence_complete)
        self.engine.action_executed.connect(self.on_action_execute)
        self.engine.engine_error.connect(self.on_engine_error)

        # 기존 콜백 방식도 유지 (하위 호환성)
        self.engine.on_sequence_start = self.on_sequence_start
        self.engine.on_sequence_complete = self.on_sequence_complete
        self.engine.on_action_execute = self.on_action_execute
        self.engine.on_error = self.on_engine_error

    def load_data(self):
        """데이터 로드"""
        try:
            # 설정 로드
            if not self.engine.load_config():
                self.add_log("설정 파일 로드 실패")

            # UI 업데이트
            self.refresh_action_table()
            self.update_stats()

            self.add_log("애플리케이션 시작됨")

        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            self.add_log(f"데이터 로드 실패: {e}")

    def refresh_action_table(self):
        """액션 테이블 새로고침"""
        self.action_table.setRowCount(0)

        # 메인 시퀀스 가져오기
        if not self.engine.config.macro_sequences:
            return

        sequence = self.engine.config.macro_sequences[
            0
        ]  # 첫 번째 시퀀스를 메인으로 사용
        self.action_table.setRowCount(len(sequence.actions))

        # 인덴트 레벨 계산
        indent_levels = self.calculate_action_indents(sequence.actions)

        for i, action in enumerate(sequence.actions):
            indent_level = indent_levels[i] if i < len(indent_levels) else 0

            # 순서
            order_item = QTableWidgetItem(str(i + 1))
            order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.action_table.setItem(i, 0, order_item)

            # 타입 (인덴트 적용)
            type_display = self.get_action_display_name(action, indent_level)
            type_item = QTableWidgetItem(type_display)
            # 구조적 요소들에 배경색 적용
            if action.action_type in [ActionType.IF, ActionType.ELSE, ActionType.LOOP]:
                type_item.setBackground(Qt.GlobalColor.lightGray)
            self.action_table.setItem(i, 1, type_item)

            # 설명 (기본 설명)
            description = action.description or "-"
            desc_item = QTableWidgetItem(description)
            self.action_table.setItem(i, 2, desc_item)

            # 활성화 체크박스
            enabled_checkbox = QCheckBox()
            enabled_checkbox.setChecked(action.enabled)
            enabled_checkbox.toggled.connect(
                lambda checked, aid=action.id: self.toggle_action_enabled(aid, checked)
            )
            self.action_table.setCellWidget(i, 3, enabled_checkbox)

    def get_action_description(self, action) -> str:
        """액션 설명 생성"""
        if action.action_type in [
            ActionType.IMAGE_CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
        ]:
            if action.click_position:
                return f"위치 ({action.click_position[0]}, {action.click_position[1]})"
            else:
                return "위치 미지정"

        elif action.action_type == ActionType.TYPE_TEXT:
            text = action.text_input or ""
            return f"텍스트 입력: {text[:30]}{'...' if len(text) > 30 else ''}"

        elif action.action_type == ActionType.KEY_PRESS:
            keys = action.key_combination or []
            return f"키 입력: {' + '.join(keys)}"

        elif action.action_type == ActionType.WAIT:
            return f"대기: {action.wait_seconds}초"

        elif action.action_type == ActionType.SEND_TELEGRAM:
            msg = action.telegram_message or ""
            return f"텔레그램: {msg[:30]}{'...' if len(msg) > 30 else ''}"

        elif action.action_type == ActionType.IF:
            condition_text = ""
            if action.condition_type:
                condition_map = {
                    "image_found": "이미지 발견 시",
                    "image_not_found": "이미지 미발견 시",
                    "always": "항상",
                }
                condition_text = condition_map.get(action.condition_type.value, "조건")
            return f"IF ({condition_text})"

        elif action.action_type == ActionType.ELSE:
            return "ELSE"

        elif action.action_type == ActionType.LOOP:
            if action.loop_count:
                return f"LOOP ({action.loop_count}회)"
            else:
                return "LOOP (무한)"

        else:
            return action.action_type.value

    def calculate_action_indents(self, actions) -> List[int]:
        """액션들의 인덴트 레벨을 계산"""
        indents = []
        current_level = 0

        for action in actions:
            if action.action_type == ActionType.IF:
                indents.append(current_level)
                current_level += 1
            elif action.action_type == ActionType.ELSE:
                # ELSE는 같은 레벨의 IF와 동일한 인덴트
                indents.append(current_level - 1 if current_level > 0 else 0)
            elif action.action_type == ActionType.LOOP:
                indents.append(current_level)
                current_level += 1
            else:
                indents.append(current_level)

        return indents

    def get_action_display_name(self, action, indent_level: int = 0) -> str:
        """인덴트가 적용된 액션 표시명 생성"""
        indent = "  " * indent_level  # 2칸씩 인덴트
        base_description = self.get_action_description(action)

        # 구조적 요소들은 특별한 표시 추가
        if action.action_type == ActionType.IF:
            return f"{indent}🔹 {base_description}"
        elif action.action_type == ActionType.ELSE:
            return f"{indent}🔸 {base_description}"
        elif action.action_type == ActionType.LOOP:
            return f"{indent}🔄 {base_description}"
        else:
            return f"{indent}{base_description}"

    def update_stats(self):
        """통계 정보 업데이트"""
        sequences = len(self.engine.config.macro_sequences)

        stats_text = f"시퀀스: {sequences}"
        self.stats_label.setText(stats_text)

    def update_status(self):
        """상태 업데이트"""
        if self.engine.is_running:
            if self.engine.current_sequence:
                self.status_label.setText(
                    f"실행 중: {self.engine.current_sequence.name}"
                )
            else:
                self.status_label.setText("실행 중...")
        else:
            self.status_label.setText("준비됨")

    def add_log(self, message: str):
        """로그 추가"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        self.log_text.appendPlainText(log_message)

        # 자동 스크롤
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # 이벤트 핸들러들

    def toggle_action_enabled(self, action_id: str, enabled: bool):
        """액션 활성화/비활성화 토글"""
        # 메인 시퀀스에서 액션 찾아서 업데이트
        if self.engine.config.macro_sequences:
            sequence = self.engine.config.macro_sequences[
                0
            ]  # 첫 번째 시퀀스를 메인으로 사용

            for action in sequence.actions:
                if action.id == action_id:
                    action.enabled = enabled
                    break

            self.engine.save_config()
            self.add_log(f"액션 {'활성화' if enabled else '비활성화'}: {action_id}")

    # 액션 메소드들
    def start_capture(self):
        """화면 캡쳐 시작 (바로 오버레이 표시)"""
        logger.info("화면 캡쳐 시작")

        if self.is_capturing:
            logger.warning("이미 캡쳐 중입니다")
            return

        try:
            self.is_capturing = True

            # 모든 QT 윈도우 숨기기 (액션 에디터 포함)
            self._hide_all_qt_windows()

            # 잠시 대기 후 오버레이 생성 (화면이 완전히 숨겨지도록)
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(200, self._create_capture_overlay)

        except Exception as e:
            logger.error(f"캡쳐 시작 실패: {e}")
            self.add_log(f"캡쳐 시작 실패: {e}")
            self.is_capturing = False
            # 오류 발생 시 윈도우 복원
            self._restore_all_qt_windows()

    def _create_capture_overlay(self):
        """캡쳐 오버레이 생성 (지연 실행)"""
        try:
            from .capture_dialog import ScreenOverlay
            from PyQt6.QtWidgets import QApplication

            logger.debug("캡쳐 오버레이 생성 시작")

            # 현재 화면 스크린샷 캡쳐 (윈도우들이 숨겨진 상태에서)
            screen = QApplication.primaryScreen()
            screenshot = screen.grabWindow(0)

            # HiDPI 디스플레이 지원을 위한 device pixel ratio 설정
            device_pixel_ratio = screen.devicePixelRatio()
            screenshot.setDevicePixelRatio(device_pixel_ratio)

            # 오버레이 생성
            self.capture_overlay = ScreenOverlay(screenshot)
            self.capture_overlay.selection_completed.connect(
                self.on_selection_completed
            )
            self.capture_overlay.capture_cancelled.connect(self.on_capture_cancelled)

            # 이벤트 처리 강제 실행
            QApplication.processEvents()

        except Exception as e:
            logger.error(f"오버레이 생성 실패: {e}")
            # 오류 발생 시 윈도우 복원
            self.is_capturing = False
            self._restore_all_qt_windows()

    def _hide_all_qt_windows(self):
        """모든 QT 윈도우 숨기기"""
        try:
            # 캡쳐 시작 전 현재 열려있는 윈도우들 저장
            self.hidden_windows = []

            # 메인 윈도우 숨기기
            if self.isVisible():
                self.hidden_windows.append(("main", self))
                self.hide()

            # 액션 에디터 숨기기
            if hasattr(self, "action_editors"):
                for editor in self.action_editors:
                    if editor.isVisible():
                        self.hidden_windows.append(("editor", editor))
                        editor.hide()

            # 모든 QDialog 윈도우 숨기기
            from PyQt6.QtWidgets import QApplication

            for widget in QApplication.allWidgets():
                if (
                    widget.isWindow()
                    and widget.isVisible()
                    and widget != self.capture_overlay
                ):
                    self.hidden_windows.append(("widget", widget))
                    widget.hide()

            logger.debug(f"숨겨진 윈도우 개수: {len(self.hidden_windows)}")

        except Exception as e:
            logger.error(f"윈도우 숨기기 실패: {e}")

    def _restore_all_qt_windows(self):
        """모든 QT 윈도우 복원"""
        try:
            if hasattr(self, "hidden_windows"):
                for window_type, window in self.hidden_windows:
                    try:
                        if window and hasattr(window, "show"):
                            window.show()
                            if window_type == "main":
                                window.raise_()
                                window.activateWindow()
                    except Exception as e:
                        logger.error(f"윈도우 복원 실패 ({window_type}): {e}")

                self.hidden_windows = []
                logger.debug("모든 윈도우 복원 완료")

        except Exception as e:
            logger.error(f"윈도우 복원 실패: {e}")

    def on_selection_completed(self, rect):
        """오버레이에서 영역 선택 완료"""
        try:

            logger.info(f"영역 선택 완료: {rect}")

            # 오버레이 닫기
            if hasattr(self, "capture_overlay") and self.capture_overlay:
                self.capture_overlay.close()
                self.capture_overlay = None

            # 윈도우 복원
            self._restore_all_qt_windows()

            # 선택 영역이 유효한지 확인
            if rect.isEmpty() or rect.width() < 10 or rect.height() < 10:
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.warning(self, "경고", "선택한 영역이 너무 작습니다.")
                self.is_capturing = False
                return

            # 자동으로 템플릿 저장 (UUID 기반 이름)
            self._auto_save_template(rect)

        except Exception as e:
            logger.error(f"영역 선택 처리 실패: {e}")
            self.is_capturing = False
            self._restore_all_qt_windows()

    def on_capture_cancelled(self):
        """오버레이에서 캡쳐 취소됨"""
        try:
            logger.info("사용자가 캡쳐를 취소했습니다")

            # 오버레이 닫기
            if hasattr(self, "capture_overlay") and self.capture_overlay:
                self.capture_overlay.close()
                self.capture_overlay = None

            # 윈도우 복원
            self._restore_all_qt_windows()
            self.is_capturing = False

        except Exception as e:
            logger.error(f"캡쳐 취소 처리 실패: {e}")
            self.is_capturing = False
            self._restore_all_qt_windows()

    def _auto_save_template(self, rect):
        """자동으로 템플릿 저장 (UUID 기반 이름)"""
        try:
            import uuid
            from pathlib import Path
            from PyQt6.QtWidgets import QApplication
            from ..models.macro_models import CaptureRegion, ImageTemplate

            if not self.engine:
                logger.error("매크로 엔진이 연결되지 않았습니다")
                self.is_capturing = False
                return

            # UUID 기반 자동 이름 생성
            template_id = str(uuid.uuid4())
            template_name = f"template_{template_id[:8]}"

            # 기본 임계값 사용
            threshold = 0.8

            # 스크린샷 캡쳐
            screen = QApplication.primaryScreen()
            screenshot = screen.grabWindow(
                0, rect.x(), rect.y(), rect.width(), rect.height()
            )

            if screenshot.isNull():
                logger.error("스크린샷 캡쳐에 실패했습니다")
                self.is_capturing = False
                return

            # 파일 저장
            screenshot_dir = Path(self.engine.config.screenshot_save_path)
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            file_name = f"{template_name}.png"
            file_path = screenshot_dir / file_name

            if not screenshot.save(str(file_path), "PNG"):
                logger.error("이미지 저장에 실패했습니다")
                self.is_capturing = False
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

            logger.info(f"이미지 템플릿 자동 생성됨: {template_name} ({file_path})")

            # 캡쳐 완료 처리 (액션 에디터에 알림)
            self.on_capture_completed(template_id, template_name)

        except Exception as e:
            logger.error(f"자동 템플릿 저장 실패: {e}")
            self.is_capturing = False

    def on_capture_completed(self, template_id: str, template_name: str):
        """캡쳐 완료 시"""
        self.is_capturing = False

        # 모든 윈도우 복원
        self._restore_all_qt_windows()

        self.add_log(f"이미지 템플릿 추가됨: {template_name}")

        # 등록된 액션 에디터들에게 알림
        notified_editors = []
        for editor in self.action_editors[:]:  # 복사본으로 순회
            # 액션 에디터 유효성 검사
            if not self._is_widget_valid(editor):
                # 유효하지 않은 에디터는 목록에서 제거
                try:
                    self.action_editors.remove(editor)
                except ValueError:
                    pass  # 이미 제거됨
                continue

            if hasattr(editor, "on_capture_completed"):
                try:
                    # 안전한 메서드 호출
                    QTimer.singleShot(
                        0,
                        lambda e=editor: self._safe_notify_capture_completion(
                            e, template_id, template_name
                        ),
                    )
                    notified_editors.append(editor)
                except Exception as e:
                    logger.error(f"액션 에디터 캡쳐 완료 알림 실패: {e}")
                    # 오류 발생한 에디터는 목록에서 제거
                    try:
                        self.action_editors.remove(editor)
                    except ValueError:
                        pass

        # 등록된 액션 에디터가 없으면 새로운 액션 에디터 다이얼로그 생성
        if not notified_editors:
            QTimer.singleShot(
                100, lambda: self._create_new_action_editor(template_id, template_name)
            )

    def _is_widget_valid(self, widget) -> bool:
        """위젯이 유효한지 확인"""
        try:
            # 위젯이 None이거나 C++ 객체가 삭제되었는지 확인
            if widget is None:
                return False

            # Qt 객체가 삭제되었는지 확인하는 방법들
            # 1. 기본 속성 접근 시도
            _ = widget.isVisible()

            # 2. 부모 위젯 확인
            _ = widget.parent()

            return True

        except (RuntimeError, AttributeError):
            # "wrapped C/C++ object has been deleted" 오류나 속성 오류
            return False

    def _create_new_action_editor(self, template_id: str, template_name: str):
        """새로운 액션 에디터 다이얼로그 생성"""
        try:
            from .action_editor import ActionEditor
            from ..models.macro_models import MacroAction, ActionType

            # 새 액션 생성 (클릭 액션으로 기본 설정)
            action = MacroAction(
                id=str(uuid.uuid4()),
                action_type=ActionType.IMAGE_CLICK,
                image_template_id=template_id,
            )

            # 액션 에디터 다이얼로그 생성
            editor = ActionEditor(parent=self, action=action)

            # 액션 에디터를 목록에 추가
            self.action_editors.append(editor)

            # 에디터가 닫힐 때 목록에서 제거되도록 연결
            editor.destroyed.connect(lambda: self._remove_action_editor(editor))

            # 액션 저장 시그널 연결
            if hasattr(editor, "action_saved"):
                editor.action_saved.connect(self._on_action_saved_from_capture)

            # 캡쳐 완료 이벤트 전달
            if hasattr(editor, "on_capture_completed"):
                editor.on_capture_completed(template_id, template_name)

            # 다이얼로그 표시
            editor.show()
            editor.raise_()
            editor.activateWindow()

            logger.info(f"새로운 액션 에디터 다이얼로그 생성: {template_name}")

        except Exception as e:
            logger.error(f"액션 에디터 다이얼로그 생성 실패: {e}")

    def _on_action_saved_from_capture(self, action):
        """캡쳐로부터 생성된 액션이 저장되었을 때"""
        try:
            # 메인 시퀀스에 액션 추가
            if not self.engine.config.macro_sequences:
                from ..models.macro_models import MacroSequence

                sequence = MacroSequence(
                    id="main_sequence",
                    name="메인 시퀀스",
                    description="기본 매크로 시퀀스",
                )
                self.engine.config.add_macro_sequence(sequence)

            # 첫 번째 시퀀스에 액션 추가
            main_sequence = self.engine.config.macro_sequences[0]
            main_sequence.add_action(action)
            self.engine.save_config()

            # UI 업데이트
            self.refresh_action_table()

            logger.info(f"캡쳐된 액션이 메인 시퀀스에 추가됨: {action}")
            self.add_log(f"액션이 추가됨: {action.action_type.value}")

        except Exception as e:
            logger.error(f"캡쳐된 액션 저장 처리 실패: {e}")

    def _remove_action_editor(self, editor):
        """액션 에디터를 목록에서 제거"""
        try:
            if editor in self.action_editors:
                self.action_editors.remove(editor)
                logger.debug("액션 에디터가 목록에서 제거됨")
        except (ValueError, RuntimeError):
            # 이미 제거되었거나 객체가 삭제됨
            pass

    def _safe_notify_capture_completion(
        self, editor, template_id: str, template_name: str
    ):
        """안전한 캡쳐 완료 알림"""
        try:
            # 다시 한번 유효성 검사
            if not self._is_widget_valid(editor):
                try:
                    self.action_editors.remove(editor)
                except ValueError:
                    pass
                return

            # 안전한 메서드 호출
            if hasattr(editor, "on_capture_completed"):
                editor.on_capture_completed(template_id, template_name)

        except Exception as e:
            logger.error(f"캡쳐 완료 알림 중 오류: {e}")
            # 오류 발생한 에디터는 목록에서 제거
            try:
                self.action_editors.remove(editor)
            except ValueError:
                pass

    def register_action_editor(self, editor):
        """액션 에디터 등록"""
        if editor not in self.action_editors:
            self.action_editors.append(editor)

            # 에디터가 닫힐 때 자동으로 등록 해제하도록 연결
            if hasattr(editor, "finished"):
                editor.finished.connect(lambda: self.unregister_action_editor(editor))

            # destroyed 시그널도 연결하여 더 안전하게 처리
            editor.destroyed.connect(lambda: self._remove_action_editor(editor))

    def unregister_action_editor(self, editor):
        """액션 에디터 등록 해제"""
        try:
            if editor in self.action_editors:
                self.action_editors.remove(editor)
                logger.debug(f"액션 에디터 등록 해제됨")
        except (ValueError, RuntimeError):
            # 이미 제거되었거나 객체가 삭제됨
            pass

    def on_action_selected(self):
        """액션 선택 시 (스레드 안전)"""
        selected_rows = set(item.row() for item in self.action_table.selectedItems())
        has_selection = len(selected_rows) > 0

        # 메인 스레드에서 실행되도록 예약
        QTimer.singleShot(0, lambda sel=has_selection: self._update_action_buttons(sel))

    def on_action_double_clicked(self, item):
        """테이블 행 더블클릭 시 액션 편집"""
        if item is None:
            return

        row = item.row()

        # 체크박스 열은 편집 다이얼로그를 열지 않음
        if item.column() == 4:  # 활성화 체크박스 열
            return

        # 액션 편집 호출
        self._edit_action_by_row(row)

    def _edit_action_by_row(self, row: int):
        """지정된 행의 액션 편집"""
        try:
            if not self.engine.config.macro_sequences:
                return

            sequence = self.engine.config.macro_sequences[0]
            if row >= len(sequence.actions):
                return

            action = sequence.actions[row]

            # 액션 에디터 다이얼로그 열기 (편집 모드)
            from .action_editor import ActionEditor

            dialog = ActionEditor(self, action)
            dialog.action_saved.connect(
                lambda updated_action: self.on_action_edited(row, updated_action)
            )
            dialog.capture_requested.connect(self.start_capture)

            # 액션 에디터 등록 (캡쳐 완료 알림용)
            self.register_action_editor(dialog)

            # 모달 대화상자로 열기
            dialog.exec()

        except Exception as e:
            logger.error(f"액션 편집 실패: {e}")
            QMessageBox.critical(self, "오류", f"액션을 편집할 수 없습니다: {e}")

    def _update_action_buttons(self, has_selection: bool):
        """액션 버튼 상태 업데이트 (메인 스레드에서 실행)"""
        self.edit_action_btn.setEnabled(has_selection)
        self.delete_action_btn.setEnabled(has_selection)

        # 순서 변경 버튼 상태 업데이트
        if has_selection:
            selected_rows = [item.row() for item in self.action_table.selectedItems()]
            if selected_rows:
                current_row = min(selected_rows)  # 첫 번째 선택된 행
                row_count = self.action_table.rowCount()

                # 위로 이동: 첫 번째 행이 아닐 때 활성화
                self.move_up_btn.setEnabled(current_row > 0)
                # 아래로 이동: 마지막 행이 아닐 때 활성화
                self.move_down_btn.setEnabled(current_row < row_count - 1)
            else:
                self.move_up_btn.setEnabled(False)
                self.move_down_btn.setEnabled(False)
        else:
            self.move_up_btn.setEnabled(False)
            self.move_down_btn.setEnabled(False)

    def add_action(self):
        """액션 추가"""
        try:
            # 메인 시퀀스가 없으면 생성
            if not self.engine.config.macro_sequences:
                from ..models.macro_models import MacroSequence

                sequence = MacroSequence(
                    id="main_sequence",
                    name="메인 시퀀스",
                    description="기본 매크로 시퀀스",
                )
                self.engine.config.add_macro_sequence(sequence)
                self.engine.save_config()

            # 액션 에디터 다이얼로그 열기
            from .action_editor import ActionEditor

            dialog = ActionEditor(self)
            dialog.action_saved.connect(self.on_action_added)
            dialog.capture_requested.connect(self.start_capture)

            # 액션 에디터 등록 (캡쳐 완료 알림용)
            self.register_action_editor(dialog)

            # 모달 대화상자로 열기
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                # 다이얼로그가 성공적으로 닫힘
                pass

        except Exception as e:
            logger.error(f"액션 추가 실패: {e}")
            QMessageBox.critical(self, "오류", f"액션을 추가할 수 없습니다: {e}")

    def edit_action(self):
        """액션 편집"""
        selected_rows = set(item.row() for item in self.action_table.selectedItems())
        if not selected_rows:
            return

        try:
            # 선택된 첫 번째 행의 액션 가져오기
            row = min(selected_rows)
            if not self.engine.config.macro_sequences:
                return

            sequence = self.engine.config.macro_sequences[0]
            if row >= len(sequence.actions):
                return

            action = sequence.actions[row]

            # 액션 에디터 다이얼로그 열기 (편집 모드)
            from .action_editor import ActionEditor

            dialog = ActionEditor(self, action)
            dialog.action_saved.connect(
                lambda updated_action: self.on_action_edited(row, updated_action)
            )
            dialog.capture_requested.connect(self.start_capture)

            # 액션 에디터 등록 (캡쳐 완료 알림용)
            self.register_action_editor(dialog)

            # 모달 대화상자로 열기
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                # 다이얼로그가 성공적으로 닫힘
                pass

        except Exception as e:
            logger.error(f"액션 편집 실패: {e}")
            QMessageBox.critical(self, "오류", f"액션을 편집할 수 없습니다: {e}")

    def delete_action(self):
        """액션 삭제"""
        selected_rows = set(item.row() for item in self.action_table.selectedItems())
        if not selected_rows:
            return

        reply = QMessageBox.question(
            self,
            "액션 삭제",
            f"선택된 액션을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 메인 시퀀스 가져오기
                if self.engine.config.macro_sequences:
                    sequence = self.engine.config.macro_sequences[0]

                    # 선택된 행들을 역순으로 정렬해서 삭제 (인덱스 변화 방지)
                    for row in sorted(selected_rows, reverse=True):
                        if row < len(sequence.actions):
                            removed_action = sequence.actions.pop(row)
                            self.add_log(
                                f"액션 삭제됨: {removed_action.action_type.value}"
                            )

                    self.engine.save_config()
                    self.refresh_action_table()
                    self.update_stats()

            except Exception as e:
                logger.error(f"액션 삭제 실패: {e}")
                QMessageBox.critical(self, "오류", f"액션을 삭제할 수 없습니다: {e}")

    def move_action_up(self):
        """선택된 액션을 위로 이동"""
        selected_rows = [item.row() for item in self.action_table.selectedItems()]
        if not selected_rows:
            return

        current_row = min(selected_rows)
        if current_row <= 0:
            return

        try:
            # 메인 시퀀스 가져오기
            if self.engine.config.macro_sequences:
                sequence = self.engine.config.macro_sequences[0]

                if current_row < len(sequence.actions):
                    # 액션 순서 교체
                    sequence.actions[current_row], sequence.actions[current_row - 1] = (
                        sequence.actions[current_row - 1],
                        sequence.actions[current_row],
                    )

                    self.engine.save_config()
                    self.refresh_action_table()

                    # 이동된 액션 다시 선택
                    self.action_table.selectRow(current_row - 1)

                    self.add_log(
                        f"액션이 위로 이동됨 (위치: {current_row} → {current_row - 1})"
                    )

        except Exception as e:
            logger.error(f"액션 이동 실패: {e}")
            QMessageBox.critical(self, "오류", f"액션을 이동할 수 없습니다: {e}")

    def move_action_down(self):
        """선택된 액션을 아래로 이동"""
        selected_rows = [item.row() for item in self.action_table.selectedItems()]
        if not selected_rows:
            return

        current_row = min(selected_rows)

        try:
            # 메인 시퀀스 가져오기
            if self.engine.config.macro_sequences:
                sequence = self.engine.config.macro_sequences[0]

                if current_row >= len(sequence.actions) - 1:
                    return

                # 액션 순서 교체
                sequence.actions[current_row], sequence.actions[current_row + 1] = (
                    sequence.actions[current_row + 1],
                    sequence.actions[current_row],
                )

                self.engine.save_config()
                self.refresh_action_table()

                # 이동된 액션 다시 선택
                self.action_table.selectRow(current_row + 1)

                self.add_log(
                    f"액션이 아래로 이동됨 (위치: {current_row} → {current_row + 1})"
                )

        except Exception as e:
            logger.error(f"액션 이동 실패: {e}")
            QMessageBox.critical(self, "오류", f"액션을 이동할 수 없습니다: {e}")

    def on_action_added(self, action):
        """액션 추가 완료 시"""
        try:
            # 메인 시퀀스에 액션 추가
            if self.engine.config.macro_sequences:
                sequence = self.engine.config.macro_sequences[0]
                sequence.add_action(action)

                self.engine.save_config()
                self.refresh_action_table()
                self.update_stats()

                # 설명 포함한 로그
                description = getattr(action, "description", "") or ""
                log_text = f"액션 추가됨: {action.action_type.value}"
                if description:
                    log_text += f" ({description})"
                self.add_log(log_text)

        except Exception as e:
            logger.error(f"액션 추가 저장 실패: {e}")
            QMessageBox.critical(self, "오류", f"액션을 저장할 수 없습니다: {e}")

    def refresh_action_table(self):
        """액션 테이블 새로고침"""
        try:
            # 테이블 초기화
            self.action_table.setRowCount(0)

            if not self.engine.config.macro_sequences:
                return

            # 메인 시퀀스의 액션들 표시
            sequence = self.engine.config.macro_sequences[0]
            actions = sequence.actions

            self.action_table.setRowCount(len(actions))

            # 액션 타입 한글 매핑
            type_map = {
                ActionType.IMAGE_CLICK: "클릭",
                ActionType.DOUBLE_CLICK: "더블클릭",
                ActionType.RIGHT_CLICK: "우클릭",
                ActionType.TYPE_TEXT: "텍스트 입력",
                ActionType.KEY_PRESS: "키 입력",
                ActionType.WAIT: "대기",
                ActionType.SEND_TELEGRAM: "텔레그램 전송",
            }

            for i, action in enumerate(actions):
                # 순서
                from PyQt6.QtWidgets import QTableWidgetItem
                from PyQt6.QtCore import Qt

                order_item = QTableWidgetItem(str(i + 1))
                order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.action_table.setItem(i, 0, order_item)

                # 타입
                type_text = type_map.get(action.action_type, action.action_type.value)
                type_item = QTableWidgetItem(type_text)
                self.action_table.setItem(i, 1, type_item)

                # 설명
                description = getattr(action, "description", "") or ""
                description_item = QTableWidgetItem(description)
                self.action_table.setItem(i, 2, description_item)

                # 활성화 상태
                enabled_text = "✓" if action.enabled else "✗"
                enabled_item = QTableWidgetItem(enabled_text)
                enabled_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.action_table.setItem(i, 3, enabled_item)

        except Exception as e:
            logger.error(f"액션 테이블 새로고침 실패: {e}")

    def on_action_edited(self, row, updated_action):
        """액션 편집 완료 시"""
        try:
            # 메인 시퀀스의 액션 업데이트
            if self.engine.config.macro_sequences:
                sequence = self.engine.config.macro_sequences[0]
                if row < len(sequence.actions):
                    sequence.actions[row] = updated_action

                    self.engine.save_config()
                    self.refresh_action_table()

                    self.add_log(f"액션 수정됨: {updated_action.action_type.value}")

        except Exception as e:
            logger.error(f"액션 편집 저장 실패: {e}")
            QMessageBox.critical(self, "오류", f"액션을 저장할 수 없습니다: {e}")

    def run_main_sequence(self):
        """메인 시퀀스 실행"""
        if self.engine.is_running:
            QMessageBox.warning(self, "경고", "다른 매크로가 실행 중입니다.")
            return

        # 메인 시퀀스 가져오기 (첫 번째 시퀀스 또는 기본 시퀀스)
        if not self.engine.config.macro_sequences:
            QMessageBox.warning(self, "경고", "실행할 시퀀스가 없습니다.")
            return

        sequence = self.engine.config.macro_sequences[
            0
        ]  # 첫 번째 시퀀스를 메인으로 사용

        if not sequence or not sequence.enabled:
            QMessageBox.warning(self, "경고", "비활성화된 시퀀스입니다.")
            return

        try:
            # UI 상태 업데이트
            self.run_btn.setEnabled(False)
            self.run_action.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.stop_action.setEnabled(True)

            self.add_log(f"매크로 시퀀스 실행 시작: {sequence.name}")

            # 매크로 실행 전 창 숨기기
            logger.debug("매크로 실행을 위해 메인 윈도우 숨김")
            self.hide()

            # 화면이 업데이트되기를 잠시 기다림
            QApplication.processEvents()
            QTimer.singleShot(
                100, lambda seq=sequence: self._start_macro_execution(seq)
            )

        except Exception as e:
            logger.error(f"시퀀스 실행 실패: {e}")
            self.show()  # 오류 발생 시 창 다시 표시
            QMessageBox.critical(self, "오류", f"시퀀스를 실행할 수 없습니다: {e}")
            self.reset_execution_ui()

    def _start_macro_execution(self, sequence):
        """실제 매크로 실행 (지연 실행)"""
        try:
            # 비동기 실행
            self.engine.execute_sequence_async(sequence.id)
        except Exception as e:
            logger.error(f"매크로 실행 실패: {e}")
            self.show()  # 오류 발생 시 창 다시 표시
            self.reset_execution_ui()

    def stop_execution(self):
        """매크로 실행 중지"""
        if self.engine.is_running:
            self.engine.stop_execution()
            self.add_log("매크로 실행 중지 요청됨")

            # 매크로 중지 후 창 다시 표시
            if self.isHidden():
                self.show()
                self.raise_()
                self.activateWindow()

    def reset_execution_ui(self):
        """실행 UI 초기화 (스레드 안전)"""
        # 메인 스레드에서 실행되도록 예약
        QTimer.singleShot(0, self._reset_execution_ui_impl)

    def _reset_execution_ui_impl(self):
        """실행 UI 초기화 실제 구현 (메인 스레드에서 실행)"""
        try:
            # 버튼 상태 복원
            self.run_btn.setEnabled(True)
            self.run_action.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.stop_action.setEnabled(False)

            # 창이 숨겨져 있다면 다시 표시
            if self.isHidden():
                logger.debug("메인 윈도우 복원 중...")
                self.show()
                self.raise_()
                self.activateWindow()

                # 잠시 후 다시 한번 확실히 활성화
                QTimer.singleShot(100, self._ensure_window_visible)

        except Exception as e:
            logger.error(f"UI 초기화 중 오류: {e}")

    def _ensure_window_visible(self):
        """윈도우가 확실히 보이도록 보장"""
        try:
            if not self.isActiveWindow():
                self.raise_()
                self.activateWindow()
                logger.debug("윈도우 활성화 재시도 완료")
        except Exception as e:
            logger.error(f"윈도우 활성화 재시도 실패: {e}")

    def clear_log(self):
        """로그 지우기"""
        self.log_text.clear()

    def save_log(self):
        """로그 저장"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "로그 저장", "macro_log.txt", "텍스트 파일 (*.txt)"
            )

            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.log_text.toPlainText())

                self.add_log(f"로그 저장됨: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "오류", f"로그 저장 실패: {e}")

    def new_config(self):
        """새 설정"""
        reply = QMessageBox.question(
            self,
            "새 설정",
            "현재 설정을 저장하지 않고 새로 시작하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.engine.config = self.engine.config.__class__()
            self.refresh_action_table()
            self.update_stats()
            self.add_log("새 설정으로 시작됨")

    def open_config(self):
        """설정 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "설정 파일 열기", "", "JSON 파일 (*.json)"
        )

        if file_path:
            try:
                self.engine.config_path = file_path
                if self.engine.load_config():
                    self.refresh_action_table()
                    self.update_stats()
                    self.add_log(f"설정 파일 로드됨: {file_path}")
                else:
                    QMessageBox.critical(
                        self, "오류", "설정 파일을 로드할 수 없습니다."
                    )
            except Exception as e:
                QMessageBox.critical(self, "오류", f"설정 파일 로드 실패: {e}")

    def save_config(self):
        """설정 저장"""
        try:
            self.engine.save_config()
            self.add_log("설정 저장됨")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 실패: {e}")

    def open_settings(self):
        """설정 다이얼로그 열기"""
        try:
            if not self.settings_dialog:
                from .settings_dialog import SettingsDialog

                self.settings_dialog = SettingsDialog(self, self.engine)
                self.settings_dialog.settings_changed.connect(self.on_settings_changed)

            self.settings_dialog.show()

        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 다이얼로그를 열 수 없습니다: {e}")

    def open_telegram_settings(self):
        """텔레그램 설정 다이얼로그 열기"""
        try:
            if not self.telegram_dialog:
                from .telegram_settings import TelegramSettingsDialog

                self.telegram_dialog = TelegramSettingsDialog(self, self.engine)
                self.telegram_dialog.settings_changed.connect(
                    self.on_telegram_settings_changed
                )

            self.telegram_dialog.show()

        except Exception as e:
            QMessageBox.critical(
                self, "오류", f"텔레그램 설정 다이얼로그를 열 수 없습니다: {e}"
            )

    def on_settings_changed(self):
        """설정 변경 시"""
        self.add_log("설정이 변경되었습니다")

    def on_telegram_settings_changed(self):
        """텔레그램 설정 변경 시"""
        self.add_log("텔레그램 설정이 변경되었습니다")

    def show_about(self):
        """정보 다이얼로그"""
        QMessageBox.about(
            self,
            "KTX Macro V2 정보",
            "KTX Macro V2\n\n"
            "이미지 매칭 기반 매크로 자동화 도구\n"
            "버전: 0.1.0\n\n"
            "주요 기능:\n"
            "• 화면 캡쳐 및 이미지 매칭\n"
            "• 마우스/키보드 자동화\n"
            "• 매크로 시퀀스 관리\n"
            "• 텔레그램 알림 연동\n\n"
            "© 2024 KTX Macro Team",
        )

    # 매크로 엔진 콜백
    def on_sequence_start(self, sequence_id: str):
        """시퀀스 시작 시"""
        sequence = self.engine.config.get_macro_sequence(sequence_id)
        if sequence:
            self.add_log(f"시퀀스 시작: {sequence.name}")

    def on_sequence_complete(self, sequence_id: str, result: MacroExecutionResult):
        """시퀀스 완료 시 (이미 메인 스레드에서 호출됨)"""
        logger.debug(f"시퀀스 완료: {sequence_id} {result = }")
        # MacroEngine에서 이미 메인 스레드로 전달했으므로 직접 호출
        self._on_sequence_complete_impl(sequence_id, result)

    def _on_sequence_complete_impl(
        self, sequence_id: str, result: MacroExecutionResult
    ):
        logger.debug(f"_on_sequence_complete_impl 시퀀스 완료: {sequence_id}")
        """시퀀스 완료 시 실제 구현 (메인 스레드에서 실행)"""
        try:
            # 매크로 완료 후 창 다시 표시
            if self.isHidden():
                self.show()
                self.raise_()
                self.activateWindow()

            sequence = self.engine.config.get_macro_sequence(sequence_id)
            sequence_name = sequence.name if sequence else "알 수 없음"

            status = "성공" if result.success else "실패"
            self.add_log(
                f"시퀀스 완료: {sequence_name} - {status} "
                f"({result.steps_executed}/{result.total_steps} 단계, "
                f"{result.execution_time:.2f}초)"
            )

            if not result.success and result.error_message:
                self.add_log(f"오류: {result.error_message}")

            # UI 리셋
            self.reset_execution_ui()

            # 완료 팝업을 지연해서 표시 (UI 복원 후)
            QTimer.singleShot(
                200, lambda: self._show_completion_popup(sequence_name, result)
            )

        except Exception as e:
            logger.error(f"시퀀스 완료 처리 중 오류: {e}")
            # 오류 발생 시에도 UI는 복원
            self.reset_execution_ui()
            if self.isHidden():
                self.show()
                self.raise_()
                self.activateWindow()

    def _show_completion_popup(self, sequence_name: str, result: MacroExecutionResult):
        """시퀀스 완료 팝업 표시"""
        try:
            # 메인 윈도우가 확실히 보이고 활성화되었는지 확인
            if self.isHidden():
                self.show()

            self.raise_()
            self.activateWindow()

            # 이벤트 처리 허용
            QApplication.processEvents()

            # 성공/실패에 따른 메시지 설정
            if result.success:
                title = "매크로 실행 완료"
                icon = QMessageBox.Icon.Information
                message = (
                    f"시퀀스 '{sequence_name}'이(가) 성공적으로 완료되었습니다!\n\n"
                    f"실행된 단계: {result.steps_executed}/{result.total_steps}\n"
                    f"실행 시간: {result.execution_time:.2f}초"
                )
            else:
                title = "매크로 실행 실패"
                icon = QMessageBox.Icon.Warning
                message = (
                    f"시퀀스 '{sequence_name}' 실행 중 오류가 발생했습니다.\n\n"
                    f"실행된 단계: {result.steps_executed}/{result.total_steps}\n"
                    f"실행 시간: {result.execution_time:.2f}초"
                )
                if result.error_message:
                    message += f"\n\n오류 내용: {result.error_message}"

            # 팝업 표시
            msg_box = QMessageBox(self)
            msg_box.setIcon(icon)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

            # 팝업 윈도우 설정
            msg_box.setWindowFlags(
                msg_box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )

            # 팝업을 중앙에 위치시키기
            if self.isVisible():
                msg_box.move(
                    self.x() + (self.width() - msg_box.width()) // 2,
                    self.y() + (self.height() - msg_box.height()) // 2,
                )

            logger.debug(f"완료 팝업 표시: {title}")

            # 팝업을 모달로 표시
            result_code = msg_box.exec()

            logger.debug(f"완료 팝업 닫힘: {result_code}")

        except Exception as e:
            logger.error(f"완료 팝업 표시 중 오류: {e}")
            # 팝업 표시 실패 시 로그로라도 알림
            if result.success:
                self.add_log(f"✅ 매크로 실행 완료: {sequence_name}")
            else:
                self.add_log(f"❌ 매크로 실행 실패: {sequence_name}")

    def on_action_execute(self, sequence_id: str, action):
        """액션 실행 시 (이미 메인 스레드에서 호출됨)"""
        # MacroEngine에서 이미 메인 스레드로 전달했으므로 직접 호출
        self.add_log(f"액션 실행: {action.action_type.value}")

    def on_engine_error(self, sequence_id: str, error: Exception):
        """엔진 오류 시"""
        self.add_log(f"엔진 오류: {error}")
        logger.error(f"매크로 엔진 오류: {error}")

    def closeEvent(self, event):
        """윈도우 종료 시"""
        if self.engine.is_running:
            reply = QMessageBox.question(
                self,
                "종료 확인",
                "매크로가 실행 중입니다. 강제로 종료하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            # 매크로 중지
            self.engine.stop_execution()

        # 리소스 정리
        try:
            self.engine.cleanup()
            self.add_log("애플리케이션 종료됨")
        except Exception as e:
            logger.error(f"종료 시 오류: {e}")

        event.accept()

    def get_global_stylesheet(self) -> str:
        """전역 스타일시트 반환"""
        return """
        /* 기본 버튼 스타일 */
        QPushButton {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            color: #495057;
            min-height: 20px;
        }
        
        /* 버튼 호버 상태 */
        QPushButton:hover:enabled {
            background-color: #e9ecef;
            border-color: #adb5bd;
        }
        
        /* 버튼 활성(눌림) 상태 */
        QPushButton:pressed:enabled {
            background-color: #007bff;
            border-color: #0056b3;
            color: white;
        }
        
        /* 버튼 비활성화 상태 */
        QPushButton:disabled {
            background-color: #e9ecef;
            border-color: #dee2e6;
            color: #6c757d;
        }
        
        /* 비활성화된 버튼 호버 방지 */
        QPushButton:disabled:hover {
            background-color: #e9ecef;
            border-color: #dee2e6;
        }
        
        /* 주요 액션 버튼 스타일 */
        QPushButton#primary_button {
            background-color: #007bff;
            border-color: #007bff;
            color: white;
        }
        
        QPushButton#primary_button:hover:enabled {
            background-color: #0056b3;
            border-color: #004085;
        }
        
        QPushButton#primary_button:pressed:enabled {
            background-color: #004085;
            border-color: #002752;
        }
        
        /* 위험 액션 버튼 스타일 */
        QPushButton#danger_button {
            background-color: #dc3545;
            border-color: #dc3545;
            color: white;
        }
        
        QPushButton#danger_button:hover:enabled {
            background-color: #c82333;
            border-color: #bd2130;
        }
        
        QPushButton#danger_button:pressed:enabled {
            background-color: #bd2130;
            border-color: #b21f2d;
        }
        
        /* 성공 액션 버튼 스타일 */
        QPushButton#success_button {
            background-color: #28a745;
            border-color: #28a745;
            color: white;
        }
        
        QPushButton#success_button:hover:enabled {
            background-color: #218838;
            border-color: #1e7e34;
        }
        
        QPushButton#success_button:pressed:enabled {
            background-color: #1e7e34;
            border-color: #1c7430;
        }
        
        /* 테이블 스타일 */
        QTableWidget {
            border: 1px solid #dee2e6;
            border-radius: 4px;
            background-color: white;
            gridline-color: #dee2e6;
        }
        
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
        }
        
        QTableWidget::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        
        /* 리스트 위젯 스타일 */
        QListWidget {
            border: 1px solid #dee2e6;
            border-radius: 4px;
            background-color: white;
        }
        
        QListWidget::item {
            padding: 8px;
            border-bottom: 1px solid #f8f9fa;
        }
        
        QListWidget::item:selected {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        
        QListWidget::item:hover {
            background-color: #f8f9fa;
        }
        """
