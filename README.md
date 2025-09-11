# KTX Macro V2

**이미지 매칭 기반 매크로 자동화 도구**

KTX Macro V2는 화면의 이미지를 인식하여 마우스와 키보드 동작을 자동화하는 강력한 도구입니다. 직관적인 GUI와 함께 복잡한 매크로 시퀀스를 쉽게 생성하고 관리할 수 있습니다.

## 🌟 주요 기능

### 📸 화면 캡쳐 및 이미지 매칭

- 드래그로 간편한 화면 영역 캡쳐
- OpenCV 기반 고정밀 이미지 매칭
- 다중 모니터 환경 지원
- 신뢰도 임계값 조정 가능

### 🖱️ 마우스/키보드 자동화

- 클릭, 더블클릭, 우클릭, 드래그
- 텍스트 입력 및 키 조합 입력
- 스크롤 및 대기 기능
- 크로스 플랫폼 호환성

### 📋 매크로 시퀀스 관리

- 직관적인 드래그 앤 드롭 인터페이스
- 액션 순서 변경 및 활성/비활성 설정
- 루프 및 조건부 실행
- JSON 기반 설정 저장/불러오기

### 📱 텔레그램 연동

- 매크로 실행 결과 알림
- 오류 발생 시 즉시 알림
- 원격 모니터링 가능

### 🎨 사용자 친화적 GUI

- PyQt6 기반 모던 인터페이스
- 실시간 로그 및 진행률 표시
- 다국어 지원 (한국어)

## 🚀 빠른 시작

### 요구사항

- **운영체제**: Windows 10+, macOS 10.15+, Ubuntu 20.04+
- **Python**: 3.9 이상 (소스 코드 실행 시)
- **메모리**: 4GB 이상 권장
- **디스크**: 100MB 이상 여유 공간

### 설치 방법

#### 1. 실행 파일 다운로드 (권장)

[Releases](https://github.com/your-repo/ktx-macro-v2/releases) 페이지에서 해당 플랫폼용 실행 파일을 다운로드하세요.

- **Windows**: `KTX_Macro_V2_windows.exe`
- **macOS**: `KTX_Macro_V2_macos.dmg`
- **Linux**: `KTX_Macro_V2_linux`

#### 2. 소스 코드에서 실행

```bash
# 저장소 클론
git clone https://github.com/your-repo/ktx-macro-v2.git
cd ktx-macro-v2

# UV 패키지 매니저 설치 (권장)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync

# 애플리케이션 실행
uv run python -m ktx_macro.main
```

### 첫 실행 가이드

1. **애플리케이션 시작**

   - 실행 파일을 더블클릭하거나 터미널에서 실행

2. **이미지 템플릿 생성**

   - "화면 캡쳐" 버튼 클릭
   - 원하는 화면 영역을 마우스로 드래그
   - 템플릿 이름과 설정 입력

3. **매크로 시퀀스 생성**

   - "새 시퀀스" 버튼 클릭
   - 액션들을 순서대로 추가
   - 시퀀스 저장

4. **매크로 실행**
   - 생성한 시퀀스 선택
   - "실행" 버튼 클릭

## 📖 사용법

### 이미지 템플릿 등록

1. **캡쳐 시작**: 메인 화면에서 "화면 캡쳐" 버튼 클릭
2. **영역 선택**: 화면이 어두워지면 마우스로 원하는 영역 드래그
3. **설정 입력**: 템플릿 이름과 매칭 신뢰도 설정
4. **저장 완료**: 템플릿이 자동으로 저장됨

### 매크로 시퀀스 편집

1. **새 시퀀스**: "새 시퀀스" 버튼으로 시퀀스 생성
2. **액션 추가**: 다양한 액션 타입 선택하여 추가
   - 이미지 찾기
   - 마우스 클릭 (클릭/더블클릭/우클릭)
   - 텍스트 입력
   - 키보드 입력
   - 대기
   - 텔레그램 전송
3. **순서 조정**: 드래그 앤 드롭으로 액션 순서 변경
4. **설정 조정**: 루프 횟수, 지연 시간 등 설정

### 텔레그램 알림 설정

1. **봇 생성**: 텔레그램에서 @BotFather에게 `/newbot` 명령어 전송
2. **토큰 복사**: 생성된 봇 토큰 복사
3. **채팅 ID 확인**: 봇과 대화 시작 후 채팅 ID 확인
4. **설정 입력**: 애플리케이션에서 "텔레그램 설정" 메뉴 선택
5. **연결 테스트**: "연결 테스트" 버튼으로 설정 확인

## 🛠️ 개발

### 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-repo/ktx-macro-v2.git
cd ktx-macro-v2

# UV 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 개발 의존성 설치
uv sync --dev

# 개발 서버 실행
uv run python -m ktx_macro.main
```

### 빌드

#### 모든 플랫폼 빌드

```bash
# Unix/Linux/macOS
./build_scripts/build.sh --platforms windows macos linux

# Windows
build_scripts\build.bat --platforms windows
```

#### 특정 플랫폼 빌드

```bash
# Windows용만 빌드
uv run python build_scripts/build.py --platforms windows

# 디버그 빌드
uv run python build_scripts/build.py --platforms windows --debug
```

### 코드 품질

```bash
# 코드 포맷팅
uv run black src/
uv run isort src/

# 린팅
uv run flake8 src/

# 타입 체킹
uv run mypy src/

# 테스트 실행
uv run pytest tests/ -v --cov=src/
```

## 📁 프로젝트 구조

```
ktx-macro-v2/
├── src/ktx_macro/           # 메인 소스 코드
│   ├── core/               # 핵심 엔진
│   │   ├── image_matcher.py    # 이미지 매칭
│   │   ├── screen_capture.py   # 화면 캡쳐
│   │   ├── input_controller.py # 입력 제어
│   │   ├── telegram_bot.py     # 텔레그램 연동
│   │   └── macro_engine.py     # 매크로 엔진
│   ├── models/             # 데이터 모델
│   │   └── macro_models.py     # 매크로 데이터 구조
│   ├── ui/                # GUI 인터페이스
│   │   ├── main_window.py      # 메인 윈도우
│   │   ├── capture_dialog.py   # 캡쳐 다이얼로그
│   │   ├── sequence_editor.py  # 시퀀스 편집기
│   │   └── settings_dialog.py  # 설정 다이얼로그
│   ├── utils/             # 유틸리티
│   │   ├── logger.py          # 로깅 시스템
│   │   ├── config_validator.py # 설정 검증
│   │   └── system_utils.py     # 시스템 유틸리티
│   └── main.py            # 애플리케이션 진입점
├── build_scripts/          # 빌드 스크립트
├── tests/                  # 테스트 코드
├── assets/                 # 리소스 파일
├── config/                 # 설정 파일
└── logs/                   # 로그 파일
```

## 🔧 설정

### 설정 파일 위치

- **Windows**: `%APPDATA%/ktx_macro/config.json`
- **macOS**: `~/Library/Application Support/ktx_macro/config.json`
- **Linux**: `~/.config/ktx_macro/config.json`

### 주요 설정 항목

```json
{
  "version": "0.1.0",
  "screenshot_save_path": "assets/screenshots",
  "auto_save_interval": 30,
  "match_confidence_threshold": 0.8,
  "telegram_config": {
    "enabled": false,
    "bot_token": "",
    "chat_id": ""
  }
}
```

## 🐛 문제 해결

### 일반적인 문제

#### 1. 실행 파일이 실행되지 않음

- **Windows**: 바이러스 백신 예외 처리, 관리자 권한으로 실행
- **macOS**: 시스템 환경설정 > 보안 및 개인정보보호에서 허용
- **Linux**: 실행 권한 부여 (`chmod +x KTX_Macro_V2_linux`)

#### 2. 이미지 매칭이 정확하지 않음

- 캡쳐 영역을 더 구체적으로 설정
- 매칭 신뢰도 임계값 조정 (0.7~0.9 권장)
- 화면 해상도나 스케일링 확인

#### 3. 텔레그램 알림이 작동하지 않음

- 봇 토큰과 채팅 ID 확인
- 네트워크 연결 상태 확인
- 방화벽 설정 확인

### 로그 확인

로그 파일 위치:

- **애플리케이션 실행 로그**: `logs/ktx_macro.log`
- **오류 로그**: `logs/ktx_macro_error.log`
- **디버그 로그**: `logs/ktx_macro_debug.log`

## 🤝 기여하기

프로젝트에 기여해주셔서 감사합니다!

### 기여 방법

1. **이슈 리포트**: 버그나 기능 요청은 [GitHub Issues](https://github.com/your-repo/ktx-macro-v2/issues)에 등록
2. **풀 리퀘스트**:
   - Fork 후 feature 브랜치 생성
   - 코드 작성 및 테스트
   - Pull Request 생성

### 개발 가이드라인

- 코드 스타일: Black, isort, flake8 준수
- 타입 힌트 사용 (mypy 통과)
- 테스트 코드 작성
- 커밋 메시지: Conventional Commits 형식

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 라이브러리들을 사용합니다:

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI 프레임워크
- [OpenCV](https://opencv.org/) - 컴퓨터 비전 라이브러리
- [PyAutoGUI](https://pyautogui.readthedocs.io/) - 자동화 라이브러리
- [python-telegram-bot](https://python-telegram-bot.org/) - 텔레그램 API
- [UV](https://astral.sh/uv/) - Python 패키지 매니저

## 📞 지원

- **문서**: [Wiki](https://github.com/your-repo/ktx-macro-v2/wiki)
- **이슈 리포트**: [GitHub Issues](https://github.com/your-repo/ktx-macro-v2/issues)
- **토론**: [GitHub Discussions](https://github.com/your-repo/ktx-macro-v2/discussions)

---

**KTX Macro V2** - 이미지 매칭의 힘으로 더 스마트한 자동화를 경험하세요! 🚀

