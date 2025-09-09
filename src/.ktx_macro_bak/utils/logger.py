"""
로깅 시스템
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from datetime import datetime
import sys


class ColoredFormatter(logging.Formatter):
    """컬러 포매터"""

    # ANSI 색상 코드
    COLORS = {
        "DEBUG": "\033[36m",  # 청록색
        "INFO": "\033[32m",  # 녹색
        "WARNING": "\033[33m",  # 노란색
        "ERROR": "\033[31m",  # 빨간색
        "CRITICAL": "\033[35m",  # 자주색
        "RESET": "\033[0m",  # 리셋
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset_color = self.COLORS["RESET"]

        # 레벨명에 색상 적용
        record.levelname = f"{log_color}{record.levelname}{reset_color}"

        return super().format(record)


def setup_logger(
    name: str = "ktx_macro",
    level: int = logging.DEBUG,
    log_dir: str = "logs",
    enable_console: bool = True,
    enable_file: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """로거 설정"""

    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 기존 핸들러 제거 (중복 방지)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 포매터 설정
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # 콘솔 핸들러
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # 컬러 포매터 적용 (터미널이 색상을 지원하는 경우)
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            colored_formatter = ColoredFormatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
            )
            console_handler.setFormatter(colored_formatter)
        else:
            console_handler.setFormatter(simple_formatter)

        logger.addHandler(console_handler)

    # 파일 핸들러
    if enable_file:
        # 로그 디렉토리 생성
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 일반 로그 파일 (로테이션)
        log_file = log_path / f"{name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_file_size, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

        # 오류 전용 로그 파일
        error_file = log_path / f"{name}_error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)

        # 디버그 전용 로그 파일 (디버그 레벨인 경우에만)
        if level <= logging.DEBUG:
            debug_file = log_path / f"{name}_debug.log"
            debug_handler = logging.handlers.RotatingFileHandler(
                debug_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding="utf-8",
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(detailed_formatter)
            logger.addHandler(debug_handler)

    # 처리되지 않은 예외 로깅
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            "처리되지 않은 예외 발생", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception

    logger.info(f"로거 설정 완료: {name} (레벨: {logging.getLevelName(level)})")
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """로거 가져오기"""
    if name is None:
        name = "ktx_macro"
    return logging.getLogger(name)


class LogCapture:
    """로그 캡처 클래스"""

    def __init__(self, logger_name: str = "ktx_macro", level: int = logging.INFO):
        self.logger_name = logger_name
        self.level = level
        self.captured_logs = []
        self.handler = None

    def start_capture(self):
        """로그 캡처 시작"""
        self.captured_logs.clear()

        # 메모리 핸들러 생성
        self.handler = logging.Handler()
        self.handler.setLevel(self.level)

        # 커스텀 emit 메소드로 로그 캡처
        def capture_emit(record):
            self.captured_logs.append(self.handler.format(record))

        self.handler.emit = capture_emit

        # 로거에 핸들러 추가
        logger = logging.getLogger(self.logger_name)
        logger.addHandler(self.handler)

    def stop_capture(self) -> list:
        """로그 캡처 중단 및 결과 반환"""
        if self.handler:
            logger = logging.getLogger(self.logger_name)
            logger.removeHandler(self.handler)
            self.handler = None

        return self.captured_logs.copy()

    def get_logs(self) -> list:
        """캡처된 로그 반환"""
        return self.captured_logs.copy()

    def clear_logs(self):
        """캡처된 로그 삭제"""
        self.captured_logs.clear()


class StructuredLogger:
    """구조화된 로깅을 위한 래퍼 클래스"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_macro_start(self, macro_name: str, sequence_id: str):
        """매크로 시작 로그"""
        self.logger.info(
            f"[MACRO_START] {macro_name}",
            extra={
                "event_type": "macro_start",
                "macro_name": macro_name,
                "sequence_id": sequence_id,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_macro_complete(
        self,
        macro_name: str,
        sequence_id: str,
        success: bool,
        execution_time: float,
        steps_completed: int,
    ):
        """매크로 완료 로그"""
        level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILED"

        self.logger.log(
            level,
            f"[MACRO_{status}] {macro_name} - {execution_time:.2f}s - {steps_completed} steps",
            extra={
                "event_type": "macro_complete",
                "macro_name": macro_name,
                "sequence_id": sequence_id,
                "success": success,
                "execution_time": execution_time,
                "steps_completed": steps_completed,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_action_execute(
        self, action_type: str, action_id: str, details: dict = None
    ):
        """액션 실행 로그"""
        self.logger.debug(
            f"[ACTION_EXECUTE] {action_type}",
            extra={
                "event_type": "action_execute",
                "action_type": action_type,
                "action_id": action_id,
                "details": details or {},
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_action_result(
        self, action_type: str, action_id: str, success: bool, error_message: str = ""
    ):
        """액션 결과 로그"""
        level = logging.DEBUG if success else logging.WARNING
        status = "SUCCESS" if success else "FAILED"

        message = f"[ACTION_{status}] {action_type}"
        if error_message:
            message += f" - {error_message}"

        self.logger.log(
            level,
            message,
            extra={
                "event_type": "action_result",
                "action_type": action_type,
                "action_id": action_id,
                "success": success,
                "error_message": error_message,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_image_match(
        self, template_name: str, found: bool, confidence: float, position: tuple = None
    ):
        """이미지 매칭 로그"""
        level = logging.DEBUG if found else logging.WARNING
        status = "FOUND" if found else "NOT_FOUND"

        message = f"[IMAGE_{status}] {template_name} - confidence: {confidence:.3f}"
        if position:
            message += f" - position: {position}"

        self.logger.log(
            level,
            message,
            extra={
                "event_type": "image_match",
                "template_name": template_name,
                "found": found,
                "confidence": confidence,
                "position": position,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def log_telegram_send(self, success: bool, message_preview: str):
        """텔레그램 전송 로그"""
        level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILED"

        self.logger.log(
            level,
            f"[TELEGRAM_{status}] {message_preview[:50]}...",
            extra={
                "event_type": "telegram_send",
                "success": success,
                "message_preview": message_preview[:100],
                "timestamp": datetime.now().isoformat(),
            },
        )


def create_structured_logger(name: str = "ktx_macro") -> StructuredLogger:
    """구조화된 로거 생성"""
    logger = get_logger(name)
    return StructuredLogger(logger)
