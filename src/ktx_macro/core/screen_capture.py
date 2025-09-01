"""
화면 캡쳐 모듈
"""

import cv2
import numpy as np
import pyautogui
from typing import Optional, Tuple, List
from pathlib import Path
import logging
import platform
from datetime import datetime

try:
    import screeninfo
except ImportError:
    screeninfo = None

from ..models.macro_models import CaptureRegion

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

    def get_primary_monitor(self) -> dict:
        """주 모니터 정보 가져오기"""
        if self._primary_monitor is None:
            self.get_monitors()
        return self._primary_monitor or {
            "id": 0,
            "x": 0,
            "y": 0,
            "width": 1920,
            "height": 1080,
        }

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

    def capture_region(self, region: CaptureRegion) -> Optional[np.ndarray]:
        """특정 영역 캡쳐"""
        try:
            # 영역 유효성 검사
            if region.width <= 0 or region.height <= 0:
                logger.error(f"유효하지 않은 캡쳐 영역: {region}")
                return None

            # 화면 경계 확인
            monitors = self.get_monitors()
            valid_region = False

            for monitor in monitors:
                if (
                    region.x >= monitor["x"]
                    and region.y >= monitor["y"]
                    and region.x + region.width <= monitor["x"] + monitor["width"]
                    and region.y + region.height <= monitor["y"] + monitor["height"]
                ):
                    valid_region = True
                    break

            if not valid_region:
                logger.warning(f"캡쳐 영역이 모니터 범위를 벗어남: {region}")

            # 영역 캡쳐
            screenshot = pyautogui.screenshot(
                region=(region.x, region.y, region.width, region.height)
            )

            # PIL Image를 OpenCV 포맷으로 변환
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            logger.debug(f"영역 캡쳐 완료: {region} -> {screenshot_cv.shape}")
            return screenshot_cv

        except Exception as e:
            logger.error(f"영역 캡쳐 실패: {region}, {e}")
            return None

    def save_screenshot(
        self, image: np.ndarray, file_path: str, create_dirs: bool = True
    ) -> bool:
        """스크린샷 저장"""
        try:
            path = Path(file_path)

            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)

            # OpenCV 포맷으로 저장
            success = cv2.imwrite(str(path), image)

            if success:
                logger.debug(f"스크린샷 저장 완료: {file_path}")
                return True
            else:
                logger.error(f"스크린샷 저장 실패: {file_path}")
                return False

        except Exception as e:
            logger.error(f"스크린샷 저장 중 오류: {file_path}, {e}")
            return False

    def capture_and_save(
        self,
        region: Optional[CaptureRegion] = None,
        file_path: Optional[str] = None,
        monitor_id: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """캡쳐 후 자동 저장"""
        try:
            # 캡쳐 수행
            if region:
                screenshot = self.capture_region(region)
            else:
                screenshot = self.capture_full_screen(monitor_id)

            if screenshot is None:
                return False, None

            # 파일명 생성
            if file_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = f"screenshot_{timestamp}.png"

            # 저장
            success = self.save_screenshot(screenshot, file_path)
            return success, file_path if success else None

        except Exception as e:
            logger.error(f"캡쳐 및 저장 실패: {e}")
            return False, None

    def get_pixel_color(self, x: int, y: int) -> Optional[Tuple[int, int, int]]:
        """특정 위치의 픽셀 색상 가져오기"""
        try:
            # PyAutoGUI는 RGB 순서로 반환
            color = pyautogui.pixel(x, y)
            logger.debug(f"픽셀 색상 ({x}, {y}): {color}")
            return color

        except Exception as e:
            logger.error(f"픽셀 색상 가져오기 실패: ({x}, {y}), {e}")
            return None

    def validate_coordinates(self, x: int, y: int) -> bool:
        """좌표 유효성 검증"""
        try:
            monitors = self.get_monitors()

            for monitor in monitors:
                if (
                    monitor["x"] <= x < monitor["x"] + monitor["width"]
                    and monitor["y"] <= y < monitor["y"] + monitor["height"]
                ):
                    return True

            logger.warning(f"유효하지 않은 좌표: ({x}, {y})")
            return False

        except Exception as e:
            logger.error(f"좌표 검증 중 오류: ({x}, {y}), {e}")
            return False

    def get_screen_size(self, monitor_id: Optional[int] = None) -> Tuple[int, int]:
        """화면 크기 가져오기"""
        try:
            if monitor_id is not None:
                monitors = self.get_monitors()
                if monitor_id < len(monitors):
                    monitor = monitors[monitor_id]
                    return monitor["width"], monitor["height"]

            # 전체 화면 크기 (모든 모니터 포함)
            screen_size = pyautogui.size()
            return screen_size.width, screen_size.height

        except Exception as e:
            logger.error(f"화면 크기 가져오기 실패: {e}")
            return 1920, 1080  # 기본값

    def create_region_from_coordinates(
        self, x1: int, y1: int, x2: int, y2: int
    ) -> CaptureRegion:
        """좌표로부터 캡쳐 영역 생성"""
        # 좌표 정규화 (좌상단, 우하단 순서로)
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)

        return CaptureRegion(x=left, y=top, width=right - left, height=bottom - top)

    def refresh_monitor_info(self) -> None:
        """모니터 정보 새로고침"""
        self._monitors = None
        self._primary_monitor = None
        logger.debug("모니터 정보 캐시 초기화됨")

    def get_capture_info(self) -> dict:
        """캡쳐 관련 정보 반환"""
        monitors = self.get_monitors()
        primary = self.get_primary_monitor()

        return {
            "platform": self.platform,
            "monitor_count": len(monitors),
            "monitors": monitors,
            "primary_monitor": primary,
            "screenshot_format": self.screenshot_format,
            "failsafe_enabled": pyautogui.FAILSAFE,
        }

