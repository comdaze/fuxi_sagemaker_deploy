#!/bin/bash

# FuXi Weather Model - Docker镜像构建脚本

set -e

ACCOUNT_ID="${1:-YOUR_ACCOUNT_ID}"
IMAGE_TAG="${2:-latest}"
REGION="cn-northwest-1"
REPOSITORY_NAME="fuxi-weather-inference"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 构建FuXi自定义Docker镜像${NC}"
echo -e "${BLUE}================================${NC}"

# 获取账户ID
if [ "$ACCOUNT_ID" = "YOUR_ACCOUNT_ID" ]; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION)
    echo -e "${GREEN}✅ 获取账户ID: $ACCOUNT_ID${NC}"
fi

ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com.cn"
FULL_IMAGE_NAME="${ECR_URI}/${REPOSITORY_NAME}:${IMAGE_TAG}"

echo -e "${BLUE}📋 构建配置:${NC}"
echo -e "  账户ID: ${ACCOUNT_ID}"
echo -e "  镜像名: ${FULL_IMAGE_NAME}"
echo ""

# 检查ECR仓库
echo -e "${YELLOW}📦 检查ECR仓库...${NC}"
if ! aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $REGION > /dev/null 2>&1; then
    echo -e "${YELLOW}创建ECR仓库: $REPOSITORY_NAME${NC}"
    aws ecr create-repository --repository-name $REPOSITORY_NAME --region $REGION
fi

# 登录ECR
echo -e "${YELLOW}🔐 登录ECR...${NC}"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin 727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# 构建镜像
echo -e "${YELLOW}🔨 构建Docker镜像...${NC}"
docker build -t $REPOSITORY_NAME:$IMAGE_TAG .

# 标记和推送
echo -e "${YELLOW}🏷️  标记镜像...${NC}"
docker tag $REPOSITORY_NAME:$IMAGE_TAG $FULL_IMAGE_NAME

echo -e "${YELLOW}📤 推送镜像...${NC}"
docker push $FULL_IMAGE_NAME

echo -e "${GREEN}🎉 镜像构建完成！${NC}"
echo -e "${GREEN}📦 镜像URI: ${FULL_IMAGE_NAME}${NC}"
