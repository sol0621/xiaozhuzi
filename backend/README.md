# 小学作业辅导助手 - 后端配置说明

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入你的配置
python main.py
```

服务默认运行在：`http://localhost:8000`

---

## 1. 大模型配置（批改与讲解）

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_API_KEY` | 你的 API Key | `sk-xxxx` |
| `LLM_BASE_URL` | 模型服务地址（**不要带末尾斜杠**） | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |

### 常见平台参考

- **DeepSeek 官方**
  ```bash
  LLM_BASE_URL=https://api.deepseek.com/v1
  LLM_MODEL=deepseek-chat
  ```

- **自建 vLLM / Ollama / OneAPI**
  ```bash
  LLM_BASE_URL=http://localhost:8000/v1
  LLM_MODEL=your-model-name
  ```

- **硅基流动 SiliconFlow**
  ```bash
  LLM_BASE_URL=https://api.siliconflow.cn/v1
  LLM_MODEL=deepseek-ai/DeepSeek-V3
  ```

### 模型能力要求

本应用依赖 LLM 的以下能力：

1. **JSON 输出**：支持 `response_format={"type":"json_object"}`（主流模型都支持）。
   - 如果不支持，注释掉 `main.py` 中的 `payload["response_format"]` 行即可。
2. **中文理解**：能准确理解小学语文、数学、英语、科学题目。
3. **图片输入（可选）**：如果你的模型本身支持图片，可以不配 OCR。如果不支持，请务必配置下文的百度 OCR。

---

## 2. 百度 OCR 配置（免费图片识别）

> **为什么需要？** 如果你的大模型（如 kimi-k2.6）不支持图片输入，但你想用拍照上传功能，就需要一个"图片转文字"的中间层。百度 OCR 提供非常慷慨的免费额度。

### 免费额度（完全够用）

| 类型 | 接口 | 免费额度 |
|------|------|---------|
| 高精度版 | `accurate` | **500 次/天** |
| 标准版 | `general` | **50,000 次/天** |
| 手写版 | `handwriting` | **500 次/天** |

一个孩子的作业量，一天通常不超过 20 页，500 次/天绰绰有余。

### 获取步骤

1. 访问 [百度智能云 - 文字识别](https://cloud.baidu.com/doc/OCR/s/dk3iqnp51)
2. 登录/注册账号
3. 创建一个"通用文字识别"应用
4. 获得 **AppID、API Key、Secret Key**
5. 填入 `.env` 文件

```bash
BAIDU_OCR_APP_ID=12345678
BAIDU_OCR_API_KEY=xxxxxxxxxxxx
BAIDU_OCR_SECRET_KEY=yyyyyyyyyyyy

# 选择识别类型
BAIDU_OCR_TYPE=accurate   # 默认值，印刷体+清晰手写
# BAIDU_OCR_TYPE=general    # 印刷体为主，额度超大
# BAIDU_OCR_TYPE=handwriting # 手写为主
```

### 技术架构

```
用户拍照 → 后端接收图片 → 百度 OCR（免费）提取文字 → 文字传给大模型批改
```

这样你的纯文本大模型也能"批改作业照片"了，全程零成本。

---

## 3. 数据库

默认使用 SQLite，数据保存在 `homework.db`，无需额外配置。

---

## 4. 启动服务

```bash
# 开发模式（带热重载）
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 5. 接口文档

启动后访问：`http://localhost:8000/docs`（Swagger UI）

---

## 常见问题

**Q: 我不想配百度 OCR，能纯文字用吗？**  
A: 完全可以。不配置百度 OCR 时，文字输入模式不受影响。拍照模式会提示"请配置百度 OCR 或切换文字输入"。

**Q: 百度 OCR 识别手写答案不准怎么办？**  
A: 可以把 `BAIDU_OCR_TYPE` 改成 `handwriting`（手写识别专用）。或者让孩子写工整一些，拍清晰一些。

**Q: 我的模型本来就支持图片（如 DeepSeek-VL、Qwen-VL），还需要 OCR 吗？**  
A: 不需要。如果你的模型支持 `image_url` 类型的消息，可以直接走模型原生识别，无需配置百度 OCR。
