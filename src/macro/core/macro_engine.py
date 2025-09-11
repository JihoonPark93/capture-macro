"""
매크로 실행 엔진
"""

import time
import logging
from typing import Optional, Callable, Dict, Any
from pathlib import Path
import uuid
from datetime import datetime
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from macro.models.macro_models import (
    MacroConfig,
    MacroSequence,
    MacroAction,
    ImageTemplate,
    ActionType,
    ImageSearchFailureAction,
    ConditionType,
)
from macro.core.image_matcher import ImageMatcher
from macro.core.screen_capture import ScreenCapture
from macro.core.input_controller import InputController
from macro.core.telegram_bot import SyncTelegramBot

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
    sequence_started = pyqtSignal()  #
    sequence_completed = pyqtSignal(object)  # MacroExecutionResult
    action_executed = pyqtSignal(object)  # MacroAction
    engine_error = pyqtSignal(Exception)  # error

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
                print(
                    f"스케일 팩터 불일치: ScreenCapture={screen_scale}, InputController={input_scale}"
                )
                # 더 작은 값을 사용 (안전한 쪽으로)
                safe_scale = min(screen_scale, input_scale)
                self.input_controller.scale_factor = safe_scale
                print(f"스케일 팩터를 {safe_scale}로 통일했습니다")
            else:
                print(f"스케일 팩터 동기화 완료: {screen_scale}")

        except Exception as e:
            print(f"스케일 팩터 동기화 실패: {e}")

    def load_config(self) -> bool:
        """설정 파일 로드"""
        try:
            if Path(self.config_path).exists():
                self.config = MacroConfig.load_from_file(self.config_path)
                print(f"설정 파일 로드됨: {self.config_path}")
            else:
                print("설정 파일이 없어서 기본 설정으로 시작합니다")
                self.save_config()

            # 텔레그램 봇 설정 적용
            self.telegram_bot.set_config(self.config.telegram_config)

            return True

        except Exception as e:
            print(f"설정 파일 로드 실패: {e}")
            return False

    def save_config(self) -> bool:
        """설정 파일 저장"""
        try:
            self.config.save_to_file(self.config_path)
            print("설정 파일 저장됨")
            return True
        except Exception as e:
            print(f"설정 파일 저장 실패: {e}")
            return False

    def add_image_template(
        self,
        name: str,
        image_path: str,
        threshold: float = 0.8,
    ) -> str:
        """이미지 템플릿 추가"""
        template_id = str(uuid.uuid4())

        template = ImageTemplate(
            id=template_id,
            name=name,
            file_path=image_path,
            threshold=threshold,
        )

        self.config.add_image_template(template)
        self.save_config()

        print(f"이미지 템플릿 추가됨: {name} ({template_id})")
        return template_id

    def execute_sequence_async(self) -> None:
        """매크로 시퀀스 비동기 실행"""
        if self.is_running:
            print("다른 매크로가 실행 중입니다")
            return

        sequence = self.config.macro_sequence
        print(f"시퀀스 시작")

        def run_sequence():
            result = self._execute_sequence_sync(sequence)
            # 시그널 발생 (스레드에서 안전함)
            print(f"시퀀스 완료 시그널 발생:")

            if (
                self.telegram_bot.is_configured()
                and self.telegram_bot.use_finished_message()
            ):
                self.telegram_bot.send_message(
                    "매크로 실행이 종료되었습니다. 확인해주세요"
                )

            self.sequence_completed.emit(result)

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
            self.sequence_started.emit()

            # 기존 콜백도 호출 (하위 호환성)
            if self.on_sequence_start:
                self.on_sequence_start()

            print(f"매크로 시퀀스 실행 시작: {sequence.name}")

            # 루프 실행
            loop_index = 0
            while loop_index < sequence.loop_count:
                loop_index += 1

                if self.stop_requested:
                    break

                print(f"루프 {loop_index + 1}/{sequence.loop_count} 시작")

                # 액션들 실행
                for action in sequence.actions:
                    if self.stop_requested:
                        break

                    if not action.enabled:
                        print(f"비활성화된 액션 건너뜀: {action.id}")
                        continue

                    # 액션 실행 시그널 발생
                    self.action_executed.emit(action)

                    # 기존 콜백도 호출 (하위 호환성)
                    if self.on_action_execute:
                        self.on_action_execute(action)

                    action_success = self._execute_action(action)

                    if action_success:
                        result.add_step_result(action.id, True, "성공")
                    else:
                        error_msg = f"액션 실행 실패: {action.action_type}"
                        result.add_step_result(action.id, False, error_msg)

                    # 재시작 요청 확인
                    if self.restart_requested:
                        print("매크로 재시작 요청으로 처음부터 다시 실행")
                        break

                # 재시작 요청이 있으면 루프도 처음부터 시작
                if self.restart_requested:
                    self.restart_requested = False
                    loop_index = 0
                    continue

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

            print(
                f"매크로 시퀀스 실행 완료: {sequence.name}, "
                f"성공: {result.success}, 실행시간: {result.execution_time:.2f}초"
            )

        except Exception as e:
            print(f"매크로 실행 중 오류: {e}")
            result.error_message = str(e)
            result.success = False

            # 에러 시그널 발생
            self.engine_error.emit(e)

            # 기존 콜백도 호출 (하위 호환성)
            if self.on_error:
                self.on_error(e)

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
            print(f"액션 실행: {action.action_type}")

            if action.action_type == ActionType.CLICK:
                return self._execute_click_action(action)

            elif action.action_type == ActionType.IMAGE_CLICK:
                return self._execute_image_click_action(action)

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

            else:
                print(f"지원하지 않는 액션 타입: {action.action_type}")
                return False

        except Exception as e:
            print(f"액션 실행 중 오류: {action.action_type}, {e}")
            return False

    def _execute_click_action(self, action: MacroAction) -> bool:
        """클릭 액션 실행"""
        if action.click_position:
            # 이미지를 찾아서 액션에서 지정한 위치 클릭
            return self.input_controller.click(
                action.click_position[0], action.click_position[1]
            )

        else:
            print("클릭 위치가 설정되지 않았습니다")
            return False

    def _execute_image_click_action(
        self, action: MacroAction, double_click: bool = False, right_click: bool = False
    ) -> bool:
        """클릭 액션 실행"""
        if not action.image_template_id or not action.click_position:
            print("이미지 템플릿과 클릭 위치가 모두 필요합니다")
            return False

        template = self.config.get_image_template(action.image_template_id)
        if not template:
            print(f"이미지 템플릿을 찾을 수 없습니다: {action.image_template_id}")
            return False

        # 이미지 파일 존재 확인
        from pathlib import Path

        if not Path(template.file_path).exists():
            print(f"이미지 파일이 존재하지 않습니다: {template.file_path}")
            return False

        print(f"이미지 매칭 시도: {template.name} ({template.file_path})")

        screenshot = self.screen_capture.capture_full_screen()
        if screenshot is None:
            print("스크린샷 캡쳐 실패")
            return False

        # 매칭 임계값 설정 (기본값 또는 템플릿 설정)
        threshold = (
            getattr(action, "match_threshold", None) or template.threshold or 0.8
        )
        print(f"매칭 임계값: {threshold}")

        match_result = self.image_matcher.find_image_in_screenshot(
            screenshot,
            template.file_path,
            action.selected_region,
            threshold,
        )

        if not match_result.found:
            print(
                f"이미지 매칭 실패: {template.name}, 임계값: {threshold}, 최대 신뢰도: {match_result.confidence:.3f}"
            )

            # 이미지 탐색 실패 시 처리 옵션에 따른 동작
            return self._handle_image_search_failure(action)

        print(
            f"이미지 매칭 성공: {template.name}, 신뢰도: {match_result.confidence:.3f}, 매칭 위치: {match_result.center_position}"
        )

        # 액션에서 설정한 클릭 위치 사용 (필수)
        if not action.click_position:
            print(f"액션에 클릭 위치가 설정되지 않았습니다: {action.id}")
            return False

        # 매칭된 이미지의 상단 좌측 좌표에서 액션 클릭 위치만큼 오프셋 적용
        match_top_left = match_result.top_left
        action_click_x, action_click_y = action.click_position

        # 실제 클릭할 화면 좌표 계산
        actual_click_x = match_top_left[0] + action_click_x
        actual_click_y = match_top_left[1] + action_click_y

        print(
            f"클릭 위치 계산: 매칭 시작점({match_top_left}) + 액션 오프셋({action.click_position}) = 실제 클릭({actual_click_x}, {actual_click_y})"
        )

        if double_click:
            return self.input_controller.double_click(actual_click_x, actual_click_y)
        elif right_click:
            return self.input_controller.right_click(actual_click_x, actual_click_y)
        else:
            return self.input_controller.click(actual_click_x, actual_click_y)

    def _execute_type_text_action(self, action: MacroAction) -> bool:
        """텍스트 입력 액션 실행"""
        if not action.text_input:
            print("입력할 텍스트가 없습니다")
            return True

        return self.input_controller.type_text(action.text_input)

    def _execute_key_press_action(self, action: MacroAction) -> bool:
        """키 입력 액션 실행"""
        if action.key_combination:
            return self.input_controller.key_combination(action.key_combination)
        else:
            print("입력할 키가 지정되지 않았습니다")
            return False

    def _execute_scroll_action(self, action: MacroAction) -> bool:
        """스크롤 액션 실행"""
        x, y = action.click_position if action.click_position else (None, None)
        direction = action.scroll_direction or "up"
        amount = action.scroll_amount or 3

        return self.input_controller.scroll(direction, amount)

    def _execute_wait_action(self, action: MacroAction) -> bool:
        """대기 액션 실행"""
        seconds = action.wait_seconds or 1.0
        return self.input_controller.wait(seconds)

    def _execute_telegram_action(self, action: MacroAction) -> bool:
        """텔레그램 메시지 전송 액션 실행"""
        if not action.telegram_message:
            print("전송할 텔레그램 메시지가 없습니다")
            return True

        if not self.telegram_bot.is_configured():
            print("텔레그램이 설정되지 않았습니다")
            return False

        return self.telegram_bot.send_message(action.telegram_message)

    def stop_execution(self) -> None:
        """매크로 실행 중단"""
        if self.is_running:
            print("매크로 실행 중단 요청됨")
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

        print(f"이미지 탐색 실패 처리: {failure_action.value}")

        if failure_action == ImageSearchFailureAction.RESTART_SEQUENCE:
            # 매크로 처음부터 재실행
            self.restart_requested = True
            return True

        elif failure_action == ImageSearchFailureAction.SKIP_TO_NEXT:
            # 무시하고 다음 단계
            print("현재 액션 건너뛰고 다음 단계로 진행")
            return True

        else:  # STOP_EXECUTION
            # 실행 중단
            print("이미지 탐색 실패로 시퀀스 중단")
            self.stop_execution()
            return False

    def _execute_if_action(self, action: MacroAction) -> bool:
        """IF 액션 실행 - 조건 체크"""
        try:
            print(f"IF 조건 체크: {action.condition_type}")

            if not action.condition_type:
                print("IF 액션에 조건 타입이 설정되지 않음")
                return False

            # 조건 체크
            condition_result = self._check_condition(action)

            # 조건 결과를 실행 컨텍스트에 저장 (ELSE에서 사용)
            if not hasattr(self, "_condition_results"):
                self._condition_results = {}
            self._condition_results[action.id] = condition_result

            print(f"IF 조건 결과: {condition_result}")
            return True  # IF 액션 자체는 항상 성공 (조건 체크만 수행)

        except Exception as e:
            print(f"IF 액션 실행 실패: {e}")
            return False

    def _execute_else_action(self, action: MacroAction) -> bool:
        """ELSE 액션 실행 - 이전 IF 조건의 반대 결과 사용"""
        try:
            print("ELSE 조건 체크")

            # 이전 IF 조건 결과 찾기
            if not hasattr(self, "_condition_results"):
                print("ELSE 액션 실행 시 이전 IF 조건 결과가 없음")
                return False

            # 마지막 IF 조건 결과 사용
            last_if_result = None
            for result in reversed(list(self._condition_results.values())):
                last_if_result = result
                break

            if last_if_result is None:
                print("ELSE 액션 실행 시 참조할 IF 조건 결과가 없음")
                return False

            # ELSE는 IF의 반대 결과
            else_result = not last_if_result
            print(f"ELSE 조건 결과: {else_result}")
            return True  # ELSE 액션 자체는 항상 성공

        except Exception as e:
            print(f"ELSE 액션 실행 실패: {e}")
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
                    print("이미지 기반 조건이지만 이미지 템플릿이 설정되지 않음")
                    return False

                # 이미지 템플릿 가져오기 (IF 액션도 동일한 image_template_id 사용)
                template = self.config.get_image_template(action.image_template_id)
                if not template:
                    print(f"이미지 템플릿을 찾을 수 없음: {action.image_template_id}")
                    return False

                # 화면 캡쳐
                screenshot = self.screen_capture.capture_screenshot()
                if screenshot is None:
                    print("조건 체크용 화면 캡쳐 실패")
                    return False

                # 이미지 매칭
                match_result = self.image_matcher.find_image_in_screenshot(
                    screenshot,
                    template.file_path,
                    action.selected_region,
                    action.match_threshold,
                )

                image_found = match_result.found
                print(
                    f"조건 이미지 매칭 결과: {image_found}, 신뢰도: {match_result.confidence:.3f}"
                )

                if action.condition_type == ConditionType.IMAGE_FOUND:
                    return image_found
                else:  # IMAGE_NOT_FOUND
                    return not image_found

            else:
                print(f"알 수 없는 조건 타입: {action.condition_type}")
                return False

        except Exception as e:
            print(f"조건 체크 실패: {e}")
            return False

    def cleanup(self) -> None:
        """리소스 정리"""
        self.stop_execution()
        self.image_matcher.clear_cache()
        self.telegram_bot.close()
        print("매크로 엔진 정리 완료")
