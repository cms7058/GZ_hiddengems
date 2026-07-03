FROM python:3.11-slim

ARG DEBIAN_MIRROR=https://mirrors.cloud.tencent.com/debian
ARG DEBIAN_SECURITY_MIRROR=https://mirrors.cloud.tencent.com/debian-security
ARG PIP_INDEX_URL=https://mirrors.cloud.tencent.com/pypi/simple
ARG PIP_TRUSTED_HOST=mirrors.cloud.tencent.com

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g; s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g; s|http://security.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -i "${PIP_INDEX_URL}" --trusted-host "${PIP_TRUSTED_HOST}" -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
