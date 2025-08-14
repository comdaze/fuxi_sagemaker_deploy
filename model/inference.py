import os
import json
import time
import torch
import numpy as np
import xarray as xr
import pandas as pd
import onnxruntime as ort

from util import save_like, test_rmse

import boto3
from urllib.parse import urlparse


num_steps = [20, 20, 34]


def download_s3_file(s3_path, local_dir="/tmp"):
    """
    从S3下载文件到本地目录
    
    Args:
        s3_path: S3文件路径，格式如 s3://bucket/key/to/file
        local_dir: 本地目标目录，默认为/tmp
    
    Returns:
        local_file_path: 下载后的本地文件路径
    """
    # 解析S3路径
    parsed_url = urlparse(s3_path)
    bucket_name = parsed_url.netloc
    s3_key = parsed_url.path.lstrip('/')
    
    # 获取文件名
    file_name = os.path.basename(s3_key)
    
    # 构建本地文件路径
    local_file_path = os.path.join(local_dir, file_name)
    
    # 创建S3客户端
    s3_client = boto3.client('s3', region_name='cn-northwest-1')
    
    try:
        # 下载文件
        print(f"正在下载: {s3_path}")
        print(f"目标位置: {local_file_path}")
        
        s3_client.download_file(bucket_name, s3_key, local_file_path)
        
        print(f"文件下载成功: {local_file_path}")
        return local_file_path
        
    except Exception as e:
        print(f"下载失败: {str(e)}")
        raise


def upload_file_to_s3(local_file_path, s3_path):
    """
    上传本地文件到S3指定路径
    
    Args:
        local_file_path: 本地文件路径
        s3_path: S3目标路径，格式如 s3://bucket/key/to/file
    
    Returns:
        bool: 上传成功返回True，失败返回False
    """
    # 检查本地文件是否存在
    if not os.path.exists(local_file_path):
        print(f"错误: 本地文件不存在: {local_file_path}")
        return False
    
    # 解析S3路径
    parsed_url = urlparse(s3_path)
    bucket_name = parsed_url.netloc
    s3_key = parsed_url.path.lstrip('/')
    
    # 创建S3客户端
    s3_client = boto3.client('s3', region_name='cn-northwest-1')
    
    try:
        # 获取文件大小
        file_size = os.path.getsize(local_file_path)
        print(f"正在上传文件: {local_file_path} ({file_size:,} bytes)")
        print(f"目标位置: {s3_path}")
        
        # 上传文件
        s3_client.upload_file(local_file_path, bucket_name, s3_key)
        
        print(f"文件上传成功: {s3_path}")
        return True
        
    except Exception as e:
        print(f"上传失败: {str(e)}")
        return False


def remove_file(file_path):
    try:
        os.remove(file_path)
        print(f"文件已删除: {file_path}")
        return True
    except FileNotFoundError:
        print(f"文件不存在: {file_path}")
    except PermissionError:
        print(f"没有权限删除文件: {file_path}")
    except Exception as e:
        print(f"删除文件时出错: {e}")
    return False

        
def time_encoding(init_time, total_step, freq=6):
    init_time = np.array([init_time])
    tembs = []
    for i in range(total_step):
        hours = np.array([pd.Timedelta(hours=t*freq) for t in [i-1, i, i+1]])
        times = init_time[:, None] + hours[None]
        times = [pd.Period(t, 'H') for t in times.reshape(-1)]
        times = [(p.day_of_year/366, p.hour/24) for p in times]
        temb = np.array(times, dtype=np.float32)
        temb = np.concatenate([np.sin(temb), np.cos(temb)], axis=-1)
        temb = temb.reshape(1, -1)
        tembs.append(temb)
    return np.stack(tembs)


def load_model(model_name):
    # Set the behavier of onnxruntime
    options = ort.SessionOptions()
    options.enable_cpu_mem_arena=False
    options.enable_mem_pattern = False
    options.enable_mem_reuse = False
    # Increase the number for faster inference and more memory consumption
    options.intra_op_num_threads = 1
    cuda_provider_options = {'arena_extend_strategy':'kSameAsRequested',}

    session = ort.InferenceSession(
        model_name,  
        sess_options=options, 
        providers=[('CUDAExecutionProvider', cuda_provider_options)]
        # providers=[('CPUExecutionProvider')]
    )
    return session


def run_inference(model_dir, data, num_steps, save_dir=""):

    total_step = sum(num_steps)
    init_time = pd.to_datetime(data.time.values[-1])
    tembs = time_encoding(init_time, total_step)

    print(f'init_time: {init_time.strftime(("%Y%m%d-%H"))}')
    print(f'latitude: {data.lat.values[0]} ~ {data.lat.values[-1]}')
    
    assert data.lat.values[0] == 90
    assert data.lat.values[-1] == -90

    input = data.values[None]
    print(f'input: {input.shape}, {input.min():.2f} ~ {input.max():.2f}')
    print(f'tembs: {tembs.shape}, {tembs.mean():.4f}')

    stages = ['short', 'medium', 'long']
    step = 0

    s3_paths = []
    for i, num_step in enumerate(num_steps):
        stage = stages[i]
        start = time.perf_counter()
        model_name = os.path.join(model_dir, f"{stage}.onnx")
        print(f'Load model from {model_name} ...')        
        session = load_model(model_name)
        load_time = time.perf_counter() - start
        print(f'Load model take {load_time:.2f} sec')

        print(f'Inference {stage} ...')
        start = time.perf_counter()

        for _ in range(0, num_step):
            temb = tembs[step]
            print(f'stage: {i}, step: {step+1:02d}')
            new_input, = session.run(None, {'input': input, 'temb': temb})
            output = new_input[:, -1] 
            print(f'stage: {i}, step: {step+1:02d}, output: {output.min():.2f} {output.max():.2f}')
            save_name = save_like(output, data, step, save_dir='/tmp')
            s3_path = save_dir+'/'+save_name.split('/')[-1]
            upload_file_to_s3(save_name, s3_path)
            remove_file(save_name)
            s3_paths.append(s3_path)
            # print(f'stage: {i}, step: {step+1:02d}, output: {output.min():.2f} {output.max():.2f}')
            input = new_input
            step += 1

        run_time = time.perf_counter() - start
        print(f'Inference {stage} take {run_time:.2f}')

        if step > total_step:
            break
    return {'s3_paths': s3_paths}


def model_fn(model_dir):
    print("="*50)
    print("所有环境变量:")
    print("="*50)
    
    # 获取所有环境变量
    all_env_vars = dict(os.environ)
    
    # 分类显示
    sagemaker_vars = {}
    ts_vars = {}
    aws_vars = {}
    cuda_vars = {}
    other_vars = {}
    
    for key, value in all_env_vars.items():
        if key.startswith('SAGEMAKER_'):
            sagemaker_vars[key] = value
        elif key.startswith('TS_'):
            ts_vars[key] = value
        elif key.startswith('AWS_'):
            aws_vars[key] = value
        elif key.startswith('CUDA_'):
            cuda_vars[key] = value
        else:
            other_vars[key] = value
    
    print("\nSageMaker 变量:")
    for k, v in sorted(sagemaker_vars.items()):
        print(f"  {k}: {v}")
    
    print("\nTorchServe 变量:")
    for k, v in sorted(ts_vars.items()):
        print(f"  {k}: {v}")
    
    print("\nAWS 变量:")
    for k, v in sorted(aws_vars.items()):
        print(f"  {k}: {v}")
    
    print("\nCUDA 变量:")
    for k, v in sorted(cuda_vars.items()):
        print(f"  {k}: {v}")

    # 从环境变量获取S3配置，如果没有则使用默认值
    s3_bucket = os.environ.get('FUXI_MODEL_BUCKET', 'sagemaker-cn-northwest-1-YOUR_ACCOUNT_ID')
    s3_prefix = os.environ.get('FUXI_MODEL_PREFIX', 'sagemaker/fuxi')
    
    print(f"\n使用S3配置:")
    print(f"  存储桶: {s3_bucket}")
    print(f"  前缀: {s3_prefix}")
    
    model_dir = '/tmp'
    
    # 下载模型文件列表
    model_files = ['short', 'short.onnx', 'medium', 'medium.onnx', 'long', 'long.onnx']
    
    for model_file in model_files:
        s3_file_path = f's3://{s3_bucket}/{s3_prefix}/{model_file}'
        try:
            # 下载文件
            local_path = download_s3_file(s3_file_path, local_dir=model_dir)
            # 验证文件是否存在
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                print(f"文件已保存到: {local_path}")
                print(f"文件大小: {file_size:,} bytes")
        except Exception as e:
            print(f"下载模型文件 {model_file} 失败: {str(e)}")
            # 如果是关键的.onnx文件下载失败，抛出异常
            if model_file.endswith('.onnx'):
                raise Exception(f"关键模型文件 {model_file} 下载失败，无法继续推理")

    return model_dir


def input_fn(request_body, request_content_type):
    if request_content_type == 'application/json':
        request = json.loads(request_body)
        filename1 = request['filename1']
        filename2 = request['filename2']
        
        local_filename1 = download_s3_file(filename1)
        # 验证文件是否存在
        if os.path.exists(local_filename1):
            file_size = os.path.getsize(local_filename1)
            print(f"文件已保存到: {local_filename1}")
            print(f"文件大小: {file_size:,} bytes")

        local_filename2 = download_s3_file(filename2)
        # 验证文件是否存在
        if os.path.exists(local_filename2):
            file_size = os.path.getsize(local_filename2)
            print(f"文件已保存到: {local_filename2}")
            print(f"文件大小: {file_size:,} bytes")
            
        data1 = xr.open_dataarray(local_filename1)  # , engine='cfgrib'
        data2 = xr.open_dataset(local_filename2)  # , engine='cfgrib'
        
        return {'filename1': filename1, 'filename2': filename2, 'local_filename1': local_filename1, 'local_filename2': local_filename2, 'data1': data1, 'data2': data2}
    else:
        # Handle other content-types here or raise an Exception
        # if the content type is not supported.  
        return request_body

    
def predict_fn(input_data, model):
    print('[DEBUG] input_data:', input_data)
    data = input_data['data1']  # TODO 如果这里是两个文件，就传2个文件
    result = run_inference(model, data, num_steps, save_dir=input_data['filename1'][:-3]+'/result')
    remove_file(input_data['local_filename1'])
    remove_file(input_data['local_filename2'])
    print('[DEBUG] result:', result)
    
    return result


if __name__ == '__main__':
    model = model_fn('./')
    request_body = '{"filename1": "s3://datalab/goldwind/Sample_data/20231012-06_input_netcdf.nc", "filename2": "s3://datalab/goldwind/Sample_data/20231012-06_input_grib.nc"}'
    request_content_type = 'application/json'
    input_data = input_fn(request_body, request_content_type)
    result = predict_fn(input_data, model)
    print(result)
