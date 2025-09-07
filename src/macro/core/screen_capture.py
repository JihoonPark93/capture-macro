"""
화면 캡쳐 모듈
"""

import cv2
import numpy as np
import pyautogui
from typing import Optional, List
import logging
import platform

try:
    import screeninfo
except ImportError:
    screeninfo = None


logger = logging.getLogger(__name__)


class ScreenCapture:
    """화면 캡쳐 관리 클래스"""

    def __init__(self):
        # PyAutoGUI 설정
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

        # 모니터 정보 캐시
        self._monitors: Optional[List[dict]] = None
        self._primary_monitor: Optional[dict] = None

        # 플랫폼별 설정
        self.platform = platform.system().lower()

        # 스크린샷 품질 설정
        self.screenshot_format = "PNG"

        # 디스플레이 스케일 팩터 (HiDPI 대응)
        self.scale_factor = self._get_display_scale_factor()

        logger.info(f"ScreenCapture - Display scale factor: {self.scale_factor}")

    def _get_display_scale_factor(self) -> float:
        """디스플레이 스케일 팩터 계산"""
        try:
            # PyAutoGUI의 화면 크기와 실제 스크린샷 크기 비교
            screen_size = pyautogui.size()
            screenshot = pyautogui.screenshot()

            # 스케일 팩터 계산
            scale_x = screenshot.width / screen_size.width

            # 일반적으로 x, y 스케일이 같으므로 x 스케일 사용
            scale_factor = scale_x

            logger.debug(
                f"ScreenCapture - Screen size: {screen_size}, Screenshot size: {screenshot.size}, Scale: {scale_factor}"
            )

            return scale_factor

        except Exception as e:
            logger.error(f"ScreenCapture - 스케일 팩터 계산 실패: {e}")
            return 1.0  # 기본값

    def get_scale_factor(self) -> float:
        """스케일 팩터 반환"""
        return self.scale_factor

    def get_monitors(self) -> List[dict]:
        """모니터 정보 가져오기"""
        if self._monitors is not None:
            return self._monitors

        monitors = []

        try:
            if screeninfo:
                # screeninfo 라이브러리 사용
                for i, monitor in enumerate(screeninfo.get_monitors()):
                    monitors.append(
                        {
                            "id": i,
                            "name": getattr(monitor, "name", f"Monitor {i+1}"),
                            "x": monitor.x,
                            "y": monitor.y,
                            "width": monitor.width,
                            "height": monitor.height,
                            "is_primary": (
                                monitor.is_primary
                                if hasattr(monitor, "is_primary")
                                else (i == 0)
                            ),
                        }
                    )
            else:
                # 기본 모니터만 사용
                screen_size = pyautogui.size()
                monitors.append(
                    {
                        "id": 0,
                        "name": "Primary Monitor",
                        "x": 0,
                        "y": 0,
                        "width": screen_size.width,
                        "height": screen_size.height,
                        "is_primary": True,
                    }
                )

        except Exception as e:
            logger.error(f"모니터 정보 가져오기 실패: {e}")
            # 폴백: 기본 화면 크기 사용
            screen_size = pyautogui.size()
            monitors.append(
                {
                    "id": 0,
                    "name": "Default Monitor",
                    "x": 0,
                    "y": 0,
                    "width": screen_size.width,
                    "height": screen_size.height,
                    "is_primary": True,
                }
            )

        self._monitors = monitors

        # 주 모니터 찾기
        for monitor in monitors:
            if monitor["is_primary"]:
                self._primary_monitor = monitor
                break

        if not self._primary_monitor and monitors:
            self._primary_monitor = monitors[0]

        logger.debug(f"모니터 정보: {len(monitors)}개 모니터 감지")
        return monitors


    def capture_full_screen(
        self, monitor_id: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """전체 화면 캡쳐"""
        try:
            if monitor_id is not None:
                monitors = self.get_monitors()
                if monitor_id < len(monitors):
                    monitor = monitors[monitor_id]
                    region = (
                        monitor["x"],
                        monitor["y"],
                        monitor["width"],
                        monitor["height"],
                    )
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    logger.warning(f"유효하지 않은 모니터 ID: {monitor_id}")
                    screenshot = pyautogui.screenshot()
            else:
                screenshot = pyautogui.screenshot()

            # PIL Image를 OpenCV 포맷으로 변환
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            logger.debug(f"전체 화면 캡쳐 완료: {screenshot_cv.shape}")
            return screenshot_cv

        except Exception as e:
            logger.error(f"전체 화면 캡쳐 실패: {e}")
            return None
