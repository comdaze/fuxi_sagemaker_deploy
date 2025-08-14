#!/usr/bin/env python3
"""
FuXi Weather Model - 主部署脚本
包含IAM角色自动创建功能
"""

import boto3
import json
import argparse
import time
import os
from datetime import datetime
from botocore.exceptions import ClientError

def create_iam_roles(account_id, region):
    """创建必需的IAM角色"""
    iam = boto3.client('iam', region_name=region)
    
    print("🔑 检查和创建IAM角色")
    
    # 根据区域确定服务主体和策略前缀
    if region.startswith('cn-'):
        # 中国区域的服务主体仍然使用 .com，但策略ARN使用 aws-cn
        sagemaker_service = "sagemaker.amazonaws.com"
        lambda_service = "lambda.amazonaws.com"
        policy_prefix = "arn:aws-cn:iam::aws:policy"
    else:
        sagemaker_service = "sagemaker.amazonaws.com"
        lambda_service = "lambda.amazonaws.com"
        policy_prefix = "arn:aws:iam::aws:policy"
    
    # SageMaker执行角色
    sagemaker_role_name = 'FuXiSageMakerExecutionRole'
    sagemaker_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": sagemaker_service
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Lambda执行角色
    lambda_role_name = 'FuXiLambdaExecutionRole'
    lambda_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": lambda_service
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # 创建SageMaker角色
    try:
        iam.get_role(RoleName=sagemaker_role_name)
        print(f"✅ SageMaker角色已存在: {sagemaker_role_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"🔨 创建SageMaker角色: {sagemaker_role_name}")
            iam.create_role(
                RoleName=sagemaker_role_name,
                AssumeRolePolicyDocument=json.dumps(sagemaker_trust_policy),
                Description='FuXi Weather Model SageMaker Execution Role'
            )
            
            # 附加必要的策略
            policies = [
                f'{policy_prefix}/AmazonSageMakerFullAccess',
                f'{policy_prefix}/AmazonS3FullAccess',
                f'{policy_prefix}/AmazonEC2ContainerRegistryReadOnly'
            ]
            
            for policy_arn in policies:
                try:
                    iam.attach_role_policy(
                        RoleName=sagemaker_role_name,
                        PolicyArn=policy_arn
                    )
                    print(f"  ✅ 附加策略: {policy_arn}")
                except ClientError as policy_error:
                    print(f"  ⚠️  策略附加失败: {policy_arn} - {policy_error}")
            
            # 等待角色生效
            print("⏳ 等待角色生效...")
            time.sleep(10)
        else:
            raise e
    
    # 创建Lambda角色
    try:
        iam.get_role(RoleName=lambda_role_name)
        print(f"✅ Lambda角色已存在: {lambda_role_name}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"🔨 创建Lambda角色: {lambda_role_name}")
            iam.create_role(
                RoleName=lambda_role_name,
                AssumeRolePolicyDocument=json.dumps(lambda_trust_policy),
                Description='FuXi Weather Model Lambda Execution Role'
            )
            
            # 附加必要的策略
            policies = [
                f'{policy_prefix}/service-role/AWSLambdaBasicExecutionRole',
                f'{policy_prefix}/AmazonSageMakerFullAccess',
                f'{policy_prefix}/AmazonS3FullAccess'
            ]
            
            for policy_arn in policies:
                try:
                    iam.attach_role_policy(
                        RoleName=lambda_role_name,
                        PolicyArn=policy_arn
                    )
                    print(f"  ✅ 附加策略: {policy_arn}")
                except ClientError as policy_error:
                    print(f"  ⚠️  策略附加失败: {policy_arn} - {policy_error}")
            
            # 等待角色生效
            print("⏳ 等待角色生效...")
            time.sleep(10)
        else:
            raise e
    
    # 返回角色ARN
    arn_prefix = f'arn:aws-cn:iam::{account_id}:role' if region.startswith('cn-') else f'arn:aws:iam::{account_id}:role'
    sagemaker_role_arn = f'{arn_prefix}/{sagemaker_role_name}'
    lambda_role_arn = f'{arn_prefix}/{lambda_role_name}'
    
    return sagemaker_role_arn, lambda_role_arn

def check_ecr_image(image_uri, region):
    """检查ECR镜像是否存在"""
    ecr = boto3.client('ecr', region_name=region)
    
    try:
        # 解析镜像URI
        parts = image_uri.split('/')
        repository_name = parts[-1].split(':')[0]
        tag = parts[-1].split(':')[1] if ':' in parts[-1] else 'latest'
        
        # 检查镜像
        response = ecr.describe_images(
            repositoryName=repository_name,
            imageIds=[{'imageTag': tag}]
        )
        
        if response['imageDetails']:
            print(f"✅ ECR镜像存在: {image_uri}")
            return True
        else:
            print(f"❌ ECR镜像不存在: {image_uri}")
            return False
            
    except ClientError as e:
        if e.response['Error']['Code'] == 'RepositoryNotFoundException':
            print(f"❌ ECR仓库不存在: {repository_name}")
            print("💡 请先运行: cd docker && ./build.sh")
        else:
            print(f"❌ 检查ECR镜像失败: {e}")
        return False

def check_s3_model(model_data_url, region):
    """检查S3模型文件是否存在"""
    s3 = boto3.client('s3', region_name=region)
    
    try:
        # 解析S3 URL
        parts = model_data_url.replace('s3://', '').split('/')
        bucket_name = parts[0]
        key = '/'.join(parts[1:])
        
        # 检查文件
        s3.head_object(Bucket=bucket_name, Key=key)
        print(f"✅ S3模型文件存在: {model_data_url}")
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            print(f"❌ S3模型文件不存在: {model_data_url}")
            print("💡 请先运行: ./scripts/setup_models.sh")
        else:
            print(f"❌ 检查S3模型文件失败: {e}")
        return False

def create_sagemaker_model(model_name, execution_role_arn, image_uri, model_data_url, bucket_name, region):
    """创建SageMaker模型"""
    sagemaker = boto3.client('sagemaker', region_name=region)
    
    print(f"🚀 创建SageMaker模型: {model_name}")
    
    # 删除现有模型
    try:
        sagemaker.describe_model(ModelName=model_name)
        print(f"🗑️  删除现有模型")
        sagemaker.delete_model(ModelName=model_name)
        time.sleep(5)
    except ClientError:
        pass
    
    # 创建新模型
    environment = {
        'SAGEMAKER_PROGRAM': 'inference.py',
        'FUXI_MODEL_BUCKET': bucket_name,
        'FUXI_MODEL_PREFIX': 'sagemaker/fuxi',
        'PYTHONUNBUFFERED': 'TRUE'
    }
    
    response = sagemaker.create_model(
        ModelName=model_name,
        PrimaryContainer={
            'Image': image_uri,
            'ModelDataUrl': model_data_url,
            'Environment': environment
        },
        ExecutionRoleArn=execution_role_arn
    )
    
    print(f"✅ SageMaker模型创建成功")
    return response['ModelArn']

def create_lambda_function(function_name, role_arn, bucket_name, model_name, region):
    """创建Lambda函数"""
    lambda_client = boto3.client('lambda', region_name=region)
    
    print(f"⚡ 创建Lambda函数: {function_name}")
    
    # 读取Lambda代码
    lambda_file = os.path.join(os.path.dirname(__file__), '../lambda/function.py')
    if not os.path.exists(lambda_file):
        print(f"❌ Lambda代码文件不存在: {lambda_file}")
        return None
        
    with open(lambda_file, 'r', encoding='utf-8') as f:
        lambda_code = f.read()
    
    # 创建ZIP文件
    import zipfile
    import io
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', lambda_code)
    
    zip_buffer.seek(0)
    zip_content = zip_buffer.read()
    
    # 删除现有函数
    try:
        lambda_client.delete_function(FunctionName=function_name)
        time.sleep(10)
    except ClientError:
        pass
    
    # 环境变量
    env_vars = {
        'MODEL_BUCKET': bucket_name,
        'SAGEMAKER_ROLE': role_arn.replace('Lambda', 'SageMaker'),
        'MODEL_NAME': model_name,
        'INSTANCE_TYPE': 'ml.g4dn.2xlarge'
    }
    
    response = lambda_client.create_function(
        FunctionName=function_name,
        Runtime='python3.9',
        Role=role_arn,
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': zip_content},
        Timeout=900,
        MemorySize=512,
        Environment={'Variables': env_vars}
    )
    
    print(f"✅ Lambda函数创建成功")
    return response['FunctionArn']

def setup_s3_trigger(bucket_name, lambda_arn, region):
    """设置S3触发器"""
    s3 = boto3.client('s3', region_name=region)
    lambda_client = boto3.client('lambda', region_name=region)
    
    print(f"🔗 设置S3触发器")
    
    # 根据区域确定S3服务主体 - 中国区域也使用 s3.amazonaws.com
    s3_service = "s3.amazonaws.com"
    s3_arn_prefix = "arn:aws-cn:s3:::" if region.startswith('cn-') else "arn:aws:s3:::"
    
    try:
        # 添加Lambda权限
        try:
            lambda_client.add_permission(
                FunctionName=lambda_arn,
                StatementId=f'allow-s3-{bucket_name}',
                Action='lambda:InvokeFunction',
                Principal=s3_service,
                SourceArn=f'{s3_arn_prefix}{bucket_name}'
            )
            print(f"  ✅ Lambda权限添加成功")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceConflictException':
                print(f"  ✅ Lambda权限已存在")
            else:
                print(f"  ⚠️  Lambda权限添加失败: {e}")
                # 尝试删除现有权限后重新添加
                try:
                    lambda_client.remove_permission(
                        FunctionName=lambda_arn,
                        StatementId=f'allow-s3-{bucket_name}'
                    )
                    time.sleep(2)
                    lambda_client.add_permission(
                        FunctionName=lambda_arn,
                        StatementId=f'allow-s3-{bucket_name}',
                        Action='lambda:InvokeFunction',
                        Principal=s3_service,
                        SourceArn=f'{s3_arn_prefix}{bucket_name}'
                    )
                    print(f"  ✅ Lambda权限重新添加成功")
                except ClientError as retry_error:
                    print(f"  ❌ Lambda权限重新添加失败: {retry_error}")
                    return False
        
        # 等待权限生效
        print(f"  ⏳ 等待权限生效...")
        time.sleep(10)
        
        # 配置S3通知
        notification_config = {
            'LambdaFunctionConfigurations': [{
                'Id': 'FuXiTrigger',
                'LambdaFunctionArn': lambda_arn,
                'Events': ['s3:ObjectCreated:*'],
                'Filter': {
                    'Key': {
                        'FilterRules': [{'Name': 'suffix', 'Value': '_SUCCESS'}]
                    }
                }
            }]
        }
        
        s3.put_bucket_notification_configuration(
            Bucket=bucket_name,
            NotificationConfiguration=notification_config
        )
        
        print(f"✅ S3触发器设置完成")
        return True
        
    except ClientError as e:
        print(f"⚠️  S3触发器设置失败: {e}")
        print(f"💡 可以稍后手动在AWS控制台中配置S3触发器")
        return False

def main():
    parser = argparse.ArgumentParser(description='FuXi Weather Model 部署')
    parser.add_argument('--account-id', '-a', required=True, help='AWS账户ID')
    parser.add_argument('--bucket', '-b', help='S3存储桶名称')
    parser.add_argument('--region', '-r', default='cn-northwest-1', help='AWS区域')
    parser.add_argument('--environment', '-e', default='prod', help='环境')
    parser.add_argument('--skip-checks', action='store_true', help='跳过预检查')
    
    args = parser.parse_args()
    
    account_id = args.account_id
    region = args.region
    environment = args.environment
    bucket_name = args.bucket or f'sagemaker-{region}-{account_id}'
    
    # 资源名称
    model_name = f'fuxi-weather-model-{environment}'
    lambda_name = f'fuxi-weather-lambda-{environment}'
    
    # 镜像和模型URL
    image_uri = f'{account_id}.dkr.ecr.{region}.amazonaws.com.cn/fuxi-weather-inference:latest'
    model_data_url = f's3://{bucket_name}/sagemaker/fuxi/model.tar.gz'
    
    print("🚀 FuXi Weather Model 部署开始")
    print("=" * 40)
    print(f"账户ID: {account_id}")
    print(f"区域: {region}")
    print(f"环境: {environment}")
    print(f"存储桶: {bucket_name}")
    print(f"镜像: {image_uri}")
    print()
    
    try:
        # 1. 创建IAM角色
        sagemaker_role_arn, lambda_role_arn = create_iam_roles(account_id, region)
        
        # 2. 预检查（可选）
        if not args.skip_checks:
            print("🔍 执行预检查")
            checks_passed = True
            
            if not check_ecr_image(image_uri, region):
                checks_passed = False
                
            if not check_s3_model(model_data_url, region):
                checks_passed = False
            
            if not checks_passed:
                print("❌ 预检查失败，请解决上述问题后重试")
                print("💡 或使用 --skip-checks 跳过检查")
                return 1
            
            print("✅ 预检查通过")
            print()
        
        # 3. 创建SageMaker模型
        model_arn = create_sagemaker_model(
            model_name, sagemaker_role_arn, image_uri, model_data_url, bucket_name, region
        )
        
        # 4. 创建Lambda函数
        lambda_arn = create_lambda_function(
            lambda_name, lambda_role_arn, bucket_name, model_name, region
        )
        
        if lambda_arn:
            # 5. 设置S3触发器
            s3_trigger_success = setup_s3_trigger(bucket_name, lambda_arn, region)
        else:
            s3_trigger_success = False
        
        print()
        print("🎉 部署完成！")
        print("=" * 40)
        print(f"SageMaker模型: {model_name}")
        print(f"Lambda函数: {lambda_name}")
        print(f"S3存储桶: {bucket_name}")
        print(f"SageMaker角色: {sagemaker_role_arn}")
        print(f"Lambda角色: {lambda_role_arn}")
        
        if not s3_trigger_success:
            print()
            print("⚠️  注意: S3触发器配置失败")
            print("💡 请手动在AWS控制台中配置S3触发器:")
            print(f"   - 存储桶: {bucket_name}")
            print(f"   - 事件: s3:ObjectCreated:*")
            print(f"   - 后缀过滤: _SUCCESS")
            print(f"   - Lambda函数: {lambda_name}")
        
        print()
        print("💡 下一步:")
        print("1. 上传测试数据到S3")
        print("2. 监控批量转换任务")
        
    except Exception as e:
        print(f"❌ 部署失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
