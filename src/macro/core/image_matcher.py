"""
이미지 매칭 엔진 모듈
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
from functools import reduce


class MatchResult:
    """이미지 매칭 결과"""

    def __init__(
        self,
        found: bool,
        confidence: float = 0.0,
        center_position: Optional[Tuple[int, int]] = None,
        top_left: Optional[Tuple[int, int]] = None,
        bottom_right: Optional[Tuple[int, int]] = None,
        template_size: Optional[Tuple[int, int]] = None,
    ):
        self.found = found
        self.confidence = confidence
        self.center_position = center_position
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.template_size = template_size


class ImageMatcher:
    """OpenCV 기반 이미지 매칭 엔진"""

    def __init__(self):
        self.template_cache: Dict[str, np.ndarray] = {}

    def load_template(self, template_path: str) -> Optional[np.ndarray]:
        """템플릿 이미지 로드"""
        try:
            if template_path in self.template_cache:
                return self.template_cache[template_path]

            template_path_obj = Path(template_path)
            if not template_path_obj.exists():
                print(
                    f"[Image Matcher] 템플릿 파일이 존재하지 않습니다: {template_path}"
                )
                return None

            # Windows에서 한글 파일명 문제 해결을 위한 여러 방법 시도
            template = None

            template = cv2.imread(str(template_path_obj))

            if template is None:
                print(f"[Image Matcher] 템플릿 이미지 로드 실패: {template_path}")
                return None

            self.template_cache[template_path] = template
            print(
                f"[Image Matcher] 템플릿 로드 완료: {template_path}, 크기: {template.shape}"
            )
            return template

        except Exception as e:
            print(f"[Image Matcher] 템플릿 로드 중 오류: {template_path}, {e}")
            return None

    def match_template(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        threshold: float = 0.8,
        method: int = cv2.TM_CCORR_NORMED,
    ) -> MatchResult:
        print("Start match_template")

        def preprocess_color(template: np.ndarray, screenshot: np.ndarray):
            # 템플릿 채널별 Otsu 적용
            channels_t = cv2.split(template)
            channels_s = cv2.split(screenshot)

            th_template_channels = []
            th_screen_channels = []

            for t_ch, s_ch in zip(channels_t, channels_s):
                _, th_t = cv2.threshold(
                    t_ch, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
                )
                _, th_s = cv2.threshold(s_ch, _, 255, cv2.THRESH_BINARY_INV)
                th_template_channels.append(th_t)
                th_screen_channels.append(th_s)

            return (
                cv2.merge(th_template_channels),
                cv2.merge(th_screen_channels),
                reduce(cv2.bitwise_or, th_template_channels),
            )

        """템플릿 매칭 수행"""
        try:
            # 템플릿/스크린샷을 이진화
            th_template, th_screen, mask = preprocess_color(template, screenshot)

            # Template Matching
            cv2.imwrite("template.png", template)
            cv2.imwrite("screenshot.png", screenshot)
            cv2.imwrite("th_template.png", th_template)
            cv2.imwrite("th_screen.png", th_screen)
            cv2.imwrite("mask.png", mask)
            # cv2.imwrite("mask.png", mask)

            # 템플릿 매칭 수행
            result = cv2.matchTemplate(screenshot, template, method, mask=mask)

            # 최적 매칭 위치 찾기
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            # TM_SQDIFF 계열은 최소값이 최적 매치
            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                match_confidence = 1.0 - min_val
                match_location = min_loc
            else:
                match_confidence = max_val
                match_location = max_loc

            # 매칭 성공 여부 판단
            found = match_confidence >= threshold

            if found:
                # 템플릿 크기
                template_h, template_w, _ = template.shape

                # 매칭된 영역의 좌표 계산
                top_left = match_location
                bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
                center_position = (
                    top_left[0] + template_w // 2,
                    top_left[1] + template_h // 2,
                )

                print(
                    f"이미지 매칭 성공 - 신뢰도: {match_confidence:.3f}, "
                    f"중심: {center_position}, 영역: {top_left} ~ {bottom_right}"
                )

                return MatchResult(
                    found=True,
                    confidence=match_confidence,
                    center_position=center_position,
                    top_left=top_left,
                    bottom_right=bottom_right,
                    template_size=(template_w, template_h),
                )
            else:
                print(
                    f"이미지 매칭 실패 - 신뢰도: {match_confidence:.3f} < {threshold}"
                )
                return MatchResult(found=False, confidence=match_confidence)

        except Exception as e:
            print(f"[Image Matcher] 템플릿 매칭 중 오류: {e}")
            return MatchResult(found=False)

    def find_image_in_screenshot(
        self,
        screenshot: np.ndarray,
        template_path: str,
        template_region: Optional[Tuple[int, int, int, int]] = None,
        threshold: float = 0.8,
    ) -> MatchResult:
        """스크린샷에서 이미지 찾기"""
        try:
            # 템플릿 로드
            template = self.load_template(template_path)
            if template is None:
                return MatchResult(found=False)

            # 검색 영역 제한
            search_area = screenshot
            offset_x, offset_y = 0, 0

            if template_region:
                template = template[
                    template_region[1] : template_region[3],
                    template_region[0] : template_region[2],
                ]
                offset_x, offset_y = template_region[0], template_region[1]

            # 이미지 매칭 수행
            result = self.match_template(search_area, template, threshold)

            # 오프셋 적용 (영역 제한한 경우)
            if result.found and (offset_x > 0 or offset_y > 0):
                result.center_position = (
                    result.center_position[0] + offset_x,
                    result.center_position[1] + offset_y,
                )
                result.top_left = (
                    result.top_left[0] + offset_x,
                    result.top_left[1] + offset_y,
                )
                result.bottom_right = (
                    result.bottom_right[0] + offset_x,
                    result.bottom_right[1] + offset_y,
                )

            return result

        except Exception as e:
            print(f"[Image Matcher] 이미지 검색 중 오류: {template_path}, {e}")
            return MatchResult(found=False)

    def clear_cache(self) -> None:
        """템플릿 캐시 삭제"""
        self.template_cache.clear()
        print("템플릿 캐시 삭제됨")

    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 정보 반환"""
        return {
            "cached_templates": len(self.template_cache),
            "template_paths": list(self.template_cache.keys()),
        }
