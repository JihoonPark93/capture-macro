from typing import Callable
from pynput import keyboard


class GlobalHotkeyManager:
    def __init__(self):
        self._hotkeys = {}
        self._listener = None
        self._is_listening = False

    def register_hotkey(
        self, key: str, callback: Callable[[], None], description: str = ""
    ) -> bool:
        """
        글로벌 핫키 등록
        """
        try:
            if key in self._hotkeys:
                print(f"Hotkey '{key}' is already registered")
                return False

            # 콜백 래핑
            def wrapped_callback():
                try:
                    print(f"Global hotkey triggered: {key} ({description})")
                    callback()
                except Exception as e:
                    print(f"Error in hotkey callback for {key}: {e}")

            self._hotkeys[key] = {
                "callback": wrapped_callback,
                "description": description,
            }

            print(f"Registered global hotkey: {key} ({description})")

            # 리스너 실행 중이면 갱신
            if self._is_listening:
                self.stop_listening()
                self.start_listening()

            return True

        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Failed to register hotkey '{key}': {e}")
            return False

    def unregister_hotkey(self, key: str) -> bool:
        """
        글로벌 핫키 해제
        """
        try:
            if key not in self._hotkeys:
                print(f"Hotkey '{key}' is not registered")
                return False

            was_listening = self._is_listening
            if was_listening:
                self.stop_listening()

            del self._hotkeys[key]

            if was_listening:
                self.start_listening()

            print(f"Unregistered global hotkey: {key}")
            return True

        except Exception as e:
            print(f"Failed to unregister hotkey '{key}': {e}")
            return False

    def start_listening(self) -> bool:
        """
        글로벌 핫키 리스너 시작
        """
        try:
            if self._is_listening:
                print("Global hotkey listener is already running")
                return True

            if not self._hotkeys:
                print("No hotkeys registered, cannot start listening")
                return False

            hotkeys = {k: v["callback"] for k, v in self._hotkeys.items()}

            def start_hotkeys(hotkeys_dict):
                def worker():
                    self._listener = keyboard.GlobalHotKeys(hotkeys_dict)
                    self._listener.run()

                import threading

                t = threading.Thread(target=worker, daemon=True)
                t.run()
                return t

            self._listener = start_hotkeys(hotkeys)
            self._is_listening = True

            print(f"Started global hotkey listening with {len(self._hotkeys)} hotkeys")
            return True

        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Failed to start global hotkey listening: {e}")
            return False

    def stop_listening(self):
        """
        글로벌 핫키 리스너 중지
        """
        if self._listener:
            self._listener.stop()
            self._listener = None
            self._is_listening = False
            print("Stopped global hotkey listener")
