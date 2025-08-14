# 故障排除指南

## 🔍 常见问题

### 1. Docker镜像构建失败

#### 问题: 无法拉取基础镜像
```
Error: pull access denied for 727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn
```

**解决方案:**
```bash
# 登录AWS官方ECR
aws ecr get-login-password --region cn-northwest-1 | \
docker login --username AWS --password-stdin \
727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn

# 检查网络连接
ping 727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn
```

#### 问题: 依赖安装失败
```
ERROR: Could not install packages due to an EnvironmentError
```

**解决方案:**
```bash
# 清理Docker缓存
docker system prune -a

# 重新构建
docker build --no-cache -t fuxi-weather-inference .
```

### 2. SageMaker模型创建失败

#### 问题: 执行角色权限不足
```
ValidationException: The role provided does not have permission
```

**解决方案:**
检查IAM角色是否包含以下权限：
- `sagemaker:*`
- `s3:GetObject`
- `s3:PutObject`
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:GetDownloadUrlForLayer`
- `ecr:BatchGetImage`

#### 问题: 镜像不存在
```
ValidationException: Could not find image
```

**解决方案:**
```bash
# 检查镜像是否存在
aws ecr describe-images --repository-name fuxi-weather-inference

# 重新构建镜像
cd docker && ./build.sh YOUR_ACCOUNT_ID
```

### 3. Lambda函数执行失败

#### 问题: 环境变量未设置
```
KeyError: 'MODEL_BUCKET'
```

**解决方案:**
```bash
# 检查Lambda环境变量
aws lambda get-function-configuration --function-name fuxi-weather-lambda-prod

# 更新环境变量
aws lambda update-function-configuration \
    --function-name fuxi-weather-lambda-prod \
    --environment Variables='{
        "MODEL_BUCKET": "your-bucket-name",
        "MODEL_NAME": "fuxi-weather-model-prod"
    }'
```

#### 问题: 超时错误
```
Task timed out after 3.00 seconds
```

**解决方案:**
```bash
# 增加超时时间
aws lambda update-function-configuration \
    --function-name fuxi-weather-lambda-prod \
    --timeout 900
```

### 4. 批量转换任务失败

#### 问题: 模型文件不存在
```
ModelError: An error occurred (404) when calling the HeadObject operation
```

**解决方案:**
```bash
# 检查模型文件
aws s3 ls s3://YOUR_BUCKET/sagemaker/fuxi/ --recursive

# 重新上传模型文件
./scripts/setup_models.sh YOUR_BUCKET
```

#### 问题: GPU配额不足
```
ResourceLimitExceeded: The account-level service limit 'ml.g4dn.2xlarge for transform job usage' is 0
```

**解决方案:**
1. 在AWS控制台申请GPU实例配额
2. 或使用CPU实例类型（性能较低）

### 5. S3触发器不工作

#### 问题: Lambda未被触发
**解决方案:**
```bash
# 检查S3通知配置
aws s3api get-bucket-notification-configuration --bucket YOUR_BUCKET

# 检查Lambda权限
aws lambda get-policy --function-name fuxi-weather-lambda-prod

# 手动测试Lambda
aws lambda invoke \
    --function-name fuxi-weather-lambda-prod \
    --payload '{"Records":[{"s3":{"bucket":{"name":"test"},"object":{"key":"test/_SUCCESS"}}}]}' \
    response.json
```

## 🔧 调试工具

### 日志查看
```bash
# Lambda日志
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/fuxi-weather
aws logs get-log-events --log-group-name /aws/lambda/fuxi-weather-lambda-prod --log-stream-name LATEST

# SageMaker日志
aws logs describe-log-groups --log-group-name-prefix /aws/sagemaker/TransformJobs
```

### 状态检查
```bash
# 检查所有资源状态
echo "=== SageMaker模型 ==="
aws sagemaker describe-model --model-name fuxi-weather-model-prod

echo "=== Lambda函数 ==="
aws lambda get-function --function-name fuxi-weather-lambda-prod

echo "=== ECR镜像 ==="
aws ecr describe-images --repository-name fuxi-weather-inference --max-items 1

echo "=== S3存储桶 ==="
aws s3 ls s3://YOUR_BUCKET/sagemaker/fuxi/
```

### 权限验证
```bash
# 运行权限检查脚本
./scripts/check_permissions.sh YOUR_ACCOUNT_ID

# 手动检查关键权限
aws sts get-caller-identity
aws ecr get-authorization-token
aws sagemaker list-models --max-items 1
```

## 📞 获取帮助

如果问题仍未解决：

1. **查看详细日志**: 启用详细日志记录
2. **检查权限**: 确保所有IAM权限正确配置
3. **验证网络**: 确认网络连接正常
4. **重新部署**: 尝试完全重新部署系统

## 🚨 紧急恢复

如果系统完全不可用：

```bash
# 1. 清理所有资源
aws sagemaker delete-model --model-name fuxi-weather-model-prod
aws lambda delete-function --function-name fuxi-weather-lambda-prod

# 2. 重新部署
python scripts/deploy.py --account-id YOUR_ACCOUNT_ID --bucket YOUR_BUCKET

# 3. 验证部署
./scripts/check_permissions.sh YOUR_ACCOUNT_ID
```
