#!/bin/bash

# FuXi SageMaker Deploy - GitHub 仓库设置脚本
# 使用方法: ./setup_github.sh YOUR_GITHUB_USERNAME

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 FuXi SageMaker Deploy - GitHub 仓库设置${NC}"
echo -e "${BLUE}===========================================${NC}"

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ 错误: 请提供 GitHub 用户名${NC}"
    echo -e "${YELLOW}使用方法: ./setup_github.sh YOUR_GITHUB_USERNAME${NC}"
    exit 1
fi

GITHUB_USERNAME=$1
REPO_NAME="fuxi_sagemaker_deploy"

echo -e "${YELLOW}📋 配置信息:${NC}"
echo -e "  GitHub 用户名: ${GITHUB_USERNAME}"
echo -e "  仓库名称: ${REPO_NAME}"
echo ""

# 检查是否已经是 git 仓库
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ 错误: 当前目录不是 git 仓库${NC}"
    echo -e "${YELLOW}请先运行: git init${NC}"
    exit 1
fi

# 检查是否有提交
if ! git log --oneline -n 1 > /dev/null 2>&1; then
    echo -e "${RED}❌ 错误: 没有找到 git 提交${NC}"
    echo -e "${YELLOW}请先运行: git add . && git commit -m 'Initial commit'${NC}"
    exit 1
fi

# 添加远程仓库
echo -e "${YELLOW}🔗 添加远程仓库...${NC}"
if git remote get-url origin > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  远程仓库已存在，移除旧的配置...${NC}"
    git remote remove origin
fi

git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
echo -e "${GREEN}✅ 远程仓库添加成功${NC}"

# 设置主分支
echo -e "${YELLOW}🌿 设置主分支...${NC}"
git branch -M main

# 推送到 GitHub
echo -e "${YELLOW}📤 推送到 GitHub...${NC}"
echo -e "${BLUE}注意: 如果这是第一次推送，可能需要输入 GitHub 凭据${NC}"

if git push -u origin main; then
    echo -e "${GREEN}✅ 推送成功!${NC}"
    echo ""
    echo -e "${GREEN}🎉 仓库设置完成!${NC}"
    echo -e "${BLUE}📍 仓库地址: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}${NC}"
    echo ""
    echo -e "${YELLOW}📋 后续操作:${NC}"
    echo -e "  1. 访问仓库地址查看代码"
    echo -e "  2. 设置仓库描述和标签"
    echo -e "  3. 配置 GitHub Pages (如果需要)"
    echo -e "  4. 设置分支保护规则 (如果需要)"
else
    echo -e "${RED}❌ 推送失败${NC}"
    echo -e "${YELLOW}💡 可能的解决方案:${NC}"
    echo -e "  1. 检查 GitHub 用户名是否正确"
    echo -e "  2. 确保已在 GitHub 创建了 ${REPO_NAME} 仓库"
    echo -e "  3. 检查 GitHub 访问权限"
    echo -e "  4. 如果使用 2FA，可能需要使用 Personal Access Token"
    exit 1
fi
