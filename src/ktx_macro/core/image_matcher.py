"""
이미지 매칭 엔진 모듈
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List, Dict, Any
from pathlib import Path
import logging

from ..models.macro_models import ImageTemplate, CaptureRegion

logger = logging.getLogger(__name__)


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
        self.match_methods = [
            cv2.TM_CCOEFF_NORMED,
            cv2.TM_CCORR_NORMED,
            cv2.TM_SQDIFF_NORMED,
        ]

    def load_template(self, template_path: str) -> Optional[np.ndarray]:
        """템플릿 이미지 로드"""
        try:
            if template_path in self.template_cache:
                return self.template_cache[template_path]

            if not Path(template_path).exists():
                logger.error(f"템플릿 파일이 존재하지 않습니다: {template_path}")
                return None

            # 이미지 로드 (그레이스케일)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                logger.error(f"템플릿 이미지 로드 실패: {template_path}")
                return None

            self.template_cache[template_path] = template
            logger.debug(f"템플릿 로드 완료: {template_path}, 크기: {template.shape}")
            return template

        except Exception as e:
            logger.error(f"템플릿 로드 중 오류: {template_path}, {e}")
            return None

    def match_template(
        self,
        screenshot: np.ndarray,
        template: np.ndarray,
        threshold: float = 0.8,
        method: int = cv2.TM_CCOEFF_NORMED,
    ) -> MatchResult:
        """템플릿 매칭 수행"""
        try:
            # 스크린샷을 그레이스케일로 변환
            if len(screenshot.shape) == 3:
                screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            else:
                screenshot_gray = screenshot

            # 템플릿 매칭 수행
            result = cv2.matchTemplate(screenshot_gray, template, method)

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
                template_h, template_w = template.shape

                # 매칭된 영역의 좌표 계산
                top_left = match_location
                bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
                center_position = (
                    top_left[0] + template_w // 2,
                    top_left[1] + template_h // 2,
                )

                logger.debug(
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
                logger.debug(
                    f"이미지 매칭 실패 - 신뢰도: {match_confidence:.3f} < {threshold}"
                )
                return MatchResult(found=False, confidence=match_confidence)

        except Exception as e:
            logger.error(f"템플릿 매칭 중 오류: {e}")
            return MatchResult(found=False)

    def multi_method_match(
        self, screenshot: np.ndarray, template: np.ndarray, threshold: float = 0.8
    ) -> MatchResult:
        """여러 매칭 방법을 시도하여 최적 결과 반환"""
        best_result = MatchResult(found=False)

        for method in self.match_methods:
            result = self.match_template(screenshot, template, threshold, method)

            if result.found and result.confidence > best_result.confidence:
                best_result = result

                # 높은 신뢰도면 즉시 반환
                if result.confidence > 0.95:
                    break

        return best_result

    def find_image_in_screenshot(
        self,
        screenshot: np.ndarray,
        template_path: str,
        threshold: float = 0.8,
        region: Optional[CaptureRegion] = None,
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

            if region:
                offset_x, offset_y = region.x, region.y
                search_area = screenshot[
                    region.y : region.y + region.height,
                    region.x : region.x + region.width,
                ]

                if search_area.size == 0:
                    logger.warning(f"검색 영역이 유효하지 않습니다: {region}")
                    return MatchResult(found=False)

            # 이미지 매칭 수행
            result = self.multi_method_match(search_area, template, threshold)

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
            logger.error(f"이미지 검색 중 오류: {template_path}, {e}")
            return MatchResult(found=False)

    def find_all_matches(
        self,
        screenshot: np.ndarray,
        template_path: str,
        threshold: float = 0.8,
        region: Optional[CaptureRegion] = None,
    ) -> List[MatchResult]:
        """스크린샷에서 모든 매칭되는 이미지 찾기"""
        try:
            template = self.load_template(template_path)
            if template is None:
                return []

            # 검색 영역 설정
            search_area = screenshot
            offset_x, offset_y = 0, 0

            if region:
                offset_x, offset_y = region.x, region.y
                search_area = screenshot[
                    region.y : region.y + region.height,
                    region.x : region.x + region.width,
                ]

            # 그레이스케일 변환
            if len(search_area.shape) == 3:
                search_gray = cv2.cvtColor(search_area, cv2.COLOR_BGR2GRAY)
            else:
                search_gray = search_area

            # 템플릿 매칭
            result = cv2.matchTemplate(search_gray, template, cv2.TM_CCOEFF_NORMED)

            # 임계값 이상의 모든 위치 찾기
            locations = np.where(result >= threshold)

            matches = []
            template_h, template_w = template.shape

            for pt in zip(*locations[::-1]):  # x, y 순서로 변환
                confidence = result[pt[1], pt[0]]

                top_left = (pt[0] + offset_x, pt[1] + offset_y)
                bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
                center_position = (
                    top_left[0] + template_w // 2,
                    top_left[1] + template_h // 2,
                )

                matches.append(
                    MatchResult(
                        found=True,
                        confidence=confidence,
                        center_position=center_position,
                        top_left=top_left,
                        bottom_right=bottom_right,
                        template_size=(template_w, template_h),
                    )
                )

            # 신뢰도 순으로 정렬
            matches.sort(key=lambda x: x.confidence, reverse=True)

            logger.debug(f"매칭 결과: {len(matches)}개 찾음 (임계값: {threshold})")
            return matches

        except Exception as e:
            logger.error(f"전체 매칭 검색 중 오류: {template_path}, {e}")
            return []

    def clear_cache(self) -> None:
        """템플릿 캐시 삭제"""
        self.template_cache.clear()
        logger.debug("템플릿 캐시 삭제됨")

    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 정보 반환"""
        return {
            "cached_templates": len(self.template_cache),
            "template_paths": list(self.template_cache.keys()),
        }

