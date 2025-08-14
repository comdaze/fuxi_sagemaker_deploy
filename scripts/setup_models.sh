#!/bin/bash

# FuXi Weather Model - 模型设置脚本
# 包含模型包创建和上传功能

set -e

BUCKET_NAME="${1:-sagemaker-cn-northwest-1-YOUR_ACCOUNT_ID}"
MODEL_DIR="${2:-../fuxi_models}"
REGION="cn-northwest-1"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 FuXi模型设置${NC}"
echo -e "${BLUE}=================${NC}"
echo -e "${BLUE}存储桶: ${BUCKET_NAME}${NC}"
echo -e "${BLUE}模型目录: ${MODEL_DIR}${NC}"
echo ""

# 1. 创建推理代码包
echo -e "${YELLOW}📦 创建推理代码包...${NC}"
cd ../model
if [ -f "model.tar.gz" ]; then
    rm -f model.tar.gz
    echo -e "${YELLOW}🗑️  删除旧的模型包${NC}"
fi

tar -czf model.tar.gz *.py
echo -e "${GREEN}✅ 推理代码包创建完成: model.tar.gz${NC}"

# 2. 上传推理代码包
echo -e "${YELLOW}📤 上传推理代码包到S3...${NC}"
aws s3 cp model.tar.gz "s3://${BUCKET_NAME}/sagemaker/fuxi/model.tar.gz" --region $REGION
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 推理代码包上传完成${NC}"
else
    echo -e "${RED}❌ 推理代码包上传失败${NC}"
    exit 1
fi

# 3. 检查和上传模型文件
echo -e "${YELLOW}🔍 检查模型文件...${NC}"
required_files=("short.onnx" "medium.onnx" "long.onnx" "short" "medium" "long")
missing_files=()
upload_needed=()

for file in "${required_files[@]}"; do
    # 检查S3中是否已存在
    if aws s3 ls "s3://${BUCKET_NAME}/sagemaker/fuxi/${file}" --region $REGION > /dev/null 2>&1; then
        echo -e "${GREEN}✅ S3中已存在: ${file}${NC}"
    else
        # 检查本地是否存在
        if [ -f "${MODEL_DIR}/${file}" ]; then
            echo -e "${YELLOW}📤 需要上传: ${file}${NC}"
            upload_needed+=("$file")
        else
            echo -e "${RED}❌ 缺少文件: ${file}${NC}"
            missing_files+=("$file")
        fi
    fi
done

# 上传需要的模型文件
if [ ${#upload_needed[@]} -gt 0 ]; then
    echo -e "${YELLOW}📤 上传模型文件到S3...${NC}"
    for file in "${upload_needed[@]}"; do
        local_file="${MODEL_DIR}/${file}"
        s3_path="s3://${BUCKET_NAME}/sagemaker/fuxi/${file}"
        
        echo -e "${BLUE}正在上传: $file${NC}"
        if aws s3 cp "$local_file" "$s3_path" --region $REGION; then
            echo -e "${GREEN}✅ 上传成功: $file${NC}"
        else
            echo -e "${RED}❌ 上传失败: $file${NC}"
            exit 1
        fi
    done
fi

# 显示缺失文件信息
if [ ${#missing_files[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  缺少以下模型文件:${NC}"
    for file in "${missing_files[@]}"; do
        echo -e "${RED}   - ${file}${NC}"
    done
    echo ""
    echo -e "${BLUE}💡 获取缺失文件的方法:${NC}"
    echo -e "1. 运行下载脚本: ./download_models.sh"
    echo -e "2. 手动下载后放入: ${MODEL_DIR}/"
    echo -e "3. 重新运行此脚本"
fi

# 验证最终结果
echo -e "${YELLOW}📋 验证S3文件列表...${NC}"
aws s3 ls "s3://${BUCKET_NAME}/sagemaker/fuxi/" --recursive --region $REGION

echo -e "${GREEN}🎉 模型设置完成！${NC}"
echo ""
echo -e "${BLUE}💡 下一步:${NC}"
echo -e "python deploy.py --account-id YOUR_ACCOUNT_ID --bucket ${BUCKET_NAME}"
