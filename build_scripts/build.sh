#!/bin/bash

# KTX Macro V2 빌드 스크립트 (Unix/Linux/macOS)

set -e  # 오류 시 스크립트 종료

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 스크립트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_info "프로젝트 루트: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Python 가상환경 확인
if [[ -n "$VIRTUAL_ENV" ]]; then
    print_info "가상환경 활성화됨: $VIRTUAL_ENV"
else
    print_warning "가상환경이 활성화되지 않았습니다"
    print_info "UV 환경을 활성화합니다..."
    
    # UV 환경 활성화 시도
    if command -v uv &> /dev/null; then
        print_info "UV를 사용하여 종속성을 동기화합니다..."
        uv sync
        
        # UV shell 활성화
        print_info "UV shell을 활성화합니다..."
        exec uv run python "$SCRIPT_DIR/build.py" "$@"
    else
        print_error "UV가 설치되지 않았습니다. 먼저 UV를 설치하세요."
        exit 1
    fi
fi

# 파라미터 파싱
PLATFORMS=""
DEBUG_FLAG=""
CLEAN_FLAG=""
HELP_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --platforms)
            shift
            while [[ $# -gt 0 ]] && [[ $1 != --* ]]; do
                PLATFORMS="$PLATFORMS $1"
                shift
            done
            ;;
        --debug)
            DEBUG_FLAG="--debug"
            shift
            ;;
        --no-clean)
            CLEAN_FLAG="--no-clean"
            shift
            ;;
        --help|-h)
            HELP_FLAG="--help"
            shift
            ;;
        *)
            print_error "알 수 없는 옵션: $1"
            exit 1
            ;;
    esac
done

# 도움말 표시
if [[ -n "$HELP_FLAG" ]]; then
    echo "KTX Macro V2 빌드 스크립트"
    echo ""
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --platforms <platform1> <platform2>  빌드할 플랫폼 (windows, macos, linux)"
    echo "  --debug                              디버그 빌드"
    echo "  --no-clean                           빌드 디렉토리 정리 안함"
    echo "  --help, -h                           이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 --platforms windows macos"
    echo "  $0 --platforms windows --debug"
    exit 0
fi

# 기본 플랫폼 설정
if [[ -z "$PLATFORMS" ]]; then
    PLATFORMS="windows"
    print_info "기본 플랫폼으로 빌드: windows"
fi

# 빌드 시작
print_info "빌드 시작..."
print_info "대상 플랫폼: $PLATFORMS"

# Python 빌드 스크립트 실행
BUILD_CMD="python $SCRIPT_DIR/build.py --platforms $PLATFORMS $DEBUG_FLAG $CLEAN_FLAG"

print_info "실행 명령어: $BUILD_CMD"
eval $BUILD_CMD

BUILD_EXIT_CODE=$?

if [[ $BUILD_EXIT_CODE -eq 0 ]]; then
    print_success "빌드가 성공적으로 완료되었습니다!"
    print_info "빌드 결과물은 dist/ 디렉토리에서 확인할 수 있습니다."
else
    print_error "빌드가 실패했습니다. (종료 코드: $BUILD_EXIT_CODE)"
    exit $BUILD_EXIT_CODE
fi

