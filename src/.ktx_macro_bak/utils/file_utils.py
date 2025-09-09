"""
파일 관리 유틸리티
"""

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime
import hashlib
import mimetypes

logger = logging.getLogger(__name__)


class FileUtils:
    """파일 관리 유틸리티 클래스"""

    @staticmethod
    def ensure_directory(path: str) -> bool:
        """디렉토리 존재 확인 및 생성"""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"디렉토리 생성 실패: {path}, {e}")
            return False

    @staticmethod
    def copy_file(src: str, dst: str, create_dirs: bool = True) -> bool:
        """파일 복사"""
        try:
            src_path = Path(src)
            dst_path = Path(dst)

            if not src_path.exists():
                logger.error(f"원본 파일이 존재하지 않습니다: {src}")
                return False

            if create_dirs:
                dst_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(src_path, dst_path)
            logger.debug(f"파일 복사 완료: {src} -> {dst}")
            return True

        except Exception as e:
            logger.error(f"파일 복사 실패: {src} -> {dst}, {e}")
            return False

    @staticmethod
    def move_file(src: str, dst: str, create_dirs: bool = True) -> bool:
        """파일 이동"""
        try:
            src_path = Path(src)
            dst_path = Path(dst)

            if not src_path.exists():
                logger.error(f"원본 파일이 존재하지 않습니다: {src}")
                return False

            if create_dirs:
                dst_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(src_path), str(dst_path))
            logger.debug(f"파일 이동 완료: {src} -> {dst}")
            return True

        except Exception as e:
            logger.error(f"파일 이동 실패: {src} -> {dst}, {e}")
            return False

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """파일 삭제"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.debug(f"파일 삭제 완료: {file_path}")
                return True
            else:
                logger.warning(f"삭제할 파일이 존재하지 않습니다: {file_path}")
                return False

        except Exception as e:
            logger.error(f"파일 삭제 실패: {file_path}, {e}")
            return False

    @staticmethod
    def get_file_size(file_path: str) -> Optional[int]:
        """파일 크기 반환 (바이트)"""
        try:
            return Path(file_path).stat().st_size
        except Exception as e:
            logger.error(f"파일 크기 확인 실패: {file_path}, {e}")
            return None

    @staticmethod
    def get_file_info(file_path: str) -> Optional[Dict[str, Any]]:
        """파일 정보 반환"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            stat = path.stat()

            return {
                "path": str(path.absolute()),
                "name": path.name,
                "stem": path.stem,
                "suffix": path.suffix,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "mime_type": mimetypes.guess_type(str(path))[0],
            }

        except Exception as e:
            logger.error(f"파일 정보 확인 실패: {file_path}, {e}")
            return None

    @staticmethod
    def list_files(
        directory: str,
        pattern: str = "*",
        recursive: bool = False,
        include_dirs: bool = False,
    ) -> List[str]:
        """디렉토리 내 파일 목록 반환"""
        try:
            path = Path(directory)
            if not path.exists():
                logger.error(f"디렉토리가 존재하지 않습니다: {directory}")
                return []

            if recursive:
                glob_pattern = f"**/{pattern}"
                files = path.rglob(pattern)
            else:
                files = path.glob(pattern)

            result = []
            for file_path in files:
                if file_path.is_file() or (include_dirs and file_path.is_dir()):
                    result.append(str(file_path))

            return sorted(result)

        except Exception as e:
            logger.error(f"파일 목록 조회 실패: {directory}, {e}")
            return []

    @staticmethod
    def get_file_hash(file_path: str, algorithm: str = "md5") -> Optional[str]:
        """파일 해시 계산"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            hash_obj = hashlib.new(algorithm)

            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()

        except Exception as e:
            logger.error(f"파일 해시 계산 실패: {file_path}, {e}")
            return None

    @staticmethod
    def create_backup(
        file_path: str, backup_dir: Optional[str] = None
    ) -> Optional[str]:
        """파일 백업 생성"""
        try:
            src_path = Path(file_path)
            if not src_path.exists():
                logger.error(f"백업할 파일이 존재하지 않습니다: {file_path}")
                return None

            # 백업 디렉토리 설정
            if backup_dir:
                backup_path = Path(backup_dir)
            else:
                backup_path = src_path.parent / "backups"

            backup_path.mkdir(parents=True, exist_ok=True)

            # 백업 파일명 생성 (타임스탬프 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"{src_path.stem}_{timestamp}{src_path.suffix}"

            # 백업 실행
            shutil.copy2(src_path, backup_file)
            logger.debug(f"백업 생성 완료: {file_path} -> {backup_file}")

            return str(backup_file)

        except Exception as e:
            logger.error(f"백업 생성 실패: {file_path}, {e}")
            return None

    @staticmethod
    def cleanup_old_files(
        directory: str, max_age_days: int, pattern: str = "*", dry_run: bool = False
    ) -> Tuple[int, List[str]]:
        """오래된 파일 정리"""
        try:
            path = Path(directory)
            if not path.exists():
                return 0, []

            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
            deleted_files = []
            deleted_count = 0

            for file_path in path.glob(pattern):
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        if not dry_run:
                            file_path.unlink()
                            deleted_count += 1
                        deleted_files.append(str(file_path))

            if not dry_run:
                logger.info(f"오래된 파일 {deleted_count}개 삭제됨: {directory}")
            else:
                logger.info(f"삭제 대상 파일 {len(deleted_files)}개 발견: {directory}")

            return deleted_count, deleted_files

        except Exception as e:
            logger.error(f"파일 정리 실패: {directory}, {e}")
            return 0, []

    @staticmethod
    def get_temp_file(suffix: str = "", prefix: str = "ktx_macro_") -> str:
        """임시 파일 경로 생성"""
        try:
            with tempfile.NamedTemporaryFile(
                suffix=suffix, prefix=prefix, delete=False
            ) as tmp_file:
                return tmp_file.name
        except Exception as e:
            logger.error(f"임시 파일 생성 실패: {e}")
            return ""

    @staticmethod
    def get_temp_dir(prefix: str = "ktx_macro_") -> str:
        """임시 디렉토리 경로 생성"""
        try:
            return tempfile.mkdtemp(prefix=prefix)
        except Exception as e:
            logger.error(f"임시 디렉토리 생성 실패: {e}")
            return ""

    @staticmethod
    def is_image_file(file_path: str) -> bool:
        """이미지 파일 여부 확인"""
        try:
            path = Path(file_path)
            image_extensions = {
                ".jpg",
                ".jpeg",
                ".png",
                ".bmp",
                ".tiff",
                ".tif",
                ".gif",
                ".webp",
            }
            return path.suffix.lower() in image_extensions
        except Exception:
            return False

    @staticmethod
    def get_available_filename(file_path: str) -> str:
        """중복되지 않는 파일명 생성"""
        try:
            path = Path(file_path)
            if not path.exists():
                return file_path

            base = path.stem
            suffix = path.suffix
            parent = path.parent

            counter = 1
            while True:
                new_name = f"{base}_{counter}{suffix}"
                new_path = parent / new_name
                if not new_path.exists():
                    return str(new_path)
                counter += 1

        except Exception as e:
            logger.error(f"사용 가능한 파일명 생성 실패: {file_path}, {e}")
            return file_path

    @staticmethod
    def compress_directory(source_dir: str, output_file: str) -> bool:
        """디렉토리 압축"""
        try:
            shutil.make_archive(Path(output_file).stem, "zip", source_dir)
            logger.debug(f"디렉토리 압축 완료: {source_dir} -> {output_file}")
            return True

        except Exception as e:
            logger.error(f"디렉토리 압축 실패: {source_dir}, {e}")
            return False

    @staticmethod
    def extract_archive(archive_file: str, extract_to: str) -> bool:
        """압축 파일 해제"""
        try:
            shutil.unpack_archive(archive_file, extract_to)
            logger.debug(f"압축 해제 완료: {archive_file} -> {extract_to}")
            return True

        except Exception as e:
            logger.error(f"압축 해제 실패: {archive_file}, {e}")
            return False

