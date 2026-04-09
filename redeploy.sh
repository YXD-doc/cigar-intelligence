#!/bin/bash
# Railway 重新部署脚本

echo "===== Railway 部署指南 ====="
echo ""
echo "由于 API 限制，请手动执行以下步骤："
echo ""
echo "1. 访问 Railway 创建页面:"
echo "   https://railway.app/new"
echo ""
echo "2. 选择 'Deploy from GitHub repo'"
echo ""
echo "3. 选择仓库: YXD-doc/cigar-intelligence"
echo ""
echo "4. 点击 Deploy，等待完成"
echo ""
echo "5. 部署完成后，在 Settings -> Domains 中查看域名"
echo ""
echo "===== 当前代码状态 ====="
cd /root/.openclaw/workspace/cigar_search_system
git log --oneline -3
echo ""
echo "GitHub仓库: https://github.com/YXD-doc/cigar-intelligence"
