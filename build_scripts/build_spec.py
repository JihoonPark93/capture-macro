"""
PyInstaller 빌드 스펙 파일 생성기
"""

import os
import sys
from pathlib import Path


def create_spec_file(
    app_name: str = "KTX_Macro_V2",
    target_platform: str = "auto",
    debug: bool = False,
    onefile: bool = True
):
    """PyInstaller 스펙 파일 생성"""
    
    # 프로젝트 루트 경로
    project_root = Path(__file__).parent.parent
    src_path = project_root / "src"
    
    # 메인 스크립트 경로
    main_script = src_path / "macro" / "main.py"
    
    # 아이콘 파일 경로 (있는 경우)
    icon_path = project_root / "assets" / "icon.ico"
    icon_arg = f"icon='{icon_path}'" if icon_path.exists() else ""
    
    # 데이터 파일들
    datas = [
        ('config', 'config'),
        ('assets', 'assets'),
    ]
    
    # 히든 임포트 (PyInstaller가 자동으로 찾지 못하는 모듈들)
    hidden_imports = [
        'macro',
        'macro.core',
        'macro.core.image_matcher',
        'macro.core.macro_engine', 
        'macro.core.screen_capture',
        'macro.core.input_controller',
        'macro.core.telegram_bot',
        'macro.models',
        'macro.models.macro_models',
        'macro.ui',
        'macro.ui.main_window',
        'macro.ui.action_editor',
        'macro.ui.capture_dialog',
        'macro.ui.key_capture_dialog',
        'macro.ui.telegram_settings',
        'cv2',
        'numpy',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'pyautogui',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'requests',
        'aiohttp',
        'asyncio',
        'psutil',
        'screeninfo',
        'telegram',
        'telegram.ext',
        'pynput',
        'pynput.keyboard',
        'pynput.mouse',
        'pyperclip',
    ]
    
    # 제외할 모듈들 (크기 최적화)
    excludes = [
        'tkinter',
        'matplotlib',
        'pandas',
        'scipy',
        'jupyter',
        'IPython',
        'pytest',
        'sphinx',
        'docutils',
    ]
    
    # Windows용 빌드 시 추가 설정
    if target_platform == "windows" or sys.platform.startswith("win"):
        hidden_imports.extend([
            'win32com.client',
            'win32api',
            'win32con',
            'win32clipboard',
            'pywintypes',
        ])
    
    # 스펙 파일 내용 생성
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# 프로젝트 경로 설정
project_root = Path("{project_root}")
src_path = project_root / "src"

# 경로를 sys.path에 추가 (맨 앞에 추가하여 우선순위 확보)
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

block_cipher = None

a = Analysis(
    ['{main_script}'],
    pathex=[str(src_path), str(project_root)],
    binaries=[],
    datas={datas},
    hiddenimports={hidden_imports},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={excludes},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

{'exe = EXE(' if onefile else 'coll = COLLECT('}
    pyz,
    a.scripts,
    {'a.binaries,' if onefile else ''}
    {'a.zipfiles,' if onefile else ''}
    {'a.datas,' if onefile else ''}
    {'[],' if not onefile else ''}
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_arg}
)
'''

    # macOS용 BUNDLE 추가 (onefile이 아닐 때만)
    if not onefile and sys.platform == 'darwin':
        spec_content += f'''
app = BUNDLE(
    coll,
    name='{app_name}.app',
    icon=None,
    bundle_identifier=None,
)
'''

    spec_content += ''''''
    
    # 스펙 파일 저장
    spec_file_path = project_root / f"{app_name}.spec"
    
    with open(spec_file_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"스펙 파일 생성됨: {spec_file_path}")
    return spec_file_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PyInstaller 스펙 파일 생성")
    parser.add_argument("--name", default="KTX_Macro_V2", help="앱 이름")
    parser.add_argument("--platform", choices=["auto", "windows", "macos", "linux"], 
                       default="auto", help="타겟 플랫폼")
    parser.add_argument("--debug", action="store_true", help="디버그 모드")
    parser.add_argument("--onedir", action="store_true", help="단일 디렉토리로 빌드")
    
    args = parser.parse_args()
    
    spec_file = create_spec_file(
        app_name=args.name,
        target_platform=args.platform,
        debug=args.debug,
        onefile=not args.onedir
    )
    
    print(f"빌드 명령어:")
    print(f"pyinstaller {spec_file}")

