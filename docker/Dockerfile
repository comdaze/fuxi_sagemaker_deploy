# 基于AWS SageMaker PyTorch推理镜像
FROM 727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn/pytorch-inference:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker

# 设置工作目录
WORKDIR /opt/ml/code

# 设置环境变量
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/ml/code:${PATH}"

# 更新系统包并安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    vim \
    htop \
    libeccodes0 \
    libeccodes-dev \
    libnetcdf-dev \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# 升级pip并设置清华源
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 复制实际的requirements文件
COPY requirements.txt /opt/ml/code/requirements.txt

# 安装FuXi模型的核心依赖（使用清华源加速）
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    onnx==1.16.0 \
    onnxruntime-gpu==1.18.1 \
    xarray \
    cfgrib \
    h5netcdf \
    numpy==1.26.4

# 安装其他常用的科学计算库（使用清华源）
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    pandas \
    scipy \
    netcdf4 \
    eccodes \
    boto3 \
    botocore \
    python-dateutil \
    pytz \
    tqdm

# 设置CUDA环境变量
ENV CUDA_VISIBLE_DEVICES=0
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# 创建必要的目录
RUN mkdir -p /opt/ml/model
RUN mkdir -p /tmp

# 设置权限
RUN chmod -R 755 /opt/ml/code

# 预热ONNX Runtime GPU
RUN python -c "import onnxruntime as ort; print('ONNX Runtime providers:', ort.get_available_providers())"

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import torch; import onnxruntime; import xarray; import cfgrib; print('All dependencies OK')" || exit 1

# 默认命令
CMD ["python", "/opt/ml/code/inference.py"]
