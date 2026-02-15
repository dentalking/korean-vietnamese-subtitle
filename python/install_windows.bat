@echo off
echo ==========================================
echo   자막 오버레이 설치 스크립트
echo ==========================================
echo.

REM Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python을 설치해주세요.
    echo 설치 시 "Add Python to PATH" 체크를 꼭 해주세요!
    pause
    exit /b 1
)

echo [1/3] pip 업그레이드 중...
python -m pip install --upgrade pip

echo.
echo [2/3] PyAudio 설치 중...
pip install PyAudio

if errorlevel 1 (
    echo.
    echo [참고] PyAudio 설치 실패 시, 아래 명령어로 수동 설치:
    echo   pip install pipwin
    echo   pipwin install pyaudio
    echo.
    pip install pipwin
    pipwin install pyaudio
)

echo.
echo [3/3] 나머지 패키지 설치 중...
pip install SpeechRecognition deep-translator

echo.
echo ==========================================
echo   설치 완료! 아래 명령어로 실행하세요:
echo   python app.py
echo ==========================================
pause
