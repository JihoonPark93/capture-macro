"""
크로스 플랫폼 빌드 스크립트
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
from typing import List, Optional
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CrossPlatformBuilder:
    """크로스 플랫폼 빌드 도구"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.build_dir = self.project_root / "dist"
        self.spec_dir = self.project_root / "build_scripts"

        # 현재 플랫폼 정보
        self.current_platform = platform.system().lower()
        self.current_arch = platform.machine().lower()

        logger.info(f"현재 플랫폼: {self.current_platform} ({self.current_arch})")

    def check_dependencies(self) -> bool:
        """빌드 의존성 확인"""
        logger.info("빌드 의존성 확인 중...")

        required_packages = [
            # "pyinstaller",
            "PyQt6",
            "opencv-python",
            "pyautogui",
            "pillow",
            "numpy",
            "requests",
            "psutil",
        ]

        missing = []

        for package in required_packages:
            try:
                if package == "opencv-python":
                    import cv2
                elif package == "pyautogui":
                    import pyautogui
                elif package == "pillow":
                    import PIL
                elif package == "PyQt6":
                    import PyQt6
                else:
                    __import__(package.lower().replace("-", "_"))

                logger.debug(f"✓ {package}")

            except ImportError:
                missing.append(package)
                logger.error(f"✗ {package}")

        if missing:
            logger.error(f"누락된 패키지: {', '.join(missing)}")
            logger.error("다음 명령어로 설치하세요:")
            logger.error(f"uv add {' '.join(missing)}")
            return False

        # PyInstaller 확인
        try:
            result = subprocess.run(
                ["pyinstaller", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info(f"PyInstaller 버전: {result.stdout.strip()}")
            else:
                logger.error("PyInstaller 실행 실패")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.error("PyInstaller가 설치되지 않았습니다")
            return False

        logger.info("모든 의존성이 확인되었습니다")
        return True

    def clean_build_dir(self):
        """빌드 디렉토리 정리"""
        logger.info("이전 빌드 파일 정리 중...")

        # dist 디렉토리 정리
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(parents=True)

        # build 디렉토리 정리
        build_dir = self.project_root / "build"
        if build_dir.exists():
            shutil.rmtree(build_dir)

        # spec 파일 정리
        for spec_file in self.project_root.glob("*.spec"):
            spec_file.unlink()

        logger.info("빌드 디렉토리 정리 완료")

    def create_spec_file(self, target_platform: str, debug: bool = False) -> Path:
        """스펙 파일 생성"""
        logger.info(f"{target_platform} 플랫폼용 스펙 파일 생성 중...")

        # build_spec.py 실행하여 스펙 파일 생성
        build_spec_script = self.spec_dir / "build_spec.py"

        cmd = [
            sys.executable,
            str(build_spec_script),
            "--platform",
            target_platform,
            "--name",
            f"KTX_Macro_V2_{target_platform}",
        ]

        if debug:
            cmd.append("--debug")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"스펙 파일 생성 실패: {result.stderr}")
                return None

            # 생성된 스펙 파일 찾기
            spec_file = self.project_root / f"KTX_Macro_V2_{target_platform}.spec"

            if spec_file.exists():
                logger.info(f"스펙 파일 생성됨: {spec_file}")
                return spec_file
            else:
                logger.error("스펙 파일을 찾을 수 없습니다")
                return None

        except subprocess.TimeoutExpired:
            logger.error("스펙 파일 생성 시간 초과")
            return None
        except Exception as e:
            logger.error(f"스펙 파일 생성 중 오류: {e}")
            return None

    def build_with_pyinstaller(self, spec_file: Path) -> bool:
        """PyInstaller로 빌드"""
        logger.info(f"PyInstaller 빌드 시작: {spec_file.name}")

        cmd = ["pyinstaller", "--clean", str(spec_file)]

        try:
            # 실시간 출력을 위한 설정
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # 실시간 로그 출력
            for line in process.stdout:
                print(line.strip())

            process.wait()

            if process.returncode == 0:
                logger.info("PyInstaller 빌드 성공")
                return True
            else:
                logger.error(f"PyInstaller 빌드 실패 (코드: {process.returncode})")
                return False

        except Exception as e:
            logger.error(f"빌드 중 오류: {e}")
            return False

    def post_build_process(self, target_platform: str):
        """빌드 후 처리"""
        logger.info("빌드 후 처리 중...")

        # 생성된 실행 파일 찾기
        app_name = f"KTX_Macro_V2_{target_platform}"

        if target_platform == "windows":
            exe_name = f"{app_name}.exe"
        elif target_platform == "macos":
            exe_name = f"{app_name}.app"
        else:
            exe_name = app_name

        exe_path = self.build_dir / exe_name

        if exe_path.exists():
            logger.info(f"실행 파일 생성됨: {exe_path}")

            # 파일 크기 출력
            if exe_path.is_file():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                logger.info(f"파일 크기: {size_mb:.1f} MB")

            # README 파일 생성
            readme_content = f"""# KTX Macro V2 - {target_platform.title()} 빌드

## 실행 방법
- {exe_name} 파일을 더블클릭하여 실행하세요

## 시스템 요구사항
- 운영체제: {target_platform.title()}
- 메모리: 4GB 이상 권장
- 디스크 공간: 100MB 이상

## 주요 기능
- 화면 캡쳐 및 이미지 매칭
- 마우스/키보드 자동화
- 매크로 시퀀스 관리
- 텔레그램 알림 연동

## 문제 해결
1. 실행이 안 되는 경우:
   - 바이러스 백신 소프트웨어에서 예외 처리
   - 관리자 권한으로 실행

2. 오류 발생 시:
   - logs 폴더의 로그 파일 확인
   - 설정 파일 초기화

## 지원
- 문제 신고: GitHub Issues
- 문서: README.md

빌드 정보:
- 빌드 시간: {__import__('datetime').datetime.now().isoformat()}
- 타겟 플랫폼: {target_platform}
- 빌드 머신: {platform.system()} {platform.release()}
"""

            readme_path = self.build_dir / "README.txt"
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)

            logger.info(f"README 파일 생성됨: {readme_path}")

        else:
            logger.error(f"실행 파일을 찾을 수 없습니다: {exe_path}")

    def build(
        self, target_platforms: List[str], debug: bool = False, clean: bool = True
    ):
        """메인 빌드 프로세스"""
        logger.info("=" * 60)
        logger.info("KTX Macro V2 크로스 플랫폼 빌드 시작")
        logger.info("=" * 60)

        # 의존성 확인
        if not self.check_dependencies():
            logger.error("의존성 확인 실패")
            return False

        # 빌드 디렉토리 정리
        if clean:
            self.clean_build_dir()

        # 각 플랫폼별 빌드
        success_count = 0

        for platform_name in target_platforms:
            logger.info(f"\n{platform_name} 플랫폼 빌드 시작...")

            try:
                # 스펙 파일 생성
                spec_file = self.create_spec_file(platform_name, debug)
                if not spec_file:
                    logger.error(f"{platform_name} 스펙 파일 생성 실패")
                    continue

                # PyInstaller 빌드
                if self.build_with_pyinstaller(spec_file):
                    # 빌드 후 처리
                    self.post_build_process(platform_name)
                    success_count += 1
                    logger.info(f"✓ {platform_name} 빌드 성공")
                else:
                    logger.error(f"✗ {platform_name} 빌드 실패")

            except Exception as e:
                logger.error(f"{platform_name} 빌드 중 오류: {e}")

        # 결과 요약
        logger.info("\n" + "=" * 60)
        logger.info("빌드 완료")
        logger.info(f"성공: {success_count}/{len(target_platforms)}")

        if success_count > 0:
            logger.info(f"빌드 결과물: {self.build_dir}")

        logger.info("=" * 60)

        return success_count == len(target_platforms)


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="KTX Macro V2 크로스 플랫폼 빌드")
    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=["windows", "macos", "linux"],
        default=["windows"],
        help="빌드할 플랫폼들",
    )
    parser.add_argument("--debug", action="store_true", help="디버그 빌드")
    parser.add_argument(
        "--no-clean", action="store_true", help="빌드 디렉토리 정리 안함"
    )
    parser.add_argument("--project-root", type=Path, help="프로젝트 루트 디렉토리")

    args = parser.parse_args()

    try:
        builder = CrossPlatformBuilder(args.project_root)
        success = builder.build(
            target_platforms=args.platforms, debug=args.debug, clean=not args.no_clean
        )

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("사용자에 의해 빌드가 중단되었습니다")
        sys.exit(1)
    except Exception as e:
        logger.error(f"빌드 스크립트 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
