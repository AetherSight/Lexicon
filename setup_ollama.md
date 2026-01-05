# 本地Ollama设置指南（4090显卡）

## 推荐方案：本地Ollama运行

4090显卡（24GB显存）完全可以在本地运行qwen3-vl-thinking模型，推荐使用Ollama。

## 安装Ollama

1. 下载安装：https://ollama.com/download
2. 安装完成后，Ollama会自动启动服务（默认端口11434）

## 下载模型

```bash
# 下载qwen3-vl-thinking模型（推荐8B或14B版本）
ollama pull qwen3-vl-thinking

# 或者使用qwen2.5-vl（如果qwen3-vl-thinking不可用）
ollama pull qwen2.5-vl:latest
```

## 运行标注脚本

```bash
# 使用Poetry运行（推荐）
poetry run python -m lexicon \
    --image_dir "你的图片目录" \
    --equipment_type "上装" \
    --model "qwen3-vl-thinking:8b" \
    --max_concurrent 20  # 本地运行可以设置更高并发

# 或者如果已安装到系统
python -m lexicon \
    --image_dir "你的图片目录" \
    --equipment_type "上装" \
    --max_concurrent 20
```

## 性能优化建议

1. **并发数**：本地运行可以设置20-30，充分利用GPU
2. **模型选择**：
   - 8B模型：约7.4GB显存，速度快
   - 14B模型：约14GB显存，精度更高
   - 32B模型：可能超出24GB，需要量化
3. **批量大小**：可以增加到100-200

## 优势

✅ **速度快**：无网络延迟，4090推理速度很快  
✅ **隐私安全**：数据完全本地处理  
✅ **成本低**：无需API费用  
✅ **可控性强**：可以随时调整参数和模型版本

