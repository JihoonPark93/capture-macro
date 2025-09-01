"""
메인 윈도우 GUI
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QPushButton,
    QLabel,
    QProgressBar,
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
    QScrollArea,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QRect
from PyQt6.QtGui import (
    QAction,
    QIcon,
    QPixmap,
    QKeySequence,
)

from ..core.macro_engine import MacroEngine, MacroExecutionResult
from ..models.macro_models import ActionType
from ..utils.logger import get_logger
from .capture_dialog import CaptureDialog
from .sequence_editor import SequenceEditor
from .settings_dialog import SettingsDialog
from .telegram_settings import TelegramSettingsDialog

logger = get_logger(__name__)


class ImagePreviewDialog(QDialog):
    """이미지 미리보기 다이얼로그"""

    def __init__(self, image_path: str, template_name: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.template_name = template_name
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle(f"이미지 미리보기 - {self.template_name}")
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # 메인 레이아웃
        layout = QVBoxLayout(self)

        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 이미지 라벨
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            "border: 1px solid #dee2e6; background-color: white;"
        )

        scroll_area.setWidget(self.image_label)
        layout.addWidget(scroll_area)

        # 정보 라벨
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(
            "padding: 10px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;"
        )
        layout.addWidget(self.info_label)

        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("닫기")
        close_btn.setObjectName("primary_button")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # 다이얼로그 크기 설정
        self.resize(600, 500)

        # 이미지 로드 (모든 UI 요소가 생성된 후)
        self.load_image()

    def load_image(self):
        """이미지 로드 및 표시"""
        try:
            if not Path(self.image_path).exists():
                self.image_label.setText("❌ 이미지 파일을 찾을 수 없습니다.")
                self.info_label.setText(f"파일 경로: {self.image_path}")
                return

            pixmap = QPixmap(self.image_path)
            if pixmap.isNull():
                self.image_label.setText("❌ 이미지를 로드할 수 없습니다.")
                self.info_label.setText(f"파일 경로: {self.image_path}")
                return

            # 이미지 크기 조정 (최대 500x400)
            max_width = 500
            max_height = 400

            if pixmap.width() > max_width or pixmap.height() > max_height:
                scaled_pixmap = pixmap.scaled(
                    max_width,
                    max_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            else:
                scaled_pixmap = pixmap

            self.image_label.setPixmap(scaled_pixmap)

            # 정보 표시
            file_size = Path(self.image_path).stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            info_text = (
                f"📋 이름: {self.template_name}\n"
                f"📐 크기: {pixmap.width()} × {pixmap.height()} 픽셀\n"
                f"💾 파일 크기: {file_size_mb:.2f} MB\n"
                f"📁 경로: {self.image_path}"
            )
            self.info_label.setText(info_text)

        except Exception as e:
            self.image_label.setText(f"❌ 이미지 로드 오류: {str(e)}")
            self.info_label.setText(f"파일 경로: {self.image_path}")


class MacroExecutionThread(QThread):
    """매크로 실행 스레드"""

    execution_finished = pyqtSignal(str, object)  # sequence_id, result
    action_started = pyqtSignal(str, object)  # sequence_id, action
    action_finished = pyqtSignal(str, object, bool)  # sequence_id, action, success

    def __init__(self, engine: MacroEngine, sequence_id: str):
        super().__init__()
        self.engine = engine
        self.sequence_id = sequence_id

    def run(self):
        """스레드 실행"""
        try:
            result = self.engine.execute_sequence(self.sequence_id)
            self.execution_finished.emit(self.sequence_id, result)
        except Exception as e:
            logger.error(f"매크로 실행 스레드 오류: {e}")


class MainWindow(QMainWindow):
    """메인 애플리케이션 윈도우"""

    def __init__(self):
        super().__init__()

        # 매크로 엔진 초기화
        self.engine = MacroEngine()

        # 상태 변수
        self.execution_thread: Optional[MacroExecutionThread] = None
        self.is_capturing = False

        # UI 컴포넌트
        self.template_list: Optional[QListWidget] = None
        self.action_table: Optional[QTableWidget] = None
        self.log_text: Optional[QTextEdit] = None
        self.status_label: Optional[QLabel] = None
        self.progress_bar: Optional[QProgressBar] = None

        # 다이얼로그
        self.capture_dialog: Optional[CaptureDialog] = None
        self.sequence_editor: Optional[SequenceEditor] = None
        self.settings_dialog: Optional[SettingsDialog] = None
        self.telegram_dialog: Optional[TelegramSettingsDialog] = None

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
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

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

        # 왼쪽 패널 (시퀀스/템플릿 목록)
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)

        # 오른쪽 패널 (액션 목록/로그)
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)

        # 분할기 비율 설정
        main_splitter.setSizes([400, 800])

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

    def create_left_panel(self) -> QWidget:
        """왼쪽 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 템플릿 목록 그룹
        template_group = QGroupBox("이미지 템플릿")
        template_group_layout = QVBoxLayout(template_group)

        # 템플릿 테이블 설정
        self.template_list = QTableWidget()
        self.template_list.setColumnCount(3)
        self.template_list.setHorizontalHeaderLabels(["썸네일", "이름", "크기"])

        # 테이블 컬럼 크기 설정
        header = self.template_list.horizontalHeader()
        header.resizeSection(0, 64)  # 썸네일 컬럼 (64px)
        header.setStretchLastSection(True)  # 마지막 컬럼 자동 조정
        header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )  # 이름 컬럼 늘어남

        # 테이블 설정
        self.template_list.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.template_list.setAlternatingRowColors(True)
        self.template_list.verticalHeader().setVisible(False)
        self.template_list.setRowHeight(0, 48)  # 기본 행 높이

        # 이벤트 연결
        self.template_list.itemSelectionChanged.connect(self.on_template_selected)
        self.template_list.itemDoubleClicked.connect(self.on_template_double_clicked)

        template_group_layout.addWidget(self.template_list)

        # 템플릿 버튼들
        temp_btn_layout = QHBoxLayout()

        add_temp_btn = QPushButton("캡쳐")
        add_temp_btn.setObjectName("success_button")
        add_temp_btn.clicked.connect(self.start_capture)
        temp_btn_layout.addWidget(add_temp_btn)

        self.del_temp_btn = QPushButton("삭제")
        self.del_temp_btn.setObjectName("danger_button")
        self.del_temp_btn.setEnabled(False)
        self.del_temp_btn.clicked.connect(self.delete_template)
        temp_btn_layout.addWidget(self.del_temp_btn)

        template_group_layout.addLayout(temp_btn_layout)
        layout.addWidget(template_group)

        return panel

    def create_right_panel(self) -> QWidget:
        """오른쪽 패널 생성"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 액션 그룹
        action_group = QGroupBox("매크로 액션")
        action_group_layout = QVBoxLayout(action_group)

        # 액션 테이블
        self.action_table = QTableWidget()
        self.action_table.setColumnCount(4)
        self.action_table.setHorizontalHeaderLabels(["순서", "타입", "설명", "활성화"])
        self.action_table.itemSelectionChanged.connect(self.on_action_selected)

        # 헤더 설정
        header = self.action_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        # 행 높이 설정 (썸네일을 위해)
        self.action_table.verticalHeader().setDefaultSectionSize(40)

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

        action_btn_layout.addSeparator = lambda: action_btn_layout.addItem(
            QHBoxLayout().addWidget(QLabel("|"))
        )

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

        # 진행률 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_bar.addPermanentWidget(self.progress_bar)

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
        # 매크로 엔진 콜백 설정
        self.engine.on_sequence_start = self.on_sequence_start
        self.engine.on_sequence_complete = self.on_sequence_complete
        self.engine.on_action_execute = self.on_action_execute
        self.engine.on_action_complete = self.on_action_complete
        self.engine.on_error = self.on_engine_error

    def load_data(self):
        """데이터 로드"""
        try:
            # 설정 로드
            if not self.engine.load_config():
                self.add_log("설정 파일 로드 실패")

            # UI 업데이트
            self.refresh_template_list()
            self.refresh_action_table()
            self.update_stats()

            self.add_log("애플리케이션 시작됨")

        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            self.add_log(f"데이터 로드 실패: {e}")

    def refresh_template_list(self):
        """템플릿 목록 새로고침"""
        self.template_list.setRowCount(0)

        for row, template in enumerate(self.engine.config.image_templates):
            self.template_list.insertRow(row)

            # 썸네일 컬럼 (0)
            thumbnail_item = QTableWidgetItem()
            thumbnail_item.setData(Qt.ItemDataRole.UserRole, template.id)

            try:
                if template.file_path and Path(template.file_path).exists():
                    pixmap = QPixmap(template.file_path)
                    if not pixmap.isNull():
                        # 48x48 썸네일로 리사이즈
                        scaled_pixmap = pixmap.scaled(
                            48,
                            48,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        thumbnail_item.setIcon(QIcon(scaled_pixmap))
                        thumbnail_item.setText("")  # 텍스트 제거
                    else:
                        thumbnail_item.setText("❌")
                else:
                    thumbnail_item.setText("❌")
            except Exception:
                thumbnail_item.setText("❌")

            # 썸네일 항목은 편집 불가
            thumbnail_item.setFlags(
                thumbnail_item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )
            self.template_list.setItem(row, 0, thumbnail_item)

            # 이름 컬럼 (1)
            name_item = QTableWidgetItem(template.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.template_list.setItem(row, 1, name_item)

            # 크기 컬럼 (2)
            size_text = "알 수 없음"
            try:
                if template.file_path and Path(template.file_path).exists():
                    pixmap = QPixmap(template.file_path)
                    if not pixmap.isNull():
                        size_text = f"{pixmap.width()}×{pixmap.height()}"
            except Exception:
                pass

            size_item = QTableWidgetItem(size_text)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.template_list.setItem(row, 2, size_item)

            # 행 높이 설정
            self.template_list.setRowHeight(row, 56)

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

        for i, action in enumerate(sequence.actions):
            # 순서
            order_item = QTableWidgetItem(str(i + 1))
            order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.action_table.setItem(i, 0, order_item)

            # 타입
            type_item = QTableWidgetItem(action.action_type.value)
            self.action_table.setItem(i, 1, type_item)

            # 설명
            description = self.get_action_description(action)
            desc_item = QTableWidgetItem(description)

            # 이미지 클릭 액션의 경우 썸네일 표시
            if (
                action.action_type
                in [ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.RIGHT_CLICK]
                and action.image_template_id
            ):
                template = self.engine.config.get_image_template(
                    action.image_template_id
                )
                if (
                    template
                    and template.file_path
                    and Path(template.file_path).exists()
                ):
                    try:
                        pixmap = QPixmap(template.file_path)
                        if not pixmap.isNull():
                            # 32x32 크기로 썸네일 생성
                            scaled_pixmap = pixmap.scaled(
                                32,
                                32,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                            desc_item.setIcon(QIcon(scaled_pixmap))
                    except Exception:
                        pass

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
        if action.action_type == ActionType.FIND_IMAGE:
            template = self.engine.config.get_image_template(action.image_template_id)
            return f"이미지 찾기: {template.name if template else '알 수 없음'}"

        elif action.action_type in [
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
        ]:
            if action.click_position:
                return f"위치 ({action.click_position[0]}, {action.click_position[1]})"
            elif action.image_template_id:
                template = self.engine.config.get_image_template(
                    action.image_template_id
                )
                return f"이미지에서: {template.name if template else '알 수 없음'}"
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

        else:
            return action.action_type.value

    def update_stats(self):
        """통계 정보 업데이트"""
        sequences = len(self.engine.config.macro_sequences)
        templates = len(self.engine.config.image_templates)

        stats_text = f"시퀀스: {sequences} | 템플릿: {templates}"
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

    def on_template_selected(self):
        """템플릿 선택 시 (스레드 안전)"""
        selected_rows = [item.row() for item in self.template_list.selectedItems()]
        has_selection = len(selected_rows) > 0

        # 메인 스레드에서 실행되도록 예약
        QTimer.singleShot(0, lambda: self.del_temp_btn.setEnabled(has_selection))

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
        """화면 캡쳐 시작"""
        if self.is_capturing:
            return

        try:
            self.is_capturing = True

            # 캡쳐 다이얼로그 생성
            if not self.capture_dialog:
                from .capture_dialog import CaptureDialog

                self.capture_dialog = CaptureDialog(self)
                self.capture_dialog.capture_completed.connect(self.on_capture_completed)

            # 윈도우 최소화
            self.showMinimized()

            # 캡쳐 다이얼로그 표시
            self.capture_dialog.start_capture()

        except Exception as e:
            logger.error(f"캡쳐 시작 실패: {e}")
            self.add_log(f"캡쳐 시작 실패: {e}")
            self.is_capturing = False

    def on_capture_completed(self, template_id: str, template_name: str):
        """캡쳐 완료 시"""
        self.is_capturing = False

        # 윈도우 복원
        self.showNormal()
        self.raise_()
        self.activateWindow()

        # 템플릿 목록 새로고침
        self.refresh_template_list()

        self.add_log(f"이미지 템플릿 추가됨: {template_name}")

    def on_action_selected(self):
        """액션 선택 시 (스레드 안전)"""
        selected_rows = set(item.row() for item in self.action_table.selectedItems())
        has_selection = len(selected_rows) > 0

        # 메인 스레드에서 실행되도록 예약
        QTimer.singleShot(0, lambda: self._update_action_buttons(has_selection))

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

                self.add_log(f"액션 추가됨: {action.action_type.value}")

        except Exception as e:
            logger.error(f"액션 추가 저장 실패: {e}")
            QMessageBox.critical(self, "오류", f"액션을 저장할 수 없습니다: {e}")

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

    def delete_template(self):
        """템플릿 삭제"""
        selected_rows = [item.row() for item in self.template_list.selectedItems()]
        if not selected_rows:
            return

        # 첫 번째 컬럼(썸네일)에서 template_id 가져오기
        row = selected_rows[0]
        thumbnail_item = self.template_list.item(row, 0)
        if not thumbnail_item:
            return

        template_id = thumbnail_item.data(Qt.ItemDataRole.UserRole)
        template = self.engine.config.get_image_template(template_id)

        if not template:
            return

        reply = QMessageBox.question(
            self,
            "템플릿 삭제",
            f"이미지 템플릿 '{template.name}'을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.engine.config.remove_image_template(template_id):
                self.engine.save_config()
                self.refresh_template_list()
                self.update_stats()
                self.add_log(f"템플릿 삭제됨: {template.name}")

    def on_template_double_clicked(self, item: QTableWidgetItem):
        """템플릿 더블클릭 시 이미지 미리보기"""
        if not item:
            return

        # 클릭된 행의 썸네일 항목에서 template_id 가져오기
        row = item.row()
        thumbnail_item = self.template_list.item(row, 0)
        if not thumbnail_item:
            return

        template_id = thumbnail_item.data(Qt.ItemDataRole.UserRole)
        template = self.engine.config.get_image_template(template_id)

        if not template:
            return

        try:
            # 이미지 미리보기 다이얼로그 열기
            preview_dialog = ImagePreviewDialog(template.file_path, template.name, self)
            preview_dialog.exec()

        except Exception as e:
            logger.error(f"이미지 미리보기 오류: {e}")
            QMessageBox.critical(
                self, "오류", f"이미지 미리보기를 열 수 없습니다:\n{str(e)}"
            )

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

            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, len(sequence.actions))
            self.progress_bar.setValue(0)

            self.add_log(f"매크로 시퀀스 실행 시작: {sequence.name}")

            # 매크로 실행 전 창 숨기기
            self.hide()

            # 화면이 업데이트되기를 잠시 기다림
            QApplication.processEvents()
            QTimer.singleShot(500, lambda: self._start_macro_execution(sequence))

        except Exception as e:
            logger.error(f"시퀀스 실행 실패: {e}")
            self.show()  # 오류 발생 시 창 다시 표시
            QMessageBox.critical(self, "오류", f"시퀀스를 실행할 수 없습니다: {e}")
            self.reset_execution_ui()
        finally:    
            self.run_btn.setEnabled(True)
            self.run_action.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.stop_action.setEnabled(False)
            self.progress_bar.setVisible(False)

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
        self.run_btn.setEnabled(True)
        self.run_action.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_action.setEnabled(False)
        self.progress_bar.setVisible(False)

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
            self.refresh_sequence_list()
            self.refresh_template_list()
            self.refresh_action_table(None)
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
                    self.refresh_sequence_list()
                    self.refresh_template_list()
                    self.refresh_action_table(None)
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
        """시퀀스 완료 시 (스레드 안전)"""
        self.show()
        self.raise_()
        self.activateWindow()
        # FIXME: 여기에서 프로그램 멈추는 오류 있음
        # 메인 스레드에서 실행되도록 예약
        QTimer.singleShot(
            0, lambda: self._on_sequence_complete_impl(sequence_id, result)
        )

    def _on_sequence_complete_impl(
        self, sequence_id: str, result: MacroExecutionResult
    ):
        # 매크로 완료 후 창 다시 표시
        if self.isHidden():
            self.show()
            self.raise_()
            self.activateWindow()
        logger.debug(f"시퀀스 완료 콜백 호출 22: {sequence_id}")
        """시퀀스 완료 시 실제 구현 (메인 스레드에서 실행)"""
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

    def on_action_execute(self, sequence_id: str, action):
        """액션 실행 시 (스레드 안전)"""
        # 메인 스레드에서 실행되도록 예약
        QTimer.singleShot(0, lambda: self._on_action_execute_impl(sequence_id, action))

    def _on_action_execute_impl(self, sequence_id: str, action):
        """액션 실행 시 실제 구현 (메인 스레드에서 실행)"""
        self.add_log(f"액션 실행: {action.action_type.value}")

        # 진행률 업데이트
        sequence = self.engine.config.get_macro_sequence(sequence_id)
        if sequence:
            current_index = sequence.actions.index(action)
            self.progress_bar.setValue(current_index)

    def on_action_complete(self, sequence_id: str, action, success: bool):
        """액션 완료 시 (스레드 안전)"""
        # 메인 스레드에서 실행되도록 예약
        QTimer.singleShot(
            0, lambda: self._on_action_complete_impl(sequence_id, action, success)
        )

    def _on_action_complete_impl(self, sequence_id: str, action, success: bool):
        """액션 완료 시 실제 구현 (메인 스레드에서 실행)"""
        status = "성공" if success else "실패"
        self.add_log(f"액션 완료: {action.action_type.value} - {status}")

        # 진행률 업데이트
        sequence = self.engine.config.get_macro_sequence(sequence_id)
        if sequence:
            current_index = sequence.actions.index(action)
            self.progress_bar.setValue(current_index + 1)

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
