@echo off
REM KTX Macro V2 빌드 스크립트 (Windows)

setlocal enabledelayedexpansion

REM 색상 코드 (Windows 10/11에서 지원)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM 스크립트 디렉토리 설정
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

echo %BLUE%[INFO]%NC% 프로젝트 루트: %PROJECT_ROOT%
cd /d "%PROJECT_ROOT%"

REM Python 가상환경 확인
if defined VIRTUAL_ENV (
    echo %BLUE%[INFO]%NC% 가상환경 활성화됨: %VIRTUAL_ENV%
) else (
    echo %YELLOW%[WARNING]%NC% 가상환경이 활성화되지 않았습니다
    echo %BLUE%[INFO]%NC% UV 환경을 활성화합니다...
    
    REM UV 확인
    where uv >nul 2>nul
    if !errorlevel! neq 0 (
        echo %RED%[ERROR]%NC% UV가 설치되지 않았습니다. 먼저 UV를 설치하세요.
        pause
        exit /b 1
    )
    
    echo %BLUE%[INFO]%NC% UV를 사용하여 종속성을 동기화합니다...
    uv sync
    
    if !errorlevel! neq 0 (
        echo %RED%[ERROR]%NC% UV 동기화 실패
        pause
        exit /b 1
    )
)

REM 파라미터 파싱
set "PLATFORMS="
set "DEBUG_FLAG="
set "CLEAN_FLAG="
set "HELP_FLAG="

:parse_args
if "%~1"=="" goto :args_done
if "%~1"=="--platforms" (
    shift
    :collect_platforms
    if "%~1"=="" goto :args_done
    if "%~1:~0,2%"=="--" goto :parse_args
    set "PLATFORMS=!PLATFORMS! %~1"
    shift
    goto :collect_platforms
)
if "%~1"=="--debug" (
    set "DEBUG_FLAG=--debug"
    shift
    goto :parse_args
)
if "%~1"=="--no-clean" (
    set "CLEAN_FLAG=--no-clean"
    shift
    goto :parse_args
)
if "%~1"=="--help" goto :show_help
if "%~1"=="-h" goto :show_help

echo %RED%[ERROR]%NC% 알 수 없는 옵션: %~1
pause
exit /b 1

:show_help
echo KTX Macro V2 빌드 스크립트
echo.
echo 사용법: %~nx0 [옵션]
echo.
echo 옵션:
echo   --platforms ^<platform1^> ^<platform2^>  빌드할 플랫폼 (windows, macos, linux)
echo   --debug                              디버그 빌드
echo   --no-clean                           빌드 디렉토리 정리 안함
echo   --help, -h                           이 도움말 표시
echo.
echo 예시:
echo   %~nx0 --platforms windows
echo   %~nx0 --platforms windows --debug
pause
exit /b 0

:args_done

REM 기본 플랫폼 설정
if "%PLATFORMS%"=="" (
    set "PLATFORMS=windows"
    echo %BLUE%[INFO]%NC% 기본 플랫폼으로 빌드: windows
)

REM 빌드 시작
echo %BLUE%[INFO]%NC% 빌드 시작...
echo %BLUE%[INFO]%NC% 대상 플랫폼:%PLATFORMS%

REM Python 빌드 스크립트 실행
set "BUILD_CMD=python "%SCRIPT_DIR%build.py" --platforms%PLATFORMS% %DEBUG_FLAG% %CLEAN_FLAG%"

echo %BLUE%[INFO]%NC% 실행 명령어: %BUILD_CMD%

REM UV 환경에서 실행
if defined VIRTUAL_ENV (
    %BUILD_CMD%
) else (
    uv run %BUILD_CMD%
)

set "BUILD_EXIT_CODE=!errorlevel!"

if !BUILD_EXIT_CODE! equ 0 (
    echo %GREEN%[SUCCESS]%NC% 빌드가 성공적으로 완료되었습니다!
    echo %BLUE%[INFO]%NC% 빌드 결과물은 dist\ 디렉토리에서 확인할 수 있습니다.
) else (
    echo %RED%[ERROR]%NC% 빌드가 실패했습니다. (종료 코드: !BUILD_EXIT_CODE!)
    pause
    exit /b !BUILD_EXIT_CODE!
)

pause

