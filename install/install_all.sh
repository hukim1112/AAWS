#!/bin/bash

# 스크립트가 위치한 디렉토리로 이동하여 경로 문제를 방지합니다.
cd "$(dirname "$0")"

echo "🚀 Github Codespaces 환경 전체 설치를 시작합니다..."

# 1. 시스템 패키지 업데이트 (선택 사항이지만 권장)
echo "🔄 시스템 패키지 목록 업데이트..."
sudo apt-get update

# 2. noVNC 및 관련 패키지 설치
echo "📦 noVNC 디스플레이 환경 설치 중..."
bash install_novnc.sh

# 3. 브라우저 한글 깨짐 방지 폰트 설치
echo "📦 한글 폰트 설치 중..."
bash install_hangul.sh

# 4. Python 의존성 설치 (requirements.txt가 있을 경우)
if [ -f "requirements.txt" ]; then
    echo "🐍 Python 패키지 설치 중..."
    pip install -r requirements.txt
    
    echo "🌐 Playwright Chromium 브라우저 설치 중..."
    playwright install chromium
else
    echo "⚠️ requirements.txt 파일을 찾을 수 없어 Python 패키지 설치를 건너뜁니다."
fi

# 5. 실행 권한 부여
echo "🔐 스크립트 실행 권한 부여 중..."
chmod +x install_novnc.sh
chmod +x install_hangul.sh
chmod +x ../start_vnc.sh

# 6. Codespaces의 권한 관련 메시지 추가 (선택)
echo "---------------------------------------------------------"
echo "✅ 전체 설치 및 디스플레이 권한 설정이 성공적으로 완료되었습니다!"
echo "💡 이제 ../start_vnc.sh 명령어로 VNC 서버를 실행하실 수 있습니다."
echo "---------------------------------------------------------"
