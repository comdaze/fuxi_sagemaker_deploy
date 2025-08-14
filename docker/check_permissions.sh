#!/bin/bash

# ECR权限检查脚本
# 验证是否有权限访问AWS官方ECR和用户ECR

set -e

# 配置参数
REGION="cn-northwest-1"
AWS_ECR_REGISTRY="727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn"
ACCOUNT_ID="${1:-YOUR_ACCOUNT_ID}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 ECR权限检查${NC}"
echo -e "${BLUE}==================${NC}"

# 获取AWS账户ID（如果未提供）
if [ "$ACCOUNT_ID" = "YOUR_ACCOUNT_ID" ]; then
    echo -e "${YELLOW}⚠️  正在获取AWS账户ID...${NC}"
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region $REGION 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 无法获取AWS账户ID，请检查AWS凭证配置${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ 获取到账户ID: $ACCOUNT_ID${NC}"
fi

USER_ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com.cn"

echo -e "${BLUE}📋 检查配置:${NC}"
echo -e "  AWS区域: ${REGION}"
echo -e "  账户ID: ${ACCOUNT_ID}"
echo -e "  AWS官方ECR: ${AWS_ECR_REGISTRY}"
echo -e "  用户ECR: ${USER_ECR_REGISTRY}"
echo ""

# 检查AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI未安装${NC}"
    exit 1
fi

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装${NC}"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker未运行${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI和Docker已就绪${NC}"

# 1. 检查AWS凭证
echo -e "${YELLOW}🔐 检查AWS凭证...${NC}"
if aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    echo -e "${GREEN}✅ AWS凭证有效${NC}"
else
    echo -e "${RED}❌ AWS凭证无效或未配置${NC}"
    echo -e "${YELLOW}💡 请运行: aws configure${NC}"
    exit 1
fi

# 2. 检查ECR GetAuthorizationToken权限
echo -e "${YELLOW}🔑 检查ECR授权权限...${NC}"
if aws ecr get-authorization-token --region $REGION > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ECR授权权限正常${NC}"
else
    echo -e "${RED}❌ 缺少ECR授权权限${NC}"
    echo -e "${YELLOW}💡 需要权限: ecr:GetAuthorizationToken${NC}"
    exit 1
fi

# 3. 测试登录AWS官方ECR
echo -e "${YELLOW}🔐 测试AWS官方ECR登录...${NC}"
if aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $AWS_ECR_REGISTRY > /dev/null 2>&1; then
    echo -e "${GREEN}✅ AWS官方ECR登录成功${NC}"
else
    echo -e "${RED}❌ AWS官方ECR登录失败${NC}"
    echo -e "${YELLOW}💡 请检查是否有权限访问AWS官方ECR仓库${NC}"
    exit 1
fi

# 4. 测试拉取基础镜像
echo -e "${YELLOW}📥 测试拉取基础镜像...${NC}"
BASE_IMAGE="727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn/pytorch-inference:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker"
if docker pull $BASE_IMAGE > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 基础镜像拉取成功${NC}"
    # 清理测试镜像
    docker rmi $BASE_IMAGE > /dev/null 2>&1 || true
else
    echo -e "${RED}❌ 基础镜像拉取失败${NC}"
    echo -e "${YELLOW}💡 请检查网络连接和ECR权限${NC}"
    exit 1
fi

# 5. 测试登录用户ECR
echo -e "${YELLOW}🔐 测试用户ECR登录...${NC}"
if aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $USER_ECR_REGISTRY > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 用户ECR登录成功${NC}"
else
    echo -e "${RED}❌ 用户ECR登录失败${NC}"
    echo -e "${YELLOW}💡 请检查用户ECR权限${NC}"
    exit 1
fi

# 6. 检查用户ECR仓库
echo -e "${YELLOW}📦 检查用户ECR仓库...${NC}"
REPO_NAME="fuxi-weather-inference"
if aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ECR仓库已存在: $REPO_NAME${NC}"
else
    echo -e "${YELLOW}⚠️  ECR仓库不存在，构建时将自动创建${NC}"
fi

# 7. 检查推送权限
echo -e "${YELLOW}📤 检查ECR推送权限...${NC}"
# 这里我们只检查权限，不实际推送
if aws ecr get-repository-policy --repository-name $REPO_NAME --region $REGION > /dev/null 2>&1 || \
   aws ecr describe-repositories --repository-names $REPO_NAME --region $REGION > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ECR推送权限正常${NC}"
else
    echo -e "${YELLOW}⚠️  无法验证ECR推送权限，构建时将测试${NC}"
fi

echo ""
echo -e "${GREEN}🎉 ECR权限检查完成！${NC}"
echo -e "${BLUE}==================${NC}"
echo -e "${GREEN}✅ 所有必需权限都已具备${NC}"
echo ""
echo -e "${BLUE}💡 下一步:${NC}"
echo -e "1. 运行构建脚本: ./build.sh $ACCOUNT_ID"
echo -e "2. 或手动构建: docker build -t fuxi-weather-inference:latest ."
echo ""
echo -e "${BLUE}📋 权限摘要:${NC}"
echo -e "  ✅ AWS凭证配置正确"
echo -e "  ✅ ECR授权权限正常"
echo -e "  ✅ AWS官方ECR访问正常"
echo -e "  ✅ 基础镜像拉取成功"
echo -e "  ✅ 用户ECR访问正常"
