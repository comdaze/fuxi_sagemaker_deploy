# FuXi Weather Model 部署指南

## 🎯 概述

FuXi天气预报模型完整部署解决方案，包含：

- 自定义Docker镜像（预装依赖，快速启动）
- SageMaker批量转换任务
- Lambda自动触发函数
- S3数据处理流程

## 🚀 快速部署

### 前置要求

1. **AWS CLI已配置**

   ```bash
   aws configure
   aws sts get-caller-identity
   ```
2. **Docker已安装**

   ```bash
   docker --version
   docker info
   ```
3. **必要权限**

   - ECR: 拉取/推送镜像
   - SageMaker: 创建模型和任务
   - Lambda: 创建函数
   - S3: 读写存储桶
   - IAM: 管理角色
4. **FUXI 模型已经上传到S3**
   确保"short.onnx" "medium.onnx" "long.onnx" "short" "medium" "long" 六个文件在fuxi_model目录下

   ```bash
   cd fuxi_model
   aws s3 sync . s3://YOUR_BUCKET_NAME/sagemaker/fuxi/
   ```

### 部署步骤

#### 1. 检查权限

```bash
cd docker
./check_permissions.sh YOUR_ACCOUNT_ID
```

#### 2. 构建Docker镜像

```bash
./build.sh YOUR_ACCOUNT_ID
```

#### 3. 设置模型文件

```bash
cd ../scripts
./setup_models.sh YOUR_BUCKET_NAME
```

#### 4. 执行部署

```bash
python deploy.py \
    --account-id YOUR_ACCOUNT_ID \
    --bucket YOUR_BUCKET_NAME \
    --environment prod
```

## 📁 文件说明

### 核心文件

- `scripts/deploy.py` - 主部署脚本
- `docker/Dockerfile` - 自定义镜像定义
- `model/inference.py` - 推理代码
- `lambda/function.py` - Lambda函数

### 辅助脚本

- `scripts/check_permissions.sh` - 权限检查
- `scripts/setup_models.sh` - 模型设置
- `docker/build.sh` - 镜像构建

## 🔧 配置说明

### 环境变量

- `FUXI_MODEL_BUCKET` - 模型存储桶
- `FUXI_MODEL_PREFIX` - 模型S3前缀
- `MODEL_NAME` - SageMaker模型名称
- `INSTANCE_TYPE` - 推理实例类型

### 资源命名

- SageMaker模型: `fuxi-weather-model-{environment}`
- Lambda函数: `fuxi-weather-lambda-{environment}`
- ECR仓库: `fuxi-weather-inference`

## 📊 监控验证

### 检查部署状态

```bash
# SageMaker模型
aws sagemaker describe-model --model-name fuxi-weather-model-prod

# Lambda函数
aws lambda get-function --function-name fuxi-weather-lambda-prod

# ECR镜像
aws ecr describe-images --repository-name fuxi-weather-inference
```

### 测试流程

1. 上传测试数据到S3
2. 创建 `_SUCCESS`文件触发Lambda
3. 监控批量转换任务状态
4. 检查输出结果

## 🛠️ 故障排除

### 常见问题

#### Docker构建失败

```bash
# 检查ECR登录
aws ecr get-login-password --region cn-northwest-1 | \
docker login --username AWS --password-stdin \
727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn

# 重新构建
docker build --no-cache -t fuxi-weather-inference .
```

#### SageMaker模型创建失败

- 检查执行角色权限
- 验证镜像URI正确性
- 确认模型数据URL可访问

#### Lambda函数执行失败

- 检查环境变量配置
- 验证SageMaker角色权限
- 查看CloudWatch日志

### 调试命令

```bash
# 查看Lambda日志
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/fuxi-weather

# 检查S3通知配置
aws s3api get-bucket-notification-configuration --bucket YOUR_BUCKET

# 测试批量转换
aws sagemaker describe-transform-job --transform-job-name JOB_NAME
```

## 📚 详细文档

- [故障排除](docs/TROUBLESHOOTING.md)
- [权限配置](docs/PERMISSIONS.md)

## 🎉 部署完成

部署成功后，系统将自动：

1. 监听S3的 `_SUCCESS`文件
2. 触发Lambda函数处理数据
3. 启动SageMaker批量转换任务
4. 使用优化的Docker镜像快速推理
5. 输出结果到指定S3路径
