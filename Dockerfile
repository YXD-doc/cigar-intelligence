FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（仅Pillow所需）
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
