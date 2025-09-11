"""
텔레그램 설정 다이얼로그
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QTextEdit,
    QMessageBox,
    QProgressBar,
)
from PyQt6.QtCore import pyqtSignal, QThread

from macro.core.macro_engine import MacroEngine
from macro.core.telegram_bot import SyncTelegramBot
from macro.models.macro_models import TelegramConfig


class TelegramTestThread(QThread):
    """텔레그램 연결 테스트 스레드"""

    test_completed = pyqtSignal(bool, str)

    def __init__(self, config: TelegramConfig):
        super().__init__()
        self.config = config

    def run(self):
        """테스트 실행"""
        try:
            bot = SyncTelegramBot(self.config)
            success = bot.test_connection()

            if success:
                self.test_completed.emit(True, "연결 테스트 성공!")
            else:
                self.test_completed.emit(False, "연결 테스트 실패")

        except Exception as e:
            self.test_completed.emit(False, f"테스트 중 오류: {e}")


class TelegramSettingsDialog(QDialog):
    """텔레그램 설정 다이얼로그"""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None, engine: MacroEngine = None):
        super().__init__(parent)

        self.engine = engine
        self.test_thread = None

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("텔레그램 설정")
        self.setModal(True)
        self.resize(500, 600)

        layout = QVBoxLayout(self)

        check_layout = QHBoxLayout()
        # 활성화 체크박스
        self.enabled_checkbox = QCheckBox("텔레그램 알림 사용")
        self.enabled_checkbox.toggled.connect(self.on_enabled_toggled)
        check_layout.addWidget(self.enabled_checkbox)

        # 매크로 완료 시 메시지 전송 체크박스
        self.use_finished_message_checkbox = QCheckBox("매크로 완료 시 메시지 전송")
        check_layout.addWidget(self.use_finished_message_checkbox)
        layout.addLayout(check_layout)

        # 봇 설정
        bot_group = QGroupBox("봇 설정")
        bot_layout = QVBoxLayout(bot_group)

        # 봇 토큰
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("봇 토큰:"))

        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText(
            "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg"
        )
        token_layout.addWidget(self.token_edit)

        bot_layout.addLayout(token_layout)

        # 채팅 ID
        chat_layout = QHBoxLayout()
        chat_layout.addWidget(QLabel("채팅 ID:"))

        self.chat_id_edit = QLineEdit()
        self.chat_id_edit.setPlaceholderText("@username 또는 숫자 ID")
        chat_layout.addWidget(self.chat_id_edit)

        bot_layout.addLayout(chat_layout)

        layout.addWidget(bot_group)

        # 테스트
        test_group = QGroupBox("연결 테스트")
        test_layout = QVBoxLayout(test_group)

        test_btn_layout = QHBoxLayout()

        self.test_button = QPushButton("연결 테스트")
        self.test_button.clicked.connect(self.test_connection)
        test_btn_layout.addWidget(self.test_button)

        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        test_btn_layout.addWidget(self.test_progress)

        test_layout.addLayout(test_btn_layout)

        # 테스트 결과
        self.test_result = QTextEdit()
        self.test_result.setMaximumHeight(100)
        self.test_result.setReadOnly(True)
        test_layout.addWidget(self.test_result)

        layout.addWidget(test_group)

        # 도움말
        help_group = QGroupBox("도움말")
        help_layout = QVBoxLayout(help_group)

        help_text = QLabel(
            "1. @BotFather에게 /newbot 명령어로 봇을 생성하세요\n"
            "2. 생성된 봇 토큰을 위에 입력하세요\n"
            "3. 봇과 대화를 시작하고 /start 명령어를 보내세요\n"
            "4. 채팅 ID를 확인하여 위에 입력하세요\n"
            "5. '연결 테스트' 버튼으로 설정을 확인하세요"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("QLabel { color: #666; padding: 10px; }")
        help_layout.addWidget(help_text)

        layout.addWidget(help_group)

        # 버튼
        button_layout = QHBoxLayout()

        self.ok_button = QPushButton("확인")
        self.ok_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.ok_button)

        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def on_enabled_toggled(self, enabled: bool):
        """활성화 토글 시"""
        # 관련 위젯들 활성화/비활성화
        self.token_edit.setEnabled(enabled)
        self.chat_id_edit.setEnabled(enabled)
        self.test_button.setEnabled(enabled)

    def load_settings(self):
        """설정 로드"""
        if not self.engine:
            return

        config = self.engine.config.telegram_config

        self.enabled_checkbox.setChecked(config.enabled)
        self.token_edit.setText(config.bot_token)
        self.chat_id_edit.setText(config.chat_id)

        # 초기 상태 설정
        self.on_enabled_toggled(config.enabled)

    def test_connection(self):
        """연결 테스트"""
        token = self.token_edit.text().strip()
        chat_id = self.chat_id_edit.text().strip()

        if not token or not chat_id:
            QMessageBox.warning(self, "경고", "봇 토큰과 채팅 ID를 모두 입력하세요.")
            return

        # 테스트 설정 생성
        test_config = TelegramConfig(bot_token=token, chat_id=chat_id, enabled=True)

        # UI 업데이트
        self.test_button.setEnabled(False)
        self.test_progress.setVisible(True)
        self.test_progress.setRange(0, 0)  # 무한 진행률
        self.test_result.clear()
        self.test_result.append("연결 테스트 중...")

        # 테스트 스레드 시작
        self.test_thread = TelegramTestThread(test_config)
        self.test_thread.test_completed.connect(self.on_test_completed)
        self.test_thread.start()

    def on_test_completed(self, success: bool, message: str):
        """테스트 완료 시"""
        # UI 복원
        self.test_button.setEnabled(True)
        self.test_progress.setVisible(False)

        # 결과 표시
        self.test_result.clear()

        if success:
            self.test_result.setStyleSheet("QTextEdit { color: green; }")
            self.test_result.append(f"✅ {message}")
        else:
            self.test_result.setStyleSheet("QTextEdit { color: red; }")
            self.test_result.append(f"❌ {message}")

        # 스레드 정리
        if self.test_thread:
            self.test_thread.quit()
            self.test_thread.wait()
            self.test_thread = None

    def save_settings(self):
        """설정 저장"""
        if not self.engine:
            return

        try:
            config = self.engine.config.telegram_config

            config.enabled = self.enabled_checkbox.isChecked()
            config.use_finished_message = self.use_finished_message_checkbox.isChecked()
            config.bot_token = self.token_edit.text().strip()
            config.chat_id = self.chat_id_edit.text().strip()

            # 유효성 검사
            if config.enabled:
                if not config.bot_token or not config.chat_id:
                    QMessageBox.warning(
                        self,
                        "경고",
                        "텔레그램을 활성화하려면 봇 토큰과 채팅 ID를 모두 입력해야 합니다.",
                    )
                    return

            # 엔진에 새 설정 적용
            self.engine.telegram_bot.set_config(config)

            # 설정 파일 저장
            self.engine.save_config()

            self.settings_changed.emit()
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 저장 실패: {e}")

    def closeEvent(self, event):
        """다이얼로그 닫기 시"""
        # 실행 중인 테스트 스레드 정리
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.quit()
            self.test_thread.wait()

        event.accept()
