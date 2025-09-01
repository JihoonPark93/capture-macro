"""
마우스/키보드 입력 제어 모듈
"""

import pyautogui
import time
import logging
from typing import List, Optional, Tuple, Union
import platform

from ..models.macro_models import ActionType

logger = logging.getLogger(__name__)


class InputController:
    """마우스/키보드 입력 제어 클래스"""

    def __init__(self):
        # PyAutoGUI 설정
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

        self.platform = platform.system().lower()

        # 기본 지연 시간
        self.default_delay = 0.1
        self.click_delay = 0.05
        self.key_delay = 0.02

        # 마우스 이동 설정
        self.mouse_move_duration = 0.2

    def move_mouse(
        self, x: int, y: int, duration: Optional[float] = None, smooth: bool = True
    ) -> bool:
        """마우스 이동"""
        try:
            if duration is None:
                duration = self.mouse_move_duration if smooth else 0

            current_x, current_y = pyautogui.position()
            logger.debug(f"마우스 이동: ({current_x}, {current_y}) -> ({x}, {y})")

            # 여러 번 시도로 정확도 향상 (macOS 호환성)
            max_attempts = 3
            for attempt in range(max_attempts):
                pyautogui.moveTo(x, y, duration=duration)
                time.sleep(0.05)  # 짧은 대기

                # 이동 확인
                final_x, final_y = pyautogui.position()
                error_x = abs(final_x - x)
                error_y = abs(final_y - y)

                if error_x <= 3 and error_y <= 3:  # 3픽셀 오차 허용
                    logger.debug(
                        f"마우스 이동 성공 ({attempt + 1}번째 시도): ({final_x}, {final_y})"
                    )
                    return True

                if attempt < max_attempts - 1:
                    logger.debug(
                        f"마우스 이동 재시도 {attempt + 2}/{max_attempts}: 오차 ({error_x}, {error_y})"
                    )
                    duration = 0  # 다음 시도는 즉시 이동

            # 모든 시도 실패
            logger.warning(
                f"마우스 이동 부정확 ({max_attempts}번 시도): 목표({x}, {y}), 실제({final_x}, {final_y})"
            )
            return False

        except Exception as e:
            logger.error(f"마우스 이동 실패: ({x}, {y}), {e}")
            return False

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
    ) -> bool:
        """마우스 클릭"""
        try:
            if x is not None and y is not None:
                # 지정된 위치로 이동 후 클릭
                if not self.move_mouse(x, y):
                    return False
                time.sleep(self.click_delay)

            logger.debug(f"마우스 클릭: 버튼={button}, 횟수={clicks}, 위치=({x}, {y})")

            pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            logger.error(f"마우스 클릭 실패: ({x}, {y}), {e}")
            return False

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """더블클릭"""
        try:
            if x is not None and y is not None:
                if not self.move_mouse(x, y):
                    return False
                time.sleep(self.click_delay)

            logger.debug(f"더블클릭: ({x}, {y})")
            pyautogui.doubleClick(x=x, y=y)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            logger.error(f"더블클릭 실패: ({x}, {y}), {e}")
            return False

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """우클릭"""
        try:
            if x is not None and y is not None:
                if not self.move_mouse(x, y):
                    return False
                time.sleep(self.click_delay)

            logger.debug(f"우클릭: ({x}, {y})")
            pyautogui.rightClick(x=x, y=y)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            logger.error(f"우클릭 실패: ({x}, {y}), {e}")
            return False

    def drag(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration: float = 0.5,
        button: str = "left",
    ) -> bool:
        """드래그"""
        try:
            logger.debug(f"드래그: ({from_x}, {from_y}) -> ({to_x}, {to_y})")

            # 시작 위치로 이동
            if not self.move_mouse(from_x, from_y):
                return False

            time.sleep(self.click_delay)

            # 드래그 수행
            pyautogui.drag(
                to_x - from_x, to_y - from_y, duration=duration, button=button
            )

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            logger.error(f"드래그 실패: ({from_x}, {from_y}) -> ({to_x}, {to_y}), {e}")
            return False

    def scroll(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        direction: str = "up",
        amount: int = 3,
    ) -> bool:
        """스크롤"""
        try:
            if x is not None and y is not None:
                if not self.move_mouse(x, y):
                    return False

            # 스크롤 방향 설정
            scroll_amount = amount if direction in ["up", "right"] else -amount

            logger.debug(f"스크롤: 방향={direction}, 양={amount}, 위치=({x}, {y})")

            if direction in ["up", "down"]:
                pyautogui.scroll(scroll_amount, x=x, y=y)
            elif direction in ["left", "right"]:
                pyautogui.hscroll(scroll_amount, x=x, y=y)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            logger.error(f"스크롤 실패: {direction}, {amount}, ({x}, {y}), {e}")
            return False

    def type_text(self, text: str, interval: float = 0.02) -> bool:
        """텍스트 입력"""
        try:
            if not text:
                return True

            logger.debug(f"텍스트 입력: '{text[:50]}{'...' if len(text) > 50 else ''}'")

            # 한글 처리를 위한 개별 문자 입력
            if self._contains_korean(text):
                for char in text:
                    pyautogui.write(char, interval=interval)
                    time.sleep(self.key_delay)
            else:
                pyautogui.write(text, interval=interval)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            logger.error(f"텍스트 입력 실패: '{text}', {e}")
            return False

    def press_key(self, key: str, presses: int = 1, interval: float = 0.0) -> bool:
        """키 누르기"""
        try:
            logger.debug(f"키 입력: {key}, 횟수={presses}")

            pyautogui.press(key, presses=presses, interval=interval)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            logger.error(f"키 입력 실패: {key}, {e}")
            return False

    def key_combination(self, keys: List[str]) -> bool:
        """키 조합 입력"""
        try:
            if not keys:
                return True

            logger.debug(f"키 조합: {' + '.join(keys)}")

            # 키 조합 실행
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            logger.error(f"키 조합 실패: {keys}, {e}")
            return False

    def hold_key(self, key: str, duration: float = 1.0) -> bool:
        """키 길게 누르기"""
        try:
            logger.debug(f"키 길게 누르기: {key}, {duration}초")

            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            logger.error(f"키 길게 누르기 실패: {key}, {e}")
            return False

    def get_mouse_position(self) -> Tuple[int, int]:
        """현재 마우스 위치 가져오기"""
        try:
            return pyautogui.position()
        except Exception as e:
            logger.error(f"마우스 위치 가져오기 실패: {e}")
            return (0, 0)

    def wait(self, seconds: float) -> bool:
        """대기"""
        try:
            if seconds <= 0:
                return True

            logger.debug(f"대기: {seconds}초")
            time.sleep(seconds)
            return True

        except Exception as e:
            logger.error(f"대기 실패: {seconds}초, {e}")
            return False

    def execute_action(self, action_type: ActionType, **kwargs) -> bool:
        """액션 타입에 따른 실행"""
        try:
            if action_type == ActionType.CLICK:
                return self.click(
                    x=kwargs.get("x"),
                    y=kwargs.get("y"),
                    button=kwargs.get("button", "left"),
                )

            elif action_type == ActionType.DOUBLE_CLICK:
                return self.double_click(x=kwargs.get("x"), y=kwargs.get("y"))

            elif action_type == ActionType.RIGHT_CLICK:
                return self.right_click(x=kwargs.get("x"), y=kwargs.get("y"))

            elif action_type == ActionType.DRAG:
                return self.drag(
                    from_x=kwargs.get("from_x"),
                    from_y=kwargs.get("from_y"),
                    to_x=kwargs.get("to_x"),
                    to_y=kwargs.get("to_y"),
                    duration=kwargs.get("duration", 0.5),
                )

            elif action_type == ActionType.TYPE_TEXT:
                return self.type_text(
                    text=kwargs.get("text", ""), interval=kwargs.get("interval", 0.02)
                )

            elif action_type == ActionType.KEY_PRESS:
                keys = kwargs.get("keys", [])
                if isinstance(keys, str):
                    return self.press_key(keys)
                elif isinstance(keys, list):
                    return self.key_combination(keys)

            elif action_type == ActionType.SCROLL:
                return self.scroll(
                    x=kwargs.get("x"),
                    y=kwargs.get("y"),
                    direction=kwargs.get("direction", "up"),
                    amount=kwargs.get("amount", 3),
                )

            elif action_type == ActionType.WAIT:
                return self.wait(kwargs.get("seconds", 1.0))

            else:
                logger.error(f"지원하지 않는 액션 타입: {action_type}")
                return False

        except Exception as e:
            logger.error(f"액션 실행 실패: {action_type}, {e}")
            return False

    def _contains_korean(self, text: str) -> bool:
        """한글 포함 여부 확인"""
        for char in text:
            if ord("가") <= ord(char) <= ord("힣"):
                return True
        return False

    def set_delays(
        self,
        default_delay: Optional[float] = None,
        click_delay: Optional[float] = None,
        key_delay: Optional[float] = None,
        mouse_move_duration: Optional[float] = None,
    ) -> None:
        """지연 시간 설정"""
        if default_delay is not None:
            self.default_delay = default_delay
        if click_delay is not None:
            self.click_delay = click_delay
        if key_delay is not None:
            self.key_delay = key_delay
        if mouse_move_duration is not None:
            self.mouse_move_duration = mouse_move_duration

        logger.debug(
            f"지연 시간 설정 업데이트: default={self.default_delay}, "
            f"click={self.click_delay}, key={self.key_delay}, "
            f"mouse_move={self.mouse_move_duration}"
        )

    def get_controller_info(self) -> dict:
        """컨트롤러 정보 반환"""
        return {
            "platform": self.platform,
            "failsafe_enabled": pyautogui.FAILSAFE,
            "pause_duration": pyautogui.PAUSE,
            "delays": {
                "default": self.default_delay,
                "click": self.click_delay,
                "key": self.key_delay,
                "mouse_move": self.mouse_move_duration,
            },
            "current_mouse_position": self.get_mouse_position(),
        }
