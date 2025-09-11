"""
텔레그램 봇 연동 모듈
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import aiohttp
from datetime import datetime

from ..models.macro_models import TelegramConfig

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TelegramBot:
    """텔레그램 봇 클래스"""

    def __init__(self, config: Optional[TelegramConfig] = None):
        self.config = config or TelegramConfig()
        # self.base_url = "https://api.telegram.org/bot${botToken}/sendmessage?chat_id=${chatId}&text=${msg}"
        self.base_url = "https://api.telegram.org/bot"
        self.session: Optional[aiohttp.ClientSession] = None

        # 메시지 전송 제한 (초당 최대 30개)
        self.rate_limit_delay = 0.034  # 1/30초
        self.last_send_time = 0.0

    def set_config(self, config: TelegramConfig) -> None:
        """텔레그램 설정 업데이트"""
        self.config = config
        logger.debug(f"텔레그램 설정 업데이트: enabled={config.enabled}")

    def is_configured(self) -> bool:
        """텔레그램 설정 확인"""
        return (
            self.config.enabled
            and bool(self.config.bot_token)
            and bool(self.config.chat_id)
        )

    def use_finished_message(self) -> bool:
        """설정 확인"""
        return self.config.use_finished_message

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """세션 확보"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def _make_request(
        self, method: str, params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """텔레그램 API 요청"""
        if not self.config.bot_token:
            logger.error("텔레그램 봇 토큰이 설정되지 않았습니다")
            return None

        url = f"{self.base_url}{self.config.bot_token}/{method}"
        logger.debug(f"텔레그램 요청 URL: {url}")
        logger.debug(f"텔레그램 요청 파라미터: {params}")

        try:
            session = await self._ensure_session()

            # JSON 대신 form data로 전송 (텔레그램 API 표준 방식)
            async with session.post(url, data=params) as response:
                response_text = await response.text()
                logger.debug(f"텔레그램 응답 상태: {response.status}")
                logger.debug(f"텔레그램 응답 내용: {response_text}")

                if response.status == 200:
                    try:
                        result = await response.json()
                        if result.get("ok"):
                            logger.debug(f"텔레그램 API 성공: {result.get('result')}")
                            return result.get("result")
                        else:
                            logger.error(
                                f"텔레그램 API 오류: {result.get('description')}"
                            )
                            return None
                    except Exception as e:
                        logger.error(f"텔레그램 응답 파싱 오류: {e}")
                        return None
                else:
                    logger.error(f"HTTP 오류: {response.status} - {response_text}")
                    return None

        except asyncio.TimeoutError:
            logger.error("텔레그램 API 요청 타임아웃")
            return None
        except Exception as e:
            logger.error(f"텔레그램 API 요청 실패: {e}")
            return None

    async def send_message(
        self, message: str, chat_id: Optional[str] = None, parse_mode: str = "HTML"
    ) -> bool:
        """메시지 전송"""
        if not self.is_configured():
            logger.warning("텔레그램이 설정되지 않아 메시지를 전송하지 않습니다")
            return False

        if not message.strip():
            logger.warning("빈 메시지는 전송하지 않습니다")
            return False

        # Rate limiting
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_send_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)

        target_chat_id = chat_id or self.config.chat_id

        params = {"chat_id": target_chat_id, "text": message, "parse_mode": parse_mode}

        logger.debug(f"텔레그램 메시지 전송: '{message[:100]}...' -> {target_chat_id}")

        result = await self._make_request("sendMessage", params)
        self.last_send_time = asyncio.get_event_loop().time()

        if result:
            logger.debug("텔레그램 메시지 전송 성공")
            return True
        else:
            logger.error("텔레그램 메시지 전송 실패")
            return False

    async def test_connection(self) -> bool:
        """연결 테스트"""
        if not self.is_configured():
            logger.error("텔레그램 설정이 완료되지 않았습니다")
            return False

        # 테스트 메시지 전송
        test_message = f"🤖 KTX Macro 연결 테스트\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        success = await self.send_message(test_message)

        if success:
            logger.info("텔레그램 연결 테스트 성공")
        else:
            logger.error("텔레그램 연결 테스트 실패")

        return success

    async def close(self) -> None:
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("텔레그램 세션 종료됨")

    def __del__(self):
        """소멸자"""
        if hasattr(self, "session") and self.session and not self.session.closed:
            # 비동기 세션이므로 여기서는 경고만 출력
            logger.warning(
                "텔레그램 세션이 적절히 종료되지 않았습니다. close()를 호출하세요."
            )


# 동기 래퍼 클래스
class SyncTelegramBot:
    """동기 텔레그램 봇 래퍼"""

    def __init__(self, config: Optional[TelegramConfig] = None):
        self.async_bot = TelegramBot(config)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """이벤트 루프 가져오기"""
        try:
            # 현재 실행 중인 이벤트 루프 가져오기
            return asyncio.get_running_loop()
        except RuntimeError:
            # 새 이벤트 루프 생성
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            return self._loop

    def _run_async(self, coro):
        """비동기 함수 동기 실행"""
        try:
            loop = self._get_loop()
            if loop.is_running():
                # 이미 실행 중인 루프에서는 태스크 생성
                return asyncio.ensure_future(coro)
            else:
                # 새 루프에서 실행
                return loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"비동기 함수 실행 실패: {e}")
            return None

    def set_config(self, config: TelegramConfig) -> None:
        """설정 업데이트"""
        self.async_bot.set_config(config)

    def is_configured(self) -> bool:
        """설정 확인"""
        return self.async_bot.is_configured()

    def use_finished_message(self) -> bool:
        """설정 확인"""
        return self.async_bot.use_finished_message()

    def send_message(
        self, message: str, chat_id: Optional[str] = None, parse_mode: str = "HTML"
    ) -> bool:
        """메시지 전송 (동기)"""
        try:
            result = self._run_async(
                self.async_bot.send_message(message, chat_id, parse_mode)
            )
            return result if isinstance(result, bool) else False
        except Exception as e:
            logger.error(f"동기 메시지 전송 실패: {e}")
            return False

    def test_connection(self) -> bool:
        """연결 테스트 (동기)"""
        try:
            result = self._run_async(self.async_bot.test_connection())
            return result if isinstance(result, bool) else False
        except Exception as e:
            logger.error(f"동기 연결 테스트 실패: {e}")
            return False

    def close(self) -> None:
        """리소스 정리"""
        try:
            self._run_async(self.async_bot.close())
            if self._loop and not self._loop.is_closed():
                self._loop.close()
        except Exception as e:
            logger.error(f"텔레그램 봇 종료 실패: {e}")
