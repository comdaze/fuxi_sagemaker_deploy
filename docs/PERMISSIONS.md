# 权限配置指南

## 🔑 必需的IAM权限

### 1. ECR权限
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:CreateRepository",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": "*"
        }
    ]
}
```

### 2. SageMaker权限
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sagemaker:CreateModel",
                "sagemaker:DeleteModel",
                "sagemaker:DescribeModel",
                "sagemaker:CreateTransformJob",
                "sagemaker:DescribeTransformJob",
                "sagemaker:StopTransformJob"
            ],
            "Resource": "*"
        }
    ]
}
```

### 3. Lambda权限
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:DeleteFunction",
                "lambda:GetFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:AddPermission"
            ],
            "Resource": "*"
        }
    ]
}
```

### 4. S3权限
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketNotification",
                "s3:PutBucketNotification"
            ],
            "Resource": [
                "arn:aws-cn:s3:::YOUR_BUCKET_NAME",
                "arn:aws-cn:s3:::YOUR_BUCKET_NAME/*"
            ]
        }
    ]
}
```

## 🏗️ IAM角色创建

### SageMaker执行角色
```bash
# 1. 创建信任策略
cat > sagemaker-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "sagemaker.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# 2. 创建角色
aws iam create-role \
    --role-name FuXiSageMakerExecutionRole \
    --assume-role-policy-document file://sagemaker-trust-policy.json

# 3. 附加策略
aws iam attach-role-policy \
    --role-name FuXiSageMakerExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy \
    --role-name FuXiSageMakerExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

### Lambda执行角色
```bash
# 1. 创建信任策略
cat > lambda-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# 2. 创建角色
aws iam create-role \
    --role-name FuXiLambdaExecutionRole \
    --assume-role-policy-document file://lambda-trust-policy.json

# 3. 附加策略
aws iam attach-role-policy \
    --role-name FuXiLambdaExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
    --role-name FuXiLambdaExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

aws iam attach-role-policy \
    --role-name FuXiLambdaExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

## ✅ 权限验证

### 自动检查
```bash
./scripts/check_permissions.sh YOUR_ACCOUNT_ID
```

### 手动验证
```bash
# 基本权限
aws sts get-caller-identity

# ECR权限
aws ecr get-authorization-token

# SageMaker权限
aws sagemaker list-models --max-items 1

# Lambda权限
aws lambda list-functions --max-items 1

# S3权限
aws s3 ls s3://YOUR_BUCKET_NAME/
```

## 🔒 安全最佳实践

### 1. 最小权限原则
- 只授予必需的权限
- 使用资源级权限限制
- 定期审查权限使用

### 2. 角色使用
- 优先使用IAM角色而非用户
- 为不同组件创建专用角色
- 启用角色会话标签

### 3. 监控审计
- 启用CloudTrail记录API调用
- 设置权限变更告警
- 定期检查访问日志

## 🚨 权限问题排查

### 常见错误
1. **AccessDenied**: 检查IAM权限
2. **AssumeRoleFailure**: 检查信任策略
3. **ResourceNotFound**: 检查资源ARN
4. **InvalidParameter**: 检查参数格式

### 调试步骤
1. 确认当前身份: `aws sts get-caller-identity`
2. 检查角色权限: `aws iam list-attached-role-policies`
3. 验证资源访问: 尝试具体操作
4. 查看错误日志: CloudTrail或CloudWatch
