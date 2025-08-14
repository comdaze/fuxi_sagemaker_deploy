import json
import boto3
from datetime import datetime
import os

def lambda_handler(event, context):
    """
    优化版Lambda处理函数
    - 使用自定义Docker镜像的SageMaker模型
    - 支持环境变量配置
    - 增强错误处理和日志
    """
    
    s3_client = boto3.client('s3')
    sagemaker_client = boto3.client('sagemaker')
    
    # 从环境变量获取配置
    model_bucket = os.environ.get('MODEL_BUCKET')
    sagemaker_role = os.environ.get('SAGEMAKER_ROLE')
    model_name = os.environ.get('MODEL_NAME', 'fuxi-weather-model-optimized')
    instance_type = os.environ.get('INSTANCE_TYPE', 'ml.g4dn.2xlarge')
    instance_count = int(os.environ.get('INSTANCE_COUNT', '1'))
    
    print(f"🚀 Lambda函数启动 - 使用优化的Docker镜像")
    print(f"📋 配置信息:")
    print(f"  模型存储桶: {model_bucket}")
    print(f"  SageMaker角色: {sagemaker_role}")
    print(f"  模型名称: {model_name}")
    print(f"  实例类型: {instance_type}")
    print(f"  实例数量: {instance_count}")
    
    # 验证必需的环境变量
    if not model_bucket:
        print("❌ 错误: 未设置MODEL_BUCKET环境变量")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'MODEL_BUCKET environment variable not set'})
        }
    
    if not sagemaker_role:
        print("❌ 错误: 未设置SAGEMAKER_ROLE环境变量")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'SAGEMAKER_ROLE environment variable not set'})
        }
    
    processed_jobs = []
    
    # 处理每个S3事件记录
    for record in event['Records']:
        try:
            # 获取触发事件的桶名和对象键
            bucket_name = record['s3']['bucket']['name']
            object_key = record['s3']['object']['key']
            
            print(f"📥 处理S3事件: s3://{bucket_name}/{object_key}")
            
            # 确保是_SUCCESS文件
            if not object_key.endswith('_SUCCESS'):
                print(f"⏭️  跳过非_SUCCESS文件: {object_key}")
                continue
                
            # 获取_SUCCESS文件所在的目录路径
            folder_path = os.path.dirname(object_key)
            print(f"📁 处理目录: {folder_path}")
            
            # 列出该目录下的所有.nc文件
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=folder_path + '/',
                Delimiter='/'
            )
            
            nc_files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    file_key = obj['Key']
                    if file_key.endswith('.nc'):
                        # 保存完整的S3路径
                        s3_path = f's3://{bucket_name}/{file_key}'
                        nc_files.append(s3_path)
            
            print(f"🔍 找到 {len(nc_files)} 个.nc文件")
            
            if len(nc_files) == 0:
                print("⚠️  未找到.nc文件，跳过处理")
                continue
            
            # 按文件名排序
            nc_files.sort()
            
            # 创建JSONL内容，每两个文件为一组
            jsonl_lines = []
            for i in range(0, len(nc_files), 2):
                if i + 1 < len(nc_files):
                    line_data = {
                        "filename1": nc_files[i],
                        "filename2": nc_files[i + 1]
                    }
                    jsonl_lines.append(json.dumps(line_data))
            
            # 如果nc文件数量为奇数，处理最后一个文件
            if len(nc_files) % 2 == 1:
                line_data = {
                    "filename1": nc_files[-1],
                    "filename2": nc_files[0]  # 使用第一个文件作为备用
                }
                jsonl_lines.append(json.dumps(line_data))
            
            print(f"📝 生成 {len(jsonl_lines)} 行JSONL数据")
            
            # 创建JSONL文件内容
            jsonl_content = '\n'.join(jsonl_lines)
            
            # 从nc文件名中提取日期
            if nc_files:
                # 从S3路径中提取文件名
                first_file_name = os.path.basename(nc_files[0])
                # 假设文件名格式如：20240101_00.nc 或 2024010100.nc
                # 提取日期部分
                if '_' in first_file_name:
                    date_str = first_file_name.split('_')[0][:8]
                elif '.' in first_file_name:
                    date_str = first_file_name.split('.')[0][:8]
                else:
                    date_str = datetime.now().strftime('%Y%m%d')
            else:
                date_str = datetime.now().strftime('%Y%m%d')
            
            print(f"📅 提取日期: {date_str}")
            
            # 设置S3路径
            s3_prefix = 'sagemaker/fuxi'
            
            # 创建带日期和时间戳的JSONL文件名
            timestamp = int(datetime.now().timestamp())
            jsonl_file_name = f'input/{date_str}-{timestamp}.jsonl'
            s3_data_path = f's3://{model_bucket}/{s3_prefix}/{jsonl_file_name}'
            s3_output_path = f's3://{model_bucket}/{s3_prefix}/output/{date_str}-{timestamp}/'
            
            # 上传JSONL文件到S3
            try:
                s3_client.put_object(
                    Bucket=model_bucket,
                    Key=f'{s3_prefix}/{jsonl_file_name}',
                    Body=jsonl_content.encode('utf-8'),
                    ContentType='application/x-jsonlines'
                )
                print(f"✅ JSONL文件上传成功: {s3_data_path}")
            except Exception as e:
                print(f"❌ JSONL文件上传失败: {e}")
                continue
            
            # 创建SageMaker批量转换任务
            transform_job_name = f"fuxi-optimized-{date_str}-{timestamp}"
            
            # 检查模型是否存在
            try:
                sagemaker_client.describe_model(ModelName=model_name)
                print(f"✅ 确认模型存在: {model_name}")
            except sagemaker_client.exceptions.ClientError as e:
                if 'ValidationException' in str(e):
                    print(f"❌ 模型不存在: {model_name}")
                    print("💡 请先创建使用自定义Docker镜像的SageMaker模型")
                    continue
                else:
                    raise e
            
            try:
                # 使用优化的配置创建批量转换任务
                response = sagemaker_client.create_transform_job(
                    TransformJobName=transform_job_name,
                    ModelName=model_name,  # 使用自定义Docker镜像的模型
                    TransformInput={
                        'DataSource': {
                            'S3DataSource': {
                                'S3DataType': 'S3Prefix',
                                'S3Uri': s3_data_path
                            }
                        },
                        'ContentType': 'application/json',
                        'SplitType': 'Line'
                    },
                    TransformOutput={
                        'S3OutputPath': s3_output_path,
                        'Accept': 'application/json',
                        'AssembleWith': 'Line'
                    },
                    TransformResources={
                        'InstanceType': instance_type,
                        'InstanceCount': instance_count
                    },
                    Environment={
                        # 优化的环境变量配置
                        'TS_DEFAULT_WORKERS_PER_MODEL': '1',
                        'TS_DEFAULT_RESPONSE_TIMEOUT': '3600',
                        'SAGEMAKER_MODEL_SERVER_TIMEOUT': '3600',
                        'SAGEMAKER_MODEL_SERVER_WORKERS': '1',
                        # FuXi模型特定配置
                        'FUXI_MODEL_BUCKET': model_bucket,
                        'FUXI_MODEL_PREFIX': 'sagemaker/fuxi',
                        'SAGEMAKER_PROGRAM': 'inference.py'
                    },
                    Tags=[
                        {
                            'Key': 'Project',
                            'Value': 'FuXi-Weather-Forecast'
                        },
                        {
                            'Key': 'Environment',
                            'Value': os.environ.get('ENVIRONMENT', 'dev')
                        },
                        {
                            'Key': 'OptimizedImage',
                            'Value': 'true'
                        },
                        {
                            'Key': 'Date',
                            'Value': date_str
                        }
                    ]
                )
                
                job_info = {
                    'job_name': transform_job_name,
                    'job_arn': response['TransformJobArn'],
                    'input_path': s3_data_path,
                    'output_path': s3_output_path,
                    'date': date_str,
                    'nc_files_count': len(nc_files)
                }
                
                processed_jobs.append(job_info)
                
                print(f"✅ SageMaker批量转换任务创建成功: {transform_job_name}")
                print(f"📍 任务ARN: {response['TransformJobArn']}")
                print(f"📥 输入路径: {s3_data_path}")
                print(f"📤 输出路径: {s3_output_path}")
                print(f"🏷️  使用优化镜像: {model_name}")
                
            except Exception as e:
                print(f"❌ SageMaker批量转换任务创建失败: {e}")
                print("💡 请检查:")
                print(f"  - 模型是否存在: {model_name}")
                print(f"  - 角色权限: {sagemaker_role}")
                print(f"  - 实例配额: {instance_type}")
                
                # 记录详细信息供调试
                print(f"📊 详细信息:")
                print(f"  输入路径: {s3_data_path}")
                print(f"  输出路径: {s3_output_path}")
                print(f"  角色ARN: {sagemaker_role}")
                print(f"  实例类型: {instance_type}")
                
        except Exception as e:
            print(f"❌ 处理记录时出错: {e}")
            print(f"📊 记录详情: {json.dumps(record, indent=2)}")
            continue
    
    # 返回处理结果
    result = {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Lambda function executed successfully with optimized Docker image',
            'processed_records': len(event['Records']),
            'created_jobs': len(processed_jobs),
            'jobs': processed_jobs,
            'optimizations': {
                'custom_docker_image': True,
                'pre_installed_dependencies': True,
                'faster_startup': True,
                'model_name': model_name
            }
        }, indent=2)
    }
    
    print(f"🎉 Lambda执行完成:")
    print(f"  处理记录数: {len(event['Records'])}")
    print(f"  创建任务数: {len(processed_jobs)}")
    print(f"  使用优化镜像: {model_name}")
    
    return result
