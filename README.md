# Cigar Intelligence System

雪茄智能检索系统 - 深度学习驱动的雪茄识别与筛选平台

## 功能特性

- 🔍 **模糊搜索**：支持品牌、型号、关键词联想
- 📷 **图片识别**：深度学习模型分析雪茄外观特征
- 🎛️ **交叉筛选**：品牌 × 茄衣 × 茄套 × 茄芯 精确匹配
- ⚠️ **智能提醒**：配方模糊产品自动提示
- 📜 **搜索历史**：本地存储，隐私保护

## 技术栈

- **后端**: FastAPI + Python 3.11
- **深度学习**: PyTorch + EfficientNet
- **图像处理**: OpenCV + Pillow
- **模糊匹配**: RapidFuzz
- **部署**: Railway / Docker

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py

# 访问 http://localhost:8000
```

## 部署到 Railway

```bash
# 1. 创建Git仓库
git init
git add .
git commit -m "Initial commit"

# 2. 连接Railway
railway login
railway init

# 3. 部署
railway up
```

## 数据来源

国产雪茄数据库 v3.1 - 182款产品，48款已核实配方

## 隐私说明

- 单机使用，无需账号
- 搜索历史本地存储
- 默认无痕浏览模式
