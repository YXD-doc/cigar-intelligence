#!/bin/bash
# Railway 部署脚本

# 1. 安装 Railway CLI (如果未安装)
if ! command -v railway &> /dev/null; then
    npm install -g @railway/cli
fi

# 2. 设置 Token
export RAILWAY_TOKEN="0801ce18-50ee-40f6-ac41-9a922ff58724"

# 3. 进入项目目录
cd /root/.openclaw/workspace/cigar_search_system

# 4. 关联项目
railway link --project "6b71051e-d5a6-439f-82d5-9fc392954f3d"

# 5. 部署
railway up

echo "部署完成！访问: https://railway.app/project/6b71051e-d5a6-439f-82d5-9fc392954f3d"
