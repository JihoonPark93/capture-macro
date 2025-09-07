"""
설정 유효성 검증 모듈
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

from ..models.macro_models import (
    MacroConfig,
    TelegramConfig,
    ImageTemplate,
    MacroSequence,
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """유효성 검증 오류"""

    pass


class ConfigValidator:
    """설정 유효성 검증 클래스"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_config(self, config: MacroConfig) -> Tuple[bool, List[str], List[str]]:
        """전체 설정 유효성 검증"""
        self.errors.clear()
        self.warnings.clear()

        try:
            # 기본 설정 검증
            self._validate_basic_config(config)

            # 텔레그램 설정 검증
            self._validate_telegram_config(config.telegram_config)

            # 이미지 템플릿 검증
            self._validate_image_templates(config.image_templates)

            # 매크로 시퀀스 검증
            self._validate_macro_sequences(
                config.macro_sequences, config.image_templates
            )

            # 경로 검증
            self._validate_paths(config)

        except Exception as e:
            self.errors.append(f"검증 중 예상치 못한 오류: {e}")

        is_valid = len(self.errors) == 0
        return is_valid, self.errors.copy(), self.warnings.copy()

    def _validate_basic_config(self, config: MacroConfig) -> None:
        """기본 설정 검증"""
        # 버전 검증
        if not config.version or not isinstance(config.version, str):
            self.errors.append("버전 정보가 유효하지 않습니다")

        # 임계값 검증
        if not (0.0 <= config.match_confidence_threshold <= 1.0):
            self.errors.append("매칭 신뢰도 임계값은 0.0과 1.0 사이여야 합니다")

        # 지연 시간 검증
        if config.action_delay < 0:
            self.errors.append("액션 지연 시간은 0 이상이어야 합니다")

        if config.auto_save_interval < 10:
            self.warnings.append("자동 저장 간격이 너무 짧습니다 (최소 10초 권장)")
        elif config.auto_save_interval > 300:
            self.warnings.append("자동 저장 간격이 너무 깁니다 (최대 5분 권장)")

    def _validate_telegram_config(self, telegram_config: TelegramConfig) -> None:
        """텔레그램 설정 검증"""
        if not telegram_config.enabled:
            return

        # 봇 토큰 검증
        if not telegram_config.bot_token:
            self.errors.append("텔레그램이 활성화되었지만 봇 토큰이 없습니다")
        elif not self._is_valid_telegram_token(telegram_config.bot_token):
            self.errors.append("텔레그램 봇 토큰 형식이 유효하지 않습니다")

        # 채팅 ID 검증
        if not telegram_config.chat_id:
            self.errors.append("텔레그램이 활성화되었지만 채팅 ID가 없습니다")
        elif not self._is_valid_chat_id(telegram_config.chat_id):
            self.errors.append("텔레그램 채팅 ID 형식이 유효하지 않습니다")

    def _validate_image_templates(self, templates: List[ImageTemplate]) -> None:
        """이미지 템플릿 검증"""
        if not templates:
            self.warnings.append("등록된 이미지 템플릿이 없습니다")
            return

        template_ids = set()
        template_names = set()

        for template in templates:
            # ID 중복 검증
            if template.id in template_ids:
                self.errors.append(f"중복된 템플릿 ID: {template.id}")
            template_ids.add(template.id)

            # 이름 중복 검증
            if template.name in template_names:
                self.warnings.append(f"중복된 템플릿 이름: {template.name}")
            template_names.add(template.name)

            # 파일 존재 검증
            if not Path(template.file_path).exists():
                self.errors.append(
                    f"템플릿 이미지 파일이 존재하지 않습니다: {template.file_path}"
                )

            # 임계값 검증
            if not (0.0 <= template.threshold <= 1.0):
                self.errors.append(
                    f"템플릿 '{template.name}'의 임계값이 유효하지 않습니다: {template.threshold}"
                )

            # 캡쳐 영역 검증
            region = template.capture_region
            if region.width <= 0 or region.height <= 0:
                self.errors.append(
                    f"템플릿 '{template.name}'의 캡쳐 영역이 유효하지 않습니다"
                )

            if region.x < 0 or region.y < 0:
                self.warnings.append(
                    f"템플릿 '{template.name}'의 캡쳐 영역이 음수 좌표를 포함합니다"
                )

    def _validate_macro_sequences(
        self, sequences: List[MacroSequence], templates: List[ImageTemplate]
    ) -> None:
        """매크로 시퀀스 검증"""
        if not sequences:
            self.warnings.append("등록된 매크로 시퀀스가 없습니다")
            return

        sequence_ids = set()
        sequence_names = set()
        template_ids = {t.id for t in templates}

        for sequence in sequences:
            # ID 중복 검증
            if sequence.id in sequence_ids:
                self.errors.append(f"중복된 시퀀스 ID: {sequence.id}")
            sequence_ids.add(sequence.id)

            # 이름 중복 검증
            if sequence.name in sequence_names:
                self.warnings.append(f"중복된 시퀀스 이름: {sequence.name}")
            sequence_names.add(sequence.name)

            # 액션 검증
            if not sequence.actions:
                self.warnings.append(f"시퀀스 '{sequence.name}'에 액션이 없습니다")
                continue

            # 루프 설정 검증
            if sequence.loop_count < 1:
                self.errors.append(
                    f"시퀀스 '{sequence.name}'의 루프 횟수가 유효하지 않습니다"
                )

            if sequence.loop_delay < 0:
                self.errors.append(
                    f"시퀀스 '{sequence.name}'의 루프 지연이 유효하지 않습니다"
                )

            # 개별 액션 검증
            action_ids = set()
            for i, action in enumerate(sequence.actions):
                # 액션 ID 중복 검증
                if action.id in action_ids:
                    self.errors.append(
                        f"시퀀스 '{sequence.name}'에 중복된 액션 ID: {action.id}"
                    )
                action_ids.add(action.id)

                # 이미지 템플릿 참조 검증
                if (
                    action.image_template_id
                    and action.image_template_id not in template_ids
                ):
                    self.errors.append(
                        f"시퀀스 '{sequence.name}' 액션 {i+1}이 존재하지 않는 템플릿을 참조합니다: "
                        f"{action.image_template_id}"
                    )

                # 액션별 세부 검증
                self._validate_action(action, sequence.name, i + 1)

    def _validate_action(self, action, sequence_name: str, action_index: int) -> None:
        """개별 액션 검증"""
        action_prefix = f"시퀀스 '{sequence_name}' 액션 {action_index}"

        # 공통 검증
        if action.match_threshold < 0 or action.match_threshold > 1:
            self.errors.append(f"{action_prefix}의 매칭 임계값이 유효하지 않습니다")

        if action.timeout_seconds <= 0:
            self.errors.append(f"{action_prefix}의 타임아웃이 유효하지 않습니다")

        if action.retry_count < 0:
            self.errors.append(f"{action_prefix}의 재시도 횟수가 유효하지 않습니다")

        # 액션 타입별 검증
        from ..models.macro_models import ActionType

        if action.action_type in [
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
        ]:
            if not action.click_position and not action.image_template_id:
                self.errors.append(
                    f"{action_prefix}에 클릭 위치나 이미지 템플릿이 지정되지 않았습니다"
                )

        elif action.action_type == ActionType.DRAG:
            if not (action.click_position and action.drag_to_position):
                self.errors.append(
                    f"{action_prefix}에 드래그 시작점과 끝점이 모두 지정되지 않았습니다"
                )

        elif action.action_type == ActionType.TYPE_TEXT:
            if not action.text_input:
                self.warnings.append(f"{action_prefix}에 입력할 텍스트가 없습니다")

        elif action.action_type == ActionType.KEY_PRESS:
            if not action.key_combination:
                self.errors.append(f"{action_prefix}에 입력할 키가 지정되지 않았습니다")

        elif action.action_type == ActionType.SCROLL:
            if action.scroll_direction not in ["up", "down", "left", "right"]:
                self.errors.append(f"{action_prefix}의 스크롤 방향이 유효하지 않습니다")

            if action.scroll_amount and action.scroll_amount <= 0:
                self.errors.append(f"{action_prefix}의 스크롤 양이 유효하지 않습니다")

        elif action.action_type == ActionType.WAIT:
            if not action.wait_seconds or action.wait_seconds <= 0:
                self.errors.append(f"{action_prefix}의 대기 시간이 유효하지 않습니다")

        elif action.action_type == ActionType.SEND_TELEGRAM:
            if not action.telegram_message:
                self.warnings.append(
                    f"{action_prefix}에 전송할 텔레그램 메시지가 없습니다"
                )

    def _validate_paths(self, config: MacroConfig) -> None:
        """경로 검증"""
        # 스크린샷 저장 경로
        screenshot_path = Path(config.screenshot_save_path)
        try:
            screenshot_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.errors.append(
                f"스크린샷 저장 경로를 생성할 수 없습니다: {config.screenshot_save_path}, {e}"
            )

    def _is_valid_telegram_token(self, token: str) -> bool:
        """텔레그램 봇 토큰 형식 검증"""
        # 텔레그램 봇 토큰 형식: 숫자:문자열
        pattern = r"^\d{8,10}:[A-Za-z0-9_-]{35}$"
        return bool(re.match(pattern, token))

    def _is_valid_chat_id(self, chat_id: str) -> bool:
        """텔레그램 채팅 ID 형식 검증"""
        # 채팅 ID는 숫자이거나 @로 시작하는 사용자명
        if chat_id.startswith("@"):
            return len(chat_id) > 1 and chat_id[1:].replace("_", "").isalnum()
        else:
            try:
                int(chat_id)
                return True
            except ValueError:
                return False

    def validate_single_template(
        self, template: ImageTemplate
    ) -> Tuple[bool, List[str]]:
        """단일 이미지 템플릿 검증"""
        self.errors.clear()

        # 파일 존재 확인
        if not Path(template.file_path).exists():
            self.errors.append(f"이미지 파일이 존재하지 않습니다: {template.file_path}")

        # 임계값 확인
        if not (0.0 <= template.threshold <= 1.0):
            self.errors.append(f"임계값이 유효하지 않습니다: {template.threshold}")

        # 캡쳐 영역 확인
        region = template.capture_region
        if region.width <= 0 or region.height <= 0:
            self.errors.append("캡쳐 영역의 크기가 유효하지 않습니다")

        return len(self.errors) == 0, self.errors.copy()

    def validate_telegram_settings(
        self, config: TelegramConfig
    ) -> Tuple[bool, List[str]]:
        """텔레그램 설정만 검증"""
        self.errors.clear()

        if config.enabled:
            if not config.bot_token:
                self.errors.append("봇 토큰이 설정되지 않았습니다")
            elif not self._is_valid_telegram_token(config.bot_token):
                self.errors.append("봇 토큰 형식이 올바르지 않습니다")

            if not config.chat_id:
                self.errors.append("채팅 ID가 설정되지 않았습니다")
            elif not self._is_valid_chat_id(config.chat_id):
                self.errors.append("채팅 ID 형식이 올바르지 않습니다")

        return len(self.errors) == 0, self.errors.copy()

    def get_config_summary(self, config: MacroConfig) -> Dict[str, Any]:
        """설정 요약 정보 반환"""
        return {
            "version": config.version,
            "template_count": len(config.image_templates),
            "sequence_count": len(config.macro_sequences),
            "total_actions": sum(len(seq.actions) for seq in config.macro_sequences),
            "telegram_enabled": config.telegram_config.enabled,
            "paths": {"screenshot_save_path": config.screenshot_save_path},
            "settings": {
                "match_confidence_threshold": config.match_confidence_threshold,
                "action_delay": config.action_delay,
                "auto_save_interval": config.auto_save_interval,
            },
        }

