FROM python:3.12-slim

# 安装系统依赖(KaTeX 和 PDF 生成需要)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    # weasyprint 需要的依赖
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js(用于 KaTeX)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
COPY package.json .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 KaTeX
RUN npm install -g katex

# 复制项目文件
COPY . .

# 创建数据和资源目录
RUN mkdir -p data/raw data/assets

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
