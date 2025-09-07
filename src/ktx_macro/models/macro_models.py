"""
매크로 관련 데이터 모델 정의
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


class ActionType(Enum):
    """매크로 액션 타입"""

    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    TYPE_TEXT = "type_text"
    KEY_PRESS = "key_press"
    SCROLL = "scroll"
    WAIT = "wait"
    SEND_TELEGRAM = "send_telegram"


@dataclass
class CaptureRegion:
    """캡쳐 영역 정보"""

    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "CaptureRegion":
        return cls(**data)


@dataclass
class ImageTemplate:
    """이미지 템플릿 정보"""

    id: str
    name: str
    file_path: str
    capture_region: CaptureRegion
    threshold: float = 0.7
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "file_path": self.file_path,
            "capture_region": self.capture_region.to_dict(),
            "threshold": self.threshold,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageTemplate":
        return cls(
            id=data["id"],
            name=data["name"],
            file_path=data["file_path"],
            capture_region=CaptureRegion.from_dict(data["capture_region"]),
            threshold=data.get("threshold", 0.8),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            ),
        )


@dataclass
class MacroAction:
    """매크로 액션 정보"""

    id: str
    action_type: ActionType
    enabled: bool = True
    description: Optional[str] = None

    # 이미지 관련
    image_template_id: Optional[str] = None

    # 마우스 관련
    click_position: Optional[Tuple[int, int]] = None
    drag_to_position: Optional[Tuple[int, int]] = None

    # 키보드 관련
    text_input: Optional[str] = None
    key_combination: Optional[List[str]] = None

    # 스크롤 관련
    scroll_direction: Optional[str] = None  # "up", "down", "left", "right"
    scroll_amount: Optional[int] = None

    # 대기 관련
    wait_seconds: Optional[float] = None

    # 텔레그램 관련
    telegram_message: Optional[str] = None

    # 매칭 관련 설정
    match_threshold: float = 0.7
    timeout_seconds: float = 10.0
    retry_count: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "enabled": self.enabled,
            "description": self.description,
            "image_template_id": self.image_template_id,
            "click_position": self.click_position,
            "drag_to_position": self.drag_to_position,
            "text_input": self.text_input,
            "key_combination": self.key_combination,
            "scroll_direction": self.scroll_direction,
            "scroll_amount": self.scroll_amount,
            "wait_seconds": self.wait_seconds,
            "telegram_message": self.telegram_message,
            "match_threshold": self.match_threshold,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MacroAction":
        return cls(
            id=data["id"],
            action_type=ActionType(data["action_type"]),
            enabled=data.get("enabled", True),
            description=data.get("description"),
            image_template_id=data.get("image_template_id"),
            click_position=(
                tuple(data["click_position"]) if data.get("click_position") else None
            ),
            drag_to_position=(
                tuple(data["drag_to_position"])
                if data.get("drag_to_position")
                else None
            ),
            text_input=data.get("text_input"),
            key_combination=data.get("key_combination"),
            scroll_direction=data.get("scroll_direction"),
            scroll_amount=data.get("scroll_amount"),
            wait_seconds=data.get("wait_seconds"),
            telegram_message=data.get("telegram_message"),
            match_threshold=data.get("match_threshold", 0.7),
            timeout_seconds=data.get("timeout_seconds", 10.0),
            retry_count=data.get("retry_count", 3),
        )


@dataclass
class MacroSequence:
    """매크로 시퀀스 정보"""

    id: str
    name: str
    description: str = ""
    actions: List[MacroAction] = field(default_factory=list)
    enabled: bool = True
    loop_count: int = 1
    loop_delay: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    def add_action(self, action: MacroAction) -> None:
        """액션 추가"""
        self.actions.append(action)
        self.modified_at = datetime.now()

    def remove_action(self, action_id: str) -> bool:
        """액션 제거"""
        for i, action in enumerate(self.actions):
            if action.id == action_id:
                del self.actions[i]
                self.modified_at = datetime.now()
                return True
        return False

    def move_action(self, action_id: str, new_index: int) -> bool:
        """액션 순서 변경"""
        action_index = None
        for i, action in enumerate(self.actions):
            if action.id == action_id:
                action_index = i
                break

        if action_index is None or new_index < 0 or new_index >= len(self.actions):
            return False

        action = self.actions.pop(action_index)
        self.actions.insert(new_index, action)
        self.modified_at = datetime.now()
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "actions": [action.to_dict() for action in self.actions],
            "enabled": self.enabled,
            "loop_count": self.loop_count,
            "loop_delay": self.loop_delay,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MacroSequence":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            actions=[
                MacroAction.from_dict(action_data)
                for action_data in data.get("actions", [])
            ],
            enabled=data.get("enabled", True),
            loop_count=data.get("loop_count", 1),
            loop_delay=data.get("loop_delay", 1.0),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            ),
            modified_at=datetime.fromisoformat(
                data.get("modified_at", datetime.now().isoformat())
            ),
        )


@dataclass
class TelegramConfig:
    """텔레그램 설정"""

    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bot_token": self.bot_token,
            "chat_id": self.chat_id,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelegramConfig":
        return cls(
            bot_token=data.get("bot_token", ""),
            chat_id=data.get("chat_id", ""),
            enabled=data.get("enabled", False),
        )


@dataclass
class MacroConfig:
    """전체 매크로 설정"""

    version: str = "0.1.0"
    image_templates: List[ImageTemplate] = field(default_factory=list)
    macro_sequences: List[MacroSequence] = field(default_factory=list)
    telegram_config: TelegramConfig = field(default_factory=TelegramConfig)

    # 일반 설정
    screenshot_save_path: str = "assets/screenshots"
    auto_save_interval: int = 30  # seconds
    match_confidence_threshold: float = 0.7
    action_delay: float = 0.5  # seconds between actions

    def add_image_template(self, template: ImageTemplate) -> None:
        """이미지 템플릿 추가"""
        self.image_templates.append(template)

    def remove_image_template(self, template_id: str) -> bool:
        """이미지 템플릿 제거"""
        for i, template in enumerate(self.image_templates):
            if template.id == template_id:
                del self.image_templates[i]
                return True
        return False

    def get_image_template(self, template_id: str) -> Optional[ImageTemplate]:
        """이미지 템플릿 조회"""
        for template in self.image_templates:
            if template.id == template_id:
                return template
        return None

    def add_macro_sequence(self, sequence: MacroSequence) -> None:
        """매크로 시퀀스 추가"""
        self.macro_sequences.append(sequence)

    def remove_macro_sequence(self, sequence_id: str) -> bool:
        """매크로 시퀀스 제거"""
        for i, sequence in enumerate(self.macro_sequences):
            if sequence.id == sequence_id:
                del self.macro_sequences[i]
                return True
        return False

    def get_macro_sequence(self, sequence_id: str) -> Optional[MacroSequence]:
        """매크로 시퀀스 조회"""
        for sequence in self.macro_sequences:
            if sequence.id == sequence_id:
                return sequence
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "image_templates": [
                template.to_dict() for template in self.image_templates
            ],
            "macro_sequences": [
                sequence.to_dict() for sequence in self.macro_sequences
            ],
            "telegram_config": self.telegram_config.to_dict(),
            "screenshot_save_path": self.screenshot_save_path,
            "auto_save_interval": self.auto_save_interval,
            "match_confidence_threshold": self.match_confidence_threshold,
            "action_delay": self.action_delay,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MacroConfig":
        return cls(
            version=data.get("version", "0.1.0"),
            image_templates=[
                ImageTemplate.from_dict(t) for t in data.get("image_templates", [])
            ],
            macro_sequences=[
                MacroSequence.from_dict(s) for s in data.get("macro_sequences", [])
            ],
            telegram_config=TelegramConfig.from_dict(data.get("telegram_config", {})),
            screenshot_save_path=data.get("screenshot_save_path", "assets/screenshots"),
            auto_save_interval=data.get("auto_save_interval", 30),
            match_confidence_threshold=data.get("match_confidence_threshold", 0.7),
            action_delay=data.get("action_delay", 0.5),
        )

    def save_to_file(self, file_path: str) -> None:
        """파일로 저장"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: str) -> "MacroConfig":
        """파일에서 불러오기"""
        if not Path(file_path).exists():
            return cls()

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.from_dict(data)
