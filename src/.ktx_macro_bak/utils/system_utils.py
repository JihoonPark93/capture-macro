"""
시스템 관련 유틸리티
"""

import platform
import psutil
import subprocess
import sys
from typing import Dict, Any, List, Optional, Tuple
import logging
from pathlib import Path
import os
import json

logger = logging.getLogger(__name__)


class SystemUtils:
    """시스템 관련 유틸리티 클래스"""

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """시스템 정보 수집"""
        try:
            # 기본 시스템 정보
            system_info = {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "python_executable": sys.executable,
            }

            # CPU 정보
            system_info["cpu"] = {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "max_frequency": psutil.cpu_freq().max if psutil.cpu_freq() else None,
                "current_frequency": (
                    psutil.cpu_freq().current if psutil.cpu_freq() else None
                ),
            }

            # 메모리 정보
            memory = psutil.virtual_memory()
            system_info["memory"] = {
                "total": memory.total,
                "total_gb": round(memory.total / (1024**3), 2),
                "available": memory.available,
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent,
            }

            # 디스크 정보
            disk = psutil.disk_usage("/")
            system_info["disk"] = {
                "total": disk.total,
                "total_gb": round(disk.total / (1024**3), 2),
                "used": disk.used,
                "used_gb": round(disk.used / (1024**3), 2),
                "free": disk.free,
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": round((disk.used / disk.total) * 100, 2),
            }

            return system_info

        except Exception as e:
            logger.error(f"시스템 정보 수집 실패: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_display_info() -> List[Dict[str, Any]]:
        """디스플레이 정보 수집"""
        displays = []

        try:
            if platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType", "-json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    for display in data.get("SPDisplaysDataType", []):
                        displays.append(
                            {
                                "name": display.get("_name", "Unknown"),
                                "resolution": display.get(
                                    "_spdisplays_resolution", "Unknown"
                                ),
                                "vendor": display.get("spdisplays_vendor", "Unknown"),
                                "model": display.get(
                                    "_spdisplays_display_type", "Unknown"
                                ),
                            }
                        )

            elif platform.system() == "Windows":
                # Windows용 구현
                import wmi

                c = wmi.WMI()
                for monitor in c.Win32_DesktopMonitor():
                    displays.append(
                        {
                            "name": monitor.Name or "Unknown",
                            "resolution": (
                                f"{monitor.ScreenWidth}x{monitor.ScreenHeight}"
                                if monitor.ScreenWidth
                                else "Unknown"
                            ),
                            "vendor": monitor.MonitorManufacturer or "Unknown",
                            "model": monitor.MonitorType or "Unknown",
                        }
                    )

            else:
                # Linux용 기본 구현
                displays.append(
                    {
                        "name": "Primary Display",
                        "resolution": "Unknown",
                        "vendor": "Unknown",
                        "model": "Unknown",
                    }
                )

        except Exception as e:
            logger.error(f"디스플레이 정보 수집 실패: {e}")
            displays.append(
                {
                    "name": "Unknown Display",
                    "resolution": "Unknown",
                    "vendor": "Unknown",
                    "model": "Unknown",
                    "error": str(e),
                }
            )

        return displays

    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """필수 종속성 확인"""
        dependencies = {
            "PyQt6": False,
            "opencv-python": False,
            "PyAutoGUI": False,
            "numpy": False,
            "Pillow": False,
            "requests": False,
            "psutil": True,  # 이미 사용중이므로 True
        }

        for package in dependencies:
            if package == "psutil":
                continue

            try:
                __import__(package)
                dependencies[package] = True
            except ImportError:
                try:
                    # 대체 이름으로 시도
                    if package == "opencv-python":
                        __import__("cv2")
                        dependencies[package] = True
                    elif package == "PyAutoGUI":
                        __import__("pyautogui")
                        dependencies[package] = True
                    elif package == "Pillow":
                        __import__("PIL")
                        dependencies[package] = True
                except ImportError:
                    dependencies[package] = False

        return dependencies

    @staticmethod
    def get_process_info() -> Dict[str, Any]:
        """현재 프로세스 정보"""
        try:
            process = psutil.Process()

            return {
                "pid": process.pid,
                "name": process.name(),
                "status": process.status(),
                "cpu_percent": process.cpu_percent(),
                "memory_info": process.memory_info()._asdict(),
                "memory_percent": process.memory_percent(),
                "num_threads": process.num_threads(),
                "create_time": process.create_time(),
                "cwd": process.cwd(),
                "cmdline": process.cmdline(),
            }

        except Exception as e:
            logger.error(f"프로세스 정보 수집 실패: {e}")
            return {"error": str(e)}

    @staticmethod
    def is_admin() -> bool:
        """관리자 권한 확인"""
        try:
            if platform.system() == "Windows":
                import ctypes

                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except Exception:
            return False

    @staticmethod
    def get_environment_variables() -> Dict[str, str]:
        """환경 변수 반환"""
        return dict(os.environ)

    @staticmethod
    def check_internet_connection(timeout: int = 5) -> bool:
        """인터넷 연결 확인"""
        try:
            import requests

            response = requests.get("https://www.google.com", timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def get_network_interfaces() -> List[Dict[str, Any]]:
        """네트워크 인터페이스 정보"""
        interfaces = []

        try:
            for interface, addresses in psutil.net_if_addrs().items():
                interface_info = {"name": interface, "addresses": []}

                for addr in addresses:
                    address_info = {
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast,
                    }
                    interface_info["addresses"].append(address_info)

                interfaces.append(interface_info)

        except Exception as e:
            logger.error(f"네트워크 인터페이스 정보 수집 실패: {e}")

        return interfaces

    @staticmethod
    def run_command(
        command: List[str], timeout: int = 30, capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """시스템 명령 실행"""
        try:
            result = subprocess.run(
                command, capture_output=capture_output, text=True, timeout=timeout
            )

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            logger.error(f"명령 실행 시간 초과: {' '.join(command)}")
            return -1, "", "Timeout"
        except Exception as e:
            logger.error(f"명령 실행 실패: {' '.join(command)}, {e}")
            return -1, "", str(e)

    @staticmethod
    def get_python_packages() -> List[Dict[str, str]]:
        """설치된 Python 패키지 목록"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"패키지 목록 조회 실패: {result.stderr}")
                return []

        except Exception as e:
            logger.error(f"패키지 목록 조회 중 오류: {e}")
            return []

    @staticmethod
    def create_desktop_shortcut(
        name: str,
        target_path: str,
        icon_path: Optional[str] = None,
        description: str = "",
    ) -> bool:
        """바탕화면 바로가기 생성"""
        try:
            if platform.system() == "Windows":
                # Windows 바로가기 생성
                import win32com.client

                desktop = Path.home() / "Desktop"
                shortcut_path = desktop / f"{name}.lnk"

                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(str(shortcut_path))
                shortcut.Targetpath = target_path
                shortcut.WorkingDirectory = str(Path(target_path).parent)
                if icon_path:
                    shortcut.IconLocation = icon_path
                if description:
                    shortcut.Description = description
                shortcut.save()

                return True

            elif platform.system() == "Darwin":  # macOS
                # macOS Alias 생성은 복잡하므로 심볼릭 링크로 대체
                desktop = Path.home() / "Desktop"
                shortcut_path = desktop / name
                shortcut_path.symlink_to(target_path)
                return True

            else:  # Linux
                # .desktop 파일 생성
                desktop = Path.home() / "Desktop"
                desktop_file = desktop / f"{name}.desktop"

                content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Exec={target_path}
Icon={icon_path or ""}
Comment={description}
Terminal=false
"""
                with open(desktop_file, "w") as f:
                    f.write(content)

                # 실행 권한 부여
                desktop_file.chmod(0o755)
                return True

        except Exception as e:
            logger.error(f"바탕화면 바로가기 생성 실패: {e}")
            return False

    @staticmethod
    def open_file_explorer(path: str) -> bool:
        """파일 탐색기에서 경로 열기"""
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path])
            else:  # Linux
                subprocess.run(["xdg-open", path])

            return True

        except Exception as e:
            logger.error(f"파일 탐색기 열기 실패: {path}, {e}")
            return False

    @staticmethod
    def get_screen_resolution() -> Tuple[int, int]:
        """화면 해상도 가져오기"""
        try:
            import pyautogui

            return pyautogui.size()
        except Exception as e:
            logger.error(f"화면 해상도 확인 실패: {e}")
            return (1920, 1080)  # 기본값

    @staticmethod
    def set_process_priority(priority: str = "normal") -> bool:
        """프로세스 우선순위 설정"""
        try:
            process = psutil.Process()

            priority_map = {
                "low": (
                    psutil.BELOW_NORMAL_PRIORITY_CLASS
                    if platform.system() == "Windows"
                    else 10
                ),
                "normal": (
                    psutil.NORMAL_PRIORITY_CLASS
                    if platform.system() == "Windows"
                    else 0
                ),
                "high": (
                    psutil.ABOVE_NORMAL_PRIORITY_CLASS
                    if platform.system() == "Windows"
                    else -10
                ),
            }

            if priority in priority_map:
                if platform.system() == "Windows":
                    process.nice(priority_map[priority])
                else:
                    os.nice(priority_map[priority])

                logger.debug(f"프로세스 우선순위 설정: {priority}")
                return True
            else:
                logger.error(f"유효하지 않은 우선순위: {priority}")
                return False

        except Exception as e:
            logger.error(f"프로세스 우선순위 설정 실패: {e}")
            return False

    @staticmethod
    def cleanup_temp_files(max_age_hours: int = 24) -> int:
        """임시 파일 정리"""
        try:
            import tempfile
            import time

            temp_dir = Path(tempfile.gettempdir())
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)

            deleted_count = 0

            for file_path in temp_dir.glob("ktx_macro_*"):
                try:
                    if file_path.stat().st_mtime < cutoff_time:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            import shutil

                            shutil.rmtree(file_path)
                        deleted_count += 1
                except Exception:
                    continue

            logger.debug(f"임시 파일 {deleted_count}개 정리됨")
            return deleted_count

        except Exception as e:
            logger.error(f"임시 파일 정리 실패: {e}")
            return 0

