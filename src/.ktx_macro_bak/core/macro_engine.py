"""
매크로 실행 엔진
"""

import asyncio
import time
import logging
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
import uuid
from datetime import datetime
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from ..models.macro_models import (
    MacroConfig,
    MacroSequence,
    MacroAction,
    ImageTemplate,
    ActionType,
    CaptureRegion,
    ImageSearchFailureAction,
    ConditionType,
)
from .image_matcher import ImageMatcher, MatchResult
from .screen_capture import ScreenCapture
from .input_controller import InputController
from .telegram_bot import SyncTelegramBot

logger = logging.getLogger(__name__)


class MacroExecutionResult:
    """매크로 실행 결과"""

    def __init__(self):
        self.success = False
        self.execution_time = 0.0
        self.steps_executed = 0
        self.total_steps = 0
        self.error_message = ""
        self.failed_action_id = ""
        self.details = []

    def add_step_result(self, action_id: str, success: bool, message: str = ""):
        """단계 결과 추가"""
        self.details.append(
            {
                "action_id": action_id,
                "success": success,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )

        if success:
            self.steps_executed += 1
        else:
            self.failed_action_id = action_id
            self.error_message = message


class MacroEngine(QObject):
    """매크로 실행 엔진"""

    # 시그널 정의
    sequence_started = pyqtSignal(str)  # sequence_id
    sequence_completed = pyqtSignal(str, object)  # sequence_id, MacroExecutionResult
    action_executed = pyqtSignal(str, object)  # sequence_id, MacroAction
    engine_error = pyqtSignal(str, Exception)  # sequence_id, error

    def __init__(self, config_path: str = "config/macro_config.json"):
        super().__init__()
        self.config_path = config_path
        self.config: MacroConfig = MacroConfig()

        # 코어 모듈들
        self.image_matcher = ImageMatcher()
        self.screen_capture = ScreenCapture()
        self.input_controller = InputController()
        self.telegram_bot = SyncTelegramBot()

        # 스케일 팩터 동기화 (screen_capture와 input_controller 간)
        self._sync_scale_factors()

        # 실행 상태
        self.is_running = False
        self.current_sequence: Optional[MacroSequence] = None
        self.execution_thread: Optional[threading.Thread] = None
        self.stop_requested = False
        self.restart_requested = False
        self.current_action_index = 0

        # 콜백 함수들
        self.on_sequence_start: Optional[Callable[[str], None]] = None
        self.on_sequence_complete: Optional[
            Callable[[str, MacroExecutionResult], None]
        ] = None
        self.on_action_execute: Optional[Callable[[str, MacroAction], None]] = None
        self.on_error: Optional[Callable[[str, Exception], None]] = None

        # 실행 통계
        self.execution_stats = {
            "total_sequences_run": 0,
            "successful_sequences": 0,
            "failed_sequences": 0,
            "total_actions_executed": 0,
            "last_execution_time": None,
        }

        # 설정 로드
        self.load_config()

    def _sync_scale_factors(self):
        """ScreenCapture와 InputController 간 스케일 팩터 동기화"""
        try:
            screen_scale = self.screen_capture.get_scale_factor()
            input_scale = self.input_controller.scale_factor

            # 두 스케일 팩터가 다르면 경고하고 더 안전한 값을 사용
            if abs(screen_scale - input_scale) > 0.1:
                logger.warning(
                    f"스케일 팩터 불일치: ScreenCapture={screen_scale}, InputController={input_scale}"
                )
                # 더 작은 값을 사용 (안전한 쪽으로)
                safe_scale = min(screen_scale, input_scale)
                self.input_controller.scale_factor = safe_scale
                logger.info(f"스케일 팩터를 {safe_scale}로 통일했습니다")
            else:
                logger.info(f"스케일 팩터 동기화 완료: {screen_scale}")

        except Exception as e:
            logger.error(f"스케일 팩터 동기화 실패: {e}")

    def load_config(self) -> bool:
        """설정 파일 로드"""
        try:
            if Path(self.config_path).exists():
                self.config = MacroConfig.load_from_file(self.config_path)
                logger.info(f"설정 파일 로드됨: {self.config_path}")
            else:
                logger.info("설정 파일이 없어서 기본 설정으로 시작합니다")
                self.save_config()

            # 텔레그램 봇 설정 적용
            self.telegram_bot.set_config(self.config.telegram_config)

            return True

        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            return False

    def save_config(self) -> bool:
        """설정 파일 저장"""
        try:
            self.config.save_to_file(self.config_path)
            logger.debug("설정 파일 저장됨")
            return True
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
            return False

    def add_image_template(
        self,
        name: str,
        image_path: str,
        capture_region: CaptureRegion,
        threshold: float = 0.8,
    ) -> str:
        """이미지 템플릿 추가"""
        template_id = str(uuid.uuid4())

        template = ImageTemplate(
            id=template_id,
            name=name,
            file_path=image_path,
            capture_region=capture_region,
            threshold=threshold,
        )

        self.config.add_image_template(template)
        self.save_config()

        logger.info(f"이미지 템플릿 추가됨: {name} ({template_id})")
        return template_id

    def create_macro_sequence(self, name: str, description: str = "") -> str:
        """매크로 시퀀스 생성"""
        sequence_id = str(uuid.uuid4())

        sequence = MacroSequence(id=sequence_id, name=name, description=description)

        self.config.add_macro_sequence(sequence)
        self.save_config()

        logger.info(f"매크로 시퀀스 생성됨: {name} ({sequence_id})")
        return sequence_id

    def execute_sequence(self, sequence_id: str) -> MacroExecutionResult:
        """매크로 시퀀스 실행 (동기)"""
        if self.is_running:
            logger.warning("다른 매크로가 실행 중입니다")
            result = MacroExecutionResult()
            result.error_message = "다른 매크로가 실행 중입니다"
            return result

        sequence = self.config.get_macro_sequence(sequence_id)
        if not sequence:
            logger.error(f"시퀀스를 찾을 수 없습니다: {sequence_id}")
            result = MacroExecutionResult()
            result.error_message = "시퀀스를 찾을 수 없습니다"
            return result

        if not sequence.enabled:
            logger.warning(f"비활성화된 시퀀스입니다: {sequence.name}")
            result = MacroExecutionResult()
            result.error_message = "비활성화된 시퀀스입니다"
            return result

        return self._execute_sequence_sync(sequence)

    def execute_sequence_async(self, sequence_id: str) -> None:
        """매크로 시퀀스 비동기 실행"""
        if self.is_running:
            logger.warning("다른 매크로가 실행 중입니다")
            return

        sequence = self.config.get_macro_sequence(sequence_id)
        logger.debug(f"시퀀스 시작: {sequence_id} {sequence = }")
        if not sequence:
            logger.error(f"시퀀스를 찾을 수 없습니다: {sequence_id}")
            return

        def run_sequence():
            result = self._execute_sequence_sync(sequence)
            # 시그널 발생 (스레드에서 안전함)
            logger.debug(f"시퀀스 완료 시그널 발생: {sequence_id}")
            self.sequence_completed.emit(sequence_id, result)

            # 기존 콜백도 호출 (하위 호환성)
            if self.on_sequence_complete:
                logger.debug(f"기존 콜백도 호출: {sequence_id}")
                self.on_sequence_complete(sequence_id, result)

        self.execution_thread = threading.Thread(target=run_sequence)
        self.execution_thread.daemon = True
        self.execution_thread.start()

    def _execute_sequence_sync(self, sequence: MacroSequence) -> MacroExecutionResult:
        """시퀀스 동기 실행 (내부)"""
        result = MacroExecutionResult()
        start_time = time.time()

        try:
            self.is_running = True
            self.current_sequence = sequence
            self.stop_requested = False
            self.restart_requested = False

            result.total_steps = len(sequence.actions)

            # 시퀀스 시작 시그널 발생
            self.sequence_started.emit(sequence.id)

            # 기존 콜백도 호출 (하위 호환성)
            if self.on_sequence_start:
                self.on_sequence_start(sequence.id)

            logger.info(f"매크로 시퀀스 실행 시작: {sequence.name}")

            # 루프 실행
            for loop_index in range(sequence.loop_count):
                if self.stop_requested:
                    break

                logger.debug(f"루프 {loop_index + 1}/{sequence.loop_count} 시작")

                # 액션들 실행
                for action in sequence.actions:
                    if self.stop_requested:
                        break

                    if not action.enabled:
                        logger.debug(f"비활성화된 액션 건너뜀: {action.id}")
                        continue

                    # 액션 실행 시그널 발생
                    self.action_executed.emit(sequence.id, action)

                    # 기존 콜백도 호출 (하위 호환성)
                    if self.on_action_execute:
                        self.on_action_execute(sequence.id, action)

                    action_success = self._execute_action(action)

                    if action_success:
                        result.add_step_result(action.id, True, "성공")
                    else:
                        error_msg = f"액션 실행 실패: {action.action_type}"
                        result.add_step_result(action.id, False, error_msg)

                    # 재시작 요청 확인
                    if self.restart_requested:
                        logger.info("매크로 재시작 요청으로 처음부터 다시 실행")
                        self.restart_requested = False
                        # 재시작을 위해 현재 루프를 중단하고 처음부터 시작
                        break

                    # 액션 간 지연
                    if self.config.action_delay > 0:
                        time.sleep(self.config.action_delay)

                # 재시작 요청이 있으면 루프도 처음부터 시작
                if self.restart_requested:
                    self.restart_requested = False
                    loop_index = -1  # 다음 반복에서 0이 되도록
                    continue

                # 루프 간 지연
                if loop_index < sequence.loop_count - 1 and sequence.loop_delay > 0:
                    time.sleep(sequence.loop_delay)

            # 실행 결과 판정
            result.success = (
                result.steps_executed > 0
                and not self.stop_requested
                and result.steps_executed >= result.total_steps * 0.8  # 80% 이상 성공
            )

            # 통계 업데이트
            self.execution_stats["total_sequences_run"] += 1
            if result.success:
                self.execution_stats["successful_sequences"] += 1
            else:
                self.execution_stats["failed_sequences"] += 1
            self.execution_stats["total_actions_executed"] += result.steps_executed
            self.execution_stats["last_execution_time"] = datetime.now().isoformat()

            logger.info(
                f"매크로 시퀀스 실행 완료: {sequence.name}, "
                f"성공: {result.success}, 실행시간: {result.execution_time:.2f}초"
            )

        except Exception as e:
            logger.error(f"매크로 실행 중 오류: {e}")
            result.error_message = str(e)
            result.success = False

            # 에러 시그널 발생
            self.engine_error.emit(sequence.id, e)

            # 기존 콜백도 호출 (하위 호환성)
            if self.on_error:
                self.on_error(sequence.id, e)

            # 오류 알림
            if self.telegram_bot.is_configured():
                self.telegram_bot.send_error_report(
                    "매크로 실행 오류", str(e), f"시퀀스: {sequence.name}"
                )

        finally:
            result.execution_time = time.time() - start_time
            self.is_running = False
            self.current_sequence = None
            self.stop_requested = False
            self.restart_requested = False

        return result

    def _execute_action(self, action: MacroAction) -> bool:
        """개별 액션 실행"""
        try:
            logger.debug(f"액션 실행: {action.action_type}")

            if action.action_type == ActionType.IMAGE_CLICK:
                return self._execute_click_action(action)

            elif action.action_type == ActionType.DOUBLE_CLICK:
                return self._execute_double_click_action(action)

            elif action.action_type == ActionType.RIGHT_CLICK:
                return self._execute_right_click_action(action)

            elif action.action_type == ActionType.DRAG:
                return self._execute_drag_action(action)

            elif action.action_type == ActionType.TYPE_TEXT:
                return self._execute_type_text_action(action)

            elif action.action_type == ActionType.KEY_PRESS:
                return self._execute_key_press_action(action)

            elif action.action_type == ActionType.SCROLL:
                return self._execute_scroll_action(action)

            elif action.action_type == ActionType.WAIT:
                return self._execute_wait_action(action)

            elif action.action_type == ActionType.SEND_TELEGRAM:
                return self._execute_telegram_action(action)

            elif action.action_type == ActionType.IF:
                return self._execute_if_action(action)

            elif action.action_type == ActionType.ELSE:
                return self._execute_else_action(action)

            elif action.action_type == ActionType.LOOP:
                return self._execute_loop_action(action)

            else:
                logger.error(f"지원하지 않는 액션 타입: {action.action_type}")
                return False

        except Exception as e:
            logger.error(f"액션 실행 중 오류: {action.action_type}, {e}")
            return False

    def _execute_click_action(self, action: MacroAction) -> bool:
        """클릭 액션 실행"""
        if action.image_template_id and action.click_position:
            # 이미지를 찾아서 액션에서 지정한 위치 클릭
            return self._find_and_click_image(action)
        else:
            logger.error("이미지 템플릿과 클릭 위치가 모두 필요합니다")
            return False

    def _execute_double_click_action(self, action: MacroAction) -> bool:
        """더블클릭 액션 실행"""
        if action.image_template_id and action.click_position:
            # 이미지를 찾아서 액션에서 지정한 위치 더블클릭
            return self._find_and_click_image(action, double_click=True)
        else:
            logger.error("이미지 템플릿과 클릭 위치가 모두 필요합니다")
            return False

    def _execute_right_click_action(self, action: MacroAction) -> bool:
        """우클릭 액션 실행"""
        if action.image_template_id and action.click_position:
            # 이미지를 찾아서 액션에서 지정한 위치 우클릭
            return self._find_and_click_image(action, right_click=True)
        else:
            logger.error("이미지 템플릿과 클릭 위치가 모두 필요합니다")
            return False

    def _find_and_click_image(
        self, action: MacroAction, double_click: bool = False, right_click: bool = False
    ) -> bool:
        """이미지를 찾아서 클릭"""
        if not action.image_template_id:
            return False

        template = self.config.get_image_template(action.image_template_id)
        if not template:
            logger.error(
                f"이미지 템플릿을 찾을 수 없습니다: {action.image_template_id}"
            )
            return False

        # 이미지 파일 존재 확인
        from pathlib import Path

        if not Path(template.file_path).exists():
            logger.error(f"이미지 파일이 존재하지 않습니다: {template.file_path}")
            return False

        logger.debug(f"이미지 매칭 시도: {template.name} ({template.file_path})")

        screenshot = self.screen_capture.capture_full_screen()
        if screenshot is None:
            logger.error("스크린샷 캡쳐 실패")
            return False

        # 매칭 임계값 설정 (기본값 또는 템플릿 설정)
        threshold = (
            getattr(action, "match_threshold", None) or template.threshold or 0.8
        )
        logger.debug(f"매칭 임계값: {threshold}")

        match_result = self.image_matcher.find_image_in_screenshot(
            screenshot,
            template.file_path,
            threshold,
        )

        if not match_result.found:
            logger.warning(
                f"이미지 매칭 실패: {template.name}, 임계값: {threshold}, 최대 신뢰도: {match_result.confidence:.3f}"
            )

            # 이미지 탐색 실패 시 처리 옵션에 따른 동작
            return self._handle_image_search_failure(action)

        logger.info(
            f"이미지 매칭 성공: {template.name}, 신뢰도: {match_result.confidence:.3f}, 매칭 위치: {match_result.center_position}"
        )

        # 액션에서 설정한 클릭 위치 사용 (필수)
        if not action.click_position:
            logger.error(f"액션에 클릭 위치가 설정되지 않았습니다: {action.id}")
            return False

        # 매칭된 이미지의 상단 좌측 좌표에서 액션 클릭 위치만큼 오프셋 적용
        match_top_left = match_result.top_left
        action_click_x, action_click_y = action.click_position

        # 실제 클릭할 화면 좌표 계산
        actual_click_x = match_top_left[0] + action_click_x
        actual_click_y = match_top_left[1] + action_click_y

        logger.info(
            f"클릭 위치 계산: 매칭 시작점({match_top_left}) + 액션 오프셋({action.click_position}) = 실제 클릭({actual_click_x}, {actual_click_y})"
        )

        if double_click:
            return self.input_controller.double_click(actual_click_x, actual_click_y)
        elif right_click:
            return self.input_controller.right_click(actual_click_x, actual_click_y)
        else:
            return self.input_controller.click(actual_click_x, actual_click_y)

    def _execute_drag_action(self, action: MacroAction) -> bool:
        """드래그 액션 실행"""
        if not (action.click_position and action.drag_to_position):
            logger.error("드래그 시작점과 끝점이 지정되지 않았습니다")
            return False

        from_x, from_y = action.click_position
        to_x, to_y = action.drag_to_position

        return self.input_controller.drag(from_x, from_y, to_x, to_y)

    def _execute_type_text_action(self, action: MacroAction) -> bool:
        """텍스트 입력 액션 실행"""
        if not action.text_input:
            logger.warning("입력할 텍스트가 없습니다")
            return True

        return self.input_controller.type_text(action.text_input)

    def _execute_key_press_action(self, action: MacroAction) -> bool:
        """키 입력 액션 실행"""
        if action.key_combination:
            return self.input_controller.key_combination(action.key_combination)
        else:
            logger.error("입력할 키가 지정되지 않았습니다")
            return False

    def _execute_scroll_action(self, action: MacroAction) -> bool:
        """스크롤 액션 실행"""
        x, y = action.click_position if action.click_position else (None, None)
        direction = action.scroll_direction or "up"
        amount = action.scroll_amount or 3

        return self.input_controller.scroll(x, y, direction, amount)

    def _execute_wait_action(self, action: MacroAction) -> bool:
        """대기 액션 실행"""
        seconds = action.wait_seconds or 1.0
        return self.input_controller.wait(seconds)

    def _execute_telegram_action(self, action: MacroAction) -> bool:
        """텔레그램 메시지 전송 액션 실행"""
        if not action.telegram_message:
            logger.warning("전송할 텔레그램 메시지가 없습니다")
            return True

        if not self.telegram_bot.is_configured():
            logger.warning("텔레그램이 설정되지 않았습니다")
            return False

        return self.telegram_bot.send_message(action.telegram_message)

    def stop_execution(self) -> None:
        """매크로 실행 중단"""
        if self.is_running:
            logger.info("매크로 실행 중단 요청됨")
            self.stop_requested = True

            # 스레드 대기 (최대 5초)
            if self.execution_thread and self.execution_thread.is_alive():
                self.execution_thread.join(timeout=5.0)

    def get_execution_status(self) -> Dict[str, Any]:
        """실행 상태 정보 반환"""
        return {
            "is_running": self.is_running,
            "current_sequence": (
                self.current_sequence.name if self.current_sequence else None
            ),
            "stop_requested": self.stop_requested,
            "stats": self.execution_stats.copy(),
        }

    def _handle_image_search_failure(self, action: MacroAction) -> bool:
        """이미지 탐색 실패 시 처리"""
        failure_action = getattr(
            action, "on_image_not_found", ImageSearchFailureAction.STOP_EXECUTION
        )

        logger.info(f"이미지 탐색 실패 처리: {failure_action.value}")

        if failure_action == ImageSearchFailureAction.REFRESH_SCREEN:
            # 화면 새로고침 (F5 키 전송)
            logger.info("화면 새로고침 실행 (F5)")
            self.input_controller.key_press(["F5"])
            time.sleep(2)  # 새로고침 대기

            # 새로고침 후 다시 이미지 탐색 시도
            return self._retry_image_search(action)

        elif failure_action == ImageSearchFailureAction.RESTART_SEQUENCE:
            # 매크로 처음부터 재실행
            logger.info("매크로 처음부터 재실행 요청")
            self.restart_requested = True
            return True  # 현재 액션은 성공으로 처리하여 루프 계속

        elif failure_action == ImageSearchFailureAction.SKIP_TO_NEXT:
            # 무시하고 다음 단계
            logger.info("현재 액션 건너뛰고 다음 단계로 진행")
            return True  # 성공으로 처리하여 다음 액션으로

        else:  # STOP_EXECUTION
            # 실행 중단
            logger.info("매크로 실행 중단")
            return False

    def _retry_image_search(self, action: MacroAction) -> bool:
        """이미지 탐색 재시도"""
        if not action.image_template_id:
            return False

        template = self.config.get_image_template(action.image_template_id)
        if not template:
            return False

        logger.debug(f"이미지 탐색 재시도: {template.name}")

        screenshot = self.screen_capture.capture_full_screen()
        if screenshot is None:
            logger.error("스크린샷 캡쳐 실패")
            return False

        threshold = (
            getattr(action, "match_threshold", None) or template.threshold or 0.8
        )
        match_result = self.image_matcher.find_image_in_screenshot(
            screenshot, template.file_path, threshold
        )

        if match_result.found:
            logger.info(
                f"재시도 성공: {template.name}, 신뢰도: {match_result.confidence:.3f}"
            )
            x, y = match_result.center_position

            # 액션 타입에 따른 클릭 실행
            if action.action_type == ActionType.IMAGE_CLICK:
                return self.input_controller.click(x, y)
            elif action.action_type == ActionType.DOUBLE_CLICK:
                return self.input_controller.double_click(x, y)
            elif action.action_type == ActionType.RIGHT_CLICK:
                return self.input_controller.right_click(x, y)
        else:
            logger.warning(f"재시도도 실패: {template.name}")
            return False

    def _execute_if_action(self, action: MacroAction) -> bool:
        """IF 액션 실행 - 조건 체크"""
        try:
            logger.debug(f"IF 조건 체크: {action.condition_type}")

            if not action.condition_type:
                logger.error("IF 액션에 조건 타입이 설정되지 않음")
                return False

            # 조건 체크
            condition_result = self._check_condition(action)

            # 조건 결과를 실행 컨텍스트에 저장 (ELSE에서 사용)
            if not hasattr(self, "_condition_results"):
                self._condition_results = {}
            self._condition_results[action.id] = condition_result

            logger.info(f"IF 조건 결과: {condition_result}")
            return True  # IF 액션 자체는 항상 성공 (조건 체크만 수행)

        except Exception as e:
            logger.error(f"IF 액션 실행 실패: {e}")
            return False

    def _execute_else_action(self, action: MacroAction) -> bool:
        """ELSE 액션 실행 - 이전 IF 조건의 반대 결과 사용"""
        try:
            logger.debug("ELSE 조건 체크")

            # 이전 IF 조건 결과 찾기
            if not hasattr(self, "_condition_results"):
                logger.error("ELSE 액션 실행 시 이전 IF 조건 결과가 없음")
                return False

            # 마지막 IF 조건 결과 사용
            last_if_result = None
            for result in reversed(list(self._condition_results.values())):
                last_if_result = result
                break

            if last_if_result is None:
                logger.error("ELSE 액션 실행 시 참조할 IF 조건 결과가 없음")
                return False

            # ELSE는 IF의 반대 결과
            else_result = not last_if_result
            logger.info(f"ELSE 조건 결과: {else_result}")
            return True  # ELSE 액션 자체는 항상 성공

        except Exception as e:
            logger.error(f"ELSE 액션 실행 실패: {e}")
            return False

    def _execute_loop_action(self, action: MacroAction) -> bool:
        """LOOP 액션 실행"""
        try:
            loop_count = action.loop_count or 0  # 0이면 무한 루프
            loop_delay = action.wait_seconds or 1.0

            logger.info(
                f"LOOP 시작: {loop_count}회 (무한: {loop_count == 0}), 간격: {loop_delay}초"
            )

            # LOOP 액션은 구조적 요소이므로 실제 반복은 상위 실행 로직에서 처리
            # 여기서는 LOOP 설정 정보만 로깅
            return True

        except Exception as e:
            logger.error(f"LOOP 액션 실행 실패: {e}")
            return False

    def _check_condition(self, action: MacroAction) -> bool:
        """조건 체크"""
        try:
            if action.condition_type == ConditionType.ALWAYS:
                return True

            elif action.condition_type in [
                ConditionType.IMAGE_FOUND,
                ConditionType.IMAGE_NOT_FOUND,
            ]:
                if not action.image_template_id:
                    logger.error("이미지 기반 조건이지만 이미지 템플릿이 설정되지 않음")
                    return False

                # 이미지 템플릿 가져오기 (IF 액션도 동일한 image_template_id 사용)
                template = self.config.get_image_template(action.image_template_id)
                if not template:
                    logger.error(
                        f"이미지 템플릿을 찾을 수 없음: {action.image_template_id}"
                    )
                    return False

                # 화면 캡쳐
                screenshot = self.screen_capture.capture_screenshot()
                if screenshot is None:
                    logger.error("조건 체크용 화면 캡쳐 실패")
                    return False

                # 이미지 매칭
                match_result = self.image_matcher.find_image_in_screenshot(
                    screenshot, template.file_path, action.match_threshold
                )

                image_found = match_result.found
                logger.debug(
                    f"조건 이미지 매칭 결과: {image_found}, 신뢰도: {match_result.confidence:.3f}"
                )

                if action.condition_type == ConditionType.IMAGE_FOUND:
                    return image_found
                else:  # IMAGE_NOT_FOUND
                    return not image_found

            else:
                logger.error(f"알 수 없는 조건 타입: {action.condition_type}")
                return False

        except Exception as e:
            logger.error(f"조건 체크 실패: {e}")
            return False

    def cleanup(self) -> None:
        """리소스 정리"""
        self.stop_execution()
        self.image_matcher.clear_cache()
        self.telegram_bot.close()
        logger.info("매크로 엔진 정리 완료")
