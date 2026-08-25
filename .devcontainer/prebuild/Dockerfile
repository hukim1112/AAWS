FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# ── 1. 시스템 패키지 (Yarn GPG 키 만료 우회) ──
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
        xvfb x11vnc fluxbox novnc websockify \
        fonts-nanum fonts-nanum-coding fonts-nanum-extra \
        fontconfig locales \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── 2. 한국어 로케일 & 폰트 캐시 ──
RUN sed -i 's/# ko_KR.UTF-8/ko_KR.UTF-8/' /etc/locale.gen \
    && locale-gen \
    && fc-cache -fv

# ── 3. Python 패키지 설치 ──
COPY install/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# ── 4. Playwright Chromium + 시스템 의존성 ──
RUN python -m playwright install chromium \
    && python -m playwright install-deps chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
