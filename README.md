# FuXi Weather Model - SageMaker 部署项目

## 🌤️ 项目概述

这是一个基于 AWS SageMaker 的 FuXi 天气预报模型部署解决方案，专为金风慧能天气大模型项目设计。该项目提供了完整的端到端部署流程，包括自定义 Docker 镜像、批量推理任务、Lambda 自动触发和 S3 数据处理。

## 📁 项目结构

```
fuxi_sagemaker_deploy/
├── README.md                    # 项目说明文档（本文件）
├── DEPLOYMENT_GUIDE.md         # 详细部署指南
├── .DS_Store                   # macOS 系统文件
│
├── docker/                     # Docker 容器相关
│   ├── Dockerfile              # 自定义推理镜像定义
│   ├── requirements.txt        # Python 依赖包列表
│   ├── build.sh               # 镜像构建脚本
│   └── check_permissions.sh   # AWS 权限检查脚本
│
├── model/                      # 模型推理代码
│   ├── inference.py           # SageMaker 推理入口点
│   ├── util.py               # 工具函数库
│   └── model.tar.gz          # 打包的模型文件
│
├── lambda/                     # AWS Lambda 函数
│   └── function.py            # S3 事件触发的 Lambda 处理函数
│
├── scripts/                    # 部署和管理脚本
│   ├── deploy.py              # 主部署脚本（包含 IAM 角色创建）
│   └── setup_models.sh        # 模型文件设置脚本
│
├── docs/                       # 文档目录
│   ├── PERMISSIONS.md         # 权限配置说明
│   ├── TROUBLESHOOTING.md     # 故障排除指南
│   └── MODEL_MANAGEMENT.md    # 模型管理指南
│
└── fuxi_models/               # FuXi 模型文件目录（需要手动添加）
    ├── short.onnx            # 短期预测模型（1-5天）
    ├── medium.onnx           # 中期预测模型（6-10天）
    ├── long.onnx             # 长期预测模型（11-15天）
    ├── short                 # 短期模型配置
    ├── medium                # 中期模型配置
    └── long                  # 长期模型配置
```

## 🛠️ 技术栈

### 核心技术
- **云平台**: AWS China (宁夏区域 cn-northwest-1)
- **机器学习**: Amazon SageMaker
- **容器化**: Docker + Amazon ECR
- **无服务器**: AWS Lambda
- **存储**: Amazon S3
- **权限管理**: AWS IAM

### 编程语言和框架
- **Python 3.10**: 主要开发语言
- **PyTorch 2.0.1**: 深度学习框架
- **ONNX Runtime GPU 1.18.1**: 模型推理引擎
- **Boto3**: AWS SDK for Python

### 科学计算库
- **NumPy 1.26.4**: 数值计算
- **XArray**: 多维数组处理
- **Pandas**: 数据分析
- **SciPy**: 科学计算
- **NetCDF4**: 气象数据格式支持

### 气象数据处理
- **cfgrib**: GRIB 格式数据读取
- **h5netcdf**: HDF5/NetCDF 数据处理
- **eccodes**: ECMWF 编码库

## 📦 依赖管理

### Python 核心依赖 (requirements.txt)
```
onnx==1.16.0                    # ONNX 模型格式支持
onnxruntime-gpu==1.18.1         # GPU 加速推理引擎
xarray                          # 多维数组数据结构
cfgrib                          # GRIB 气象数据格式
h5netcdf                        # NetCDF 数据格式
numpy==1.26.4                   # 数值计算基础库
```

### 系统级依赖
```bash
# 气象数据处理库
libeccodes0, libeccodes-dev     # ECMWF 编码库
libnetcdf-dev                   # NetCDF 开发库
libhdf5-dev                     # HDF5 开发库

# 系统工具
wget, curl, vim, htop           # 基础系统工具
```

### Docker 基础镜像
```
FROM 727897471807.dkr.ecr.cn-northwest-1.amazonaws.com.cn/pytorch-inference:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker
```

## 🏗️ 系统架构

### 数据流程
1. **数据输入**: 气象数据上传到 S3 存储桶
2. **事件触发**: S3 `_SUCCESS` 文件触发 Lambda 函数
3. **批量推理**: Lambda 启动 SageMaker 批量转换任务
4. **模型推理**: 使用自定义 Docker 镜像进行 FuXi 模型推理
5. **结果输出**: 预测结果保存到 S3 指定路径

### 核心组件
- **自定义 Docker 镜像**: 预装所有依赖，支持 GPU 加速
- **SageMaker 模型**: 托管的 FuXi 天气预报模型
- **Lambda 触发器**: 自动化批量推理任务启动
- **IAM 角色**: 自动创建和配置必要的权限

## 🚀 快速开始

### 前置要求
1. AWS CLI 已配置（中国区域）
2. Docker 已安装
3. 必要的 AWS 权限（ECR、SageMaker、Lambda、S3、IAM）
4. FuXi 模型文件已准备

### 部署步骤

1. **检查权限**
   ```bash
   cd docker
   ./check_permissions.sh YOUR_ACCOUNT_ID
   ```

2. **构建 Docker 镜像**
   ```bash
   ./build.sh YOUR_ACCOUNT_ID
   ```

3. **设置模型文件**
   ```bash
   cd ../scripts
   ./setup_models.sh YOUR_BUCKET_NAME
   ```

4. **执行部署**
   ```bash
   python deploy.py \
       --account-id YOUR_ACCOUNT_ID \
       --bucket YOUR_BUCKET_NAME \
       --environment prod
   ```

## 🔧 配置说明

### 环境变量
- `FUXI_MODEL_BUCKET`: 模型存储桶名称
- `FUXI_MODEL_PREFIX`: 模型 S3 前缀路径
- `MODEL_NAME`: SageMaker 模型名称
- `INSTANCE_TYPE`: 推理实例类型（默认: ml.g4dn.2xlarge）

### 资源命名规范
- SageMaker 模型: `fuxi-weather-model-{environment}`
- Lambda 函数: `fuxi-weather-lambda-{environment}`
- ECR 仓库: `fuxi-weather-inference`
- IAM 角色: `FuXiSageMakerExecutionRole`, `FuXiLambdaExecutionRole`

## 📊 模型信息

### FuXi 模型特点
- **短期预测** (short.onnx): 1-5 天天气预报
- **中期预测** (medium.onnx): 6-10 天天气预报  
- **长期预测** (long.onnx): 11-15 天天气预报

### 推理性能
- **GPU 加速**: 支持 NVIDIA CUDA
- **批量处理**: SageMaker 批量转换任务
- **自动扩缩**: 根据数据量自动调整实例

## 🔍 监控和调试

### 检查部署状态
```bash
# SageMaker 模型状态
aws sagemaker describe-model --model-name fuxi-weather-model-prod

# Lambda 函数状态
aws lambda get-function --function-name fuxi-weather-lambda-prod

# ECR 镜像列表
aws ecr describe-images --repository-name fuxi-weather-inference
```

### 日志查看
```bash
# Lambda 函数日志
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/fuxi-weather

# SageMaker 任务日志
aws sagemaker describe-transform-job --transform-job-name JOB_NAME
```

## 📚 文档链接

- [详细部署指南](DEPLOYMENT_GUIDE.md)
- [权限配置说明](docs/PERMISSIONS.md)
- [故障排除指南](docs/TROUBLESHOOTING.md)
- [模型管理指南](docs/MODEL_MANAGEMENT.md)

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

**注意**: 本项目专为 AWS 中国区域设计，使用前请确保已正确配置中国区域的 AWS 访问权限。
