#!/bin/bash
# Dockerfile prebuild 방식에서 사용하는 경량 post-create 스크립트
# (시스템 패키지, pip, Playwright는 이미 이미지에 포함됨)

cd "$(dirname "$0")"

# 실행 권한 부여
chmod +x install_novnc.sh 2>/dev/null
chmod +x install_hangul.sh 2>/dev/null
chmod +x ../start_vnc.sh 2>/dev/null

# .env 파일 생성
if [ ! -f "../.env" ]; then
    cp ../.env.example ../.env
    echo "📄 .env 파일이 생성되었습니다. API 키를 설정해 주세요."
else
    echo "📄 .env 파일이 이미 존재합니다."
fi

echo "✅ 환경 준비 완료! (Prebuild 이미지 사용)"
