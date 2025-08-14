# FuXi模型管理指南

## 📦 模型文件概述

FuXi天气预报模型需要以下文件：

### 必需文件

```
fuxi_models/
├── short.onnx          # 短期预测模型 (1-5天)
├── medium.onnx         # 中期预测模型 (6-10天)  
├── long.onnx           # 长期预测模型 (11-15天)
├── short               # 短期模型配置文件
├── medium              # 中期模型配置文件
└── long                # 长期模型配置文件
```

## 🚀 模型获取流程

### 1. 下载模型文件

**下载来源:**

- GitHub官方仓库: https://github.com/tpys/FuXi
- Zenodo数据仓库: https://zenodo.org/records/15762985
- 学术合作渠道

### 2. 上传到S3

```bash
cd fuxi_model
aws s3 sync . s3://YOUR_BUCKET_NAME/sagemaker/fuxi/
```

### 3. 验证模型文件

```bash
# 检查S3中的模型文件
aws s3 ls s3://YOUR_BUCKET_NAME/sagemaker/fuxi/ --recursive

# 验证ONNX模型完整性
python -c "
import onnx
model = onnx.load('../fuxi_models/short.onnx')
print('✅ short.onnx 文件完整')
"
```
