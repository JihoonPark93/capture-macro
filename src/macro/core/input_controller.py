"""
마우스/키보드 입력 제어 모듈
"""

import pyautogui
import time
import logging
from typing import List, Optional, Tuple
import platform
import pyperclip

logger = logging.getLogger(__name__)


class InputController:
    """마우스/키보드 입력 제어 클래스"""

    def __init__(self):
        # PyAutoGUI 설정
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

        self.platform = platform.system().lower()

        # 기본 지연 시간
        self.default_delay = 0
        self.click_delay = 0
        self.key_delay = 0

        # 마우스 이동 설정
        self.mouse_move_duration = 0

        # 좌표 스케일링 팩터 (HiDPI 대응)
        self.scale_factor = self._get_display_scale_factor()

        print(f"Display scale factor: {self.scale_factor}")

    def _get_display_scale_factor(self) -> float:
        """디스플레이 스케일 팩터 계산"""
        try:
            # PyAutoGUI의 화면 크기와 실제 스크린샷 크기 비교
            screen_size = pyautogui.size()
            screenshot = pyautogui.screenshot()

            # 스케일 팩터 계산
            scale_x = screenshot.width / screen_size.width
            scale_y = screenshot.height / screen_size.height

            # 일반적으로 x, y 스케일이 같으므로 x 스케일 사용
            scale_factor = scale_x

            print(
                f"Screen size: {screen_size}, Screenshot size: {screenshot.size}, Scale: {scale_factor}"
            )

            return scale_factor

        except Exception as e:
            print(f"스케일 팩터 계산 실패: {e}")
            return 1.0  # 기본값

    def _adjust_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """HiDPI 디스플레이를 위한 좌표 보정"""
        if self.scale_factor != 1.0:
            adjusted_x = int(x / self.scale_factor)
            adjusted_y = int(y / self.scale_factor)
            print(
                f"좌표 보정: ({x}, {y}) -> ({adjusted_x}, {adjusted_y}) (scale: {self.scale_factor})"
            )
            return adjusted_x, adjusted_y
        return x, y

    def get_scale_factor(self) -> float:
        """현재 디스플레이 스케일 팩터 반환"""
        return self.scale_factor

    def adjust_coordinates_for_capture(self, x: int, y: int) -> Tuple[int, int]:
        """캡쳐된 좌표를 클릭 실행에 맞게 보정 (외부 접근용)"""
        return self._adjust_coordinates(x, y)

    def click_with_adjusted_coordinates(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.0,
    ) -> bool:
        """이미 보정된 좌표로 직접 클릭 (추가 보정 없음)"""
        try:
            # 지정된 위치로 이동 (보정 없이)
            pyautogui.moveTo(x, y, duration=self.mouse_move_duration)
            time.sleep(self.click_delay)

            print(
                f"마우스 클릭 (보정된 좌표): 버튼={button}, 횟수={clicks}, 위치=({x}, {y})"
            )
            pyautogui.click(
                x=x,
                y=y,
                clicks=clicks,
                interval=interval,
                button=button,
            )

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            print(f"마우스 클릭 실패 (보정된 좌표): {e}")
            logger.error(f"마우스 클릭 실패: {e}")
            return False

    def move_mouse(
        self, x: int, y: int, duration: Optional[float] = None, smooth: bool = False
    ) -> bool:
        """마우스 이동"""
        try:
            # 좌표 보정 적용
            adjusted_x, adjusted_y = self._adjust_coordinates(x, y)

            if duration is None:
                duration = self.mouse_move_duration if smooth else 0

            current_x, current_y = pyautogui.position()
            print(
                f"마우스 이동: ({current_x}, {current_y}) -> ({adjusted_x}, {adjusted_y}) [원본: ({x}, {y})]"
            )

            # 여러 번 시도로 정확도 향상 (macOS 호환성)
            max_attempts = 1
            for attempt in range(max_attempts):
                pyautogui.moveTo(adjusted_x, adjusted_y, duration=duration)

                # 이동 확인
                final_x, final_y = pyautogui.position()
                error_x = abs(final_x - adjusted_x)
                error_y = abs(final_y - adjusted_y)

                if error_x <= 3 and error_y <= 3:  # 3픽셀 오차 허용
                    print(
                        f"마우스 이동 성공 ({attempt + 1}번째 시도): ({final_x}, {final_y})"
                    )
                    return True

                if attempt < max_attempts - 1:
                    print(
                        f"마우스 이동 재시도 {attempt + 2}/{max_attempts}: 오차 ({error_x}, {error_y})"
                    )
                    duration = 0  # 다음 시도는 즉시 이동

            # 모든 시도 실패
            print(
                f"마우스 이동 부정확 ({max_attempts}번 시도): 목표({adjusted_x}, {adjusted_y}), 실제({final_x}, {final_y})"
            )
            return False

        except Exception as e:
            print(f"마우스 이동 실패: ({x}, {y}), {e}")
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
                # 좌표 보정 적용
                adjusted_x, adjusted_y = self._adjust_coordinates(x, y)

                # 지정된 위치로 이동 후 클릭
                if not self.move_mouse(x, y):
                    return False
                time.sleep(self.click_delay)

                print(
                    f"마우스 클릭: 버튼={button}, 횟수={clicks}, 위치=({adjusted_x}, {adjusted_y}) [원본: ({x}, {y})]"
                )
                pyautogui.click(
                    x=adjusted_x,
                    y=adjusted_y,
                    clicks=clicks,
                    interval=interval,
                    button=button,
                )
            else:
                print(f"마우스 클릭: 버튼={button}, 횟수={clicks}, 현재 위치")
                pyautogui.click(clicks=clicks, interval=interval, button=button)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            print(f"마우스 클릭 실패: ({x}, {y}), {e}")
            return False

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """더블클릭"""
        try:
            if x is not None and y is not None:
                # 좌표 보정 적용
                adjusted_x, adjusted_y = self._adjust_coordinates(x, y)

                if not self.move_mouse(x, y):
                    return False
                time.sleep(self.click_delay)

                print(f"더블클릭: ({adjusted_x}, {adjusted_y}) [원본: ({x}, {y})]")
                pyautogui.doubleClick(x=adjusted_x, y=adjusted_y)
            else:
                print(f"더블클릭: 현재 위치")
                pyautogui.doubleClick()

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            print(f"더블클릭 실패: ({x}, {y}), {e}")
            return False

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """우클릭"""
        try:
            if x is not None and y is not None:
                # 좌표 보정 적용
                adjusted_x, adjusted_y = self._adjust_coordinates(x, y)

                if not self.move_mouse(x, y):
                    return False
                time.sleep(self.click_delay)

                print(f"우클릭: ({adjusted_x}, {adjusted_y}) [원본: ({x}, {y})]")
                pyautogui.rightClick(x=adjusted_x, y=adjusted_y)
            else:
                print(f"우클릭: 현재 위치")
                pyautogui.rightClick()

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            print(f"우클릭 실패: ({x}, {y}), {e}")
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
            print(f"드래그: ({from_x}, {from_y}) -> ({to_x}, {to_y})")

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
            print(f"드래그 실패: ({from_x}, {from_y}) -> ({to_x}, {to_y}), {e}")
            return False

    def scroll(
        self,
        direction: str = "up",
        amount: int = 3,
    ) -> bool:
        """스크롤"""
        try:
            # 스크롤 방향 설정
            scroll_amount = amount if direction in ["up", "right"] else -amount

            print(f"스크롤: 방향={direction}, 양={amount}")

            if direction in ["up", "down"]:
                pyautogui.scroll(scroll_amount)
            elif direction in ["left", "right"]:
                pyautogui.hscroll(scroll_amount)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            print(f"스크롤 실패: {direction}, {amount}, {e}")
            return False

    def type_text(self, text: str, interval: float = 0.02) -> bool:
        """텍스트 입력"""
        try:
            if not text:
                return True

            print(f"텍스트 입력: '{text[:50]}{'...' if len(text) > 50 else ''}'")

            pyperclip.copy(text)

            if self.platform == "darwin":  # macOS
                pyautogui.hotkey("command", "v")
            else:  # Windows, Linux 등
                pyautogui.hotkey("ctrl", "v")
            # pyautogui.write(text, interval=interval)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            print(f"텍스트 입력 실패: '{text}', {e}")
            return False

    def press_key(self, key: str, presses: int = 1, interval: float = 0.0) -> bool:
        """키 누르기"""
        try:
            print(f"키 입력: {key}, 횟수={presses}")

            pyautogui.press(key, presses=presses, interval=interval)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            print(f"키 입력 실패: {key}, {e}")
            return False

    def key_combination(self, keys: List[str]) -> bool:
        """키 조합 입력"""
        try:
            if not keys:
                return True

            print(f"키 조합: {' + '.join(keys)}")

            # 키 조합 실행
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            print(f"키 조합 실패: {keys}, {e}")
            return False

    def hold_key(self, key: str, duration: float = 1.0) -> bool:
        """키 길게 누르기"""
        try:
            print(f"키 길게 누르기: {key}, {duration}초")

            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)

            time.sleep(self.default_delay)
            return True

        except Exception as e:
            print(f"키 길게 누르기 실패: {key}, {e}")
            return False

    def get_mouse_position(self) -> Tuple[int, int]:
        """현재 마우스 위치 가져오기"""
        try:
            return pyautogui.position()
        except Exception as e:
            print(f"마우스 위치 가져오기 실패: {e}")
            return (0, 0)

    def wait(self, seconds: float) -> bool:
        """대기"""
        try:
            if seconds <= 0:
                return True

            print(f"대기: {seconds}초")
            time.sleep(seconds)
            return True

        except Exception as e:
            print(f"대기 실패: {seconds}초, {e}")
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

        print(
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
