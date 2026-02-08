# Python 版本的编码助手

这是 [https://github.com/ghuntley/how-to-build-a-coding-agent](https://github.com/ghuntley/how-to-build-a-coding-agent) 编码助手的 Python 实现。逐步构建一个功能强大的 AI 编码助手。

## 功能特性

本项目包含 6 个逐步增强的版本：

1. **chat.py** - 基础聊天功能
2. **read.py** - 添加文件读取工具
3. **list_files.py** - 添加文件列表工具
4. **bash_tool.py** - 添加 bash 命令执行工具
5. **edit_tool.py** - 添加文件编辑工具
6. **code_search_tool.py** - 添加代码搜索工具（使用 ripgrep）

## 安装

### 前置要求

- Python 3.8+
- LLM API Key

### 安装依赖

```bash
pip install -r requirements.txt
```

### 设置 API Key 和 BASE URL, MODEL_NAME

MODEL_NAME默认使用 glm-4.7
在.env文件中设置
```
API_KEY=your-api-key-here
BASE_URL=base-url-here
MODEL_NAME=glm-4.7
```

或者在代码中直接设置（不推荐用于生产环境）：

```python
from anthropic import Anthropic
client = Anthropic(api_key="your-api-key-here", base_url="base-url-here")
```

## 使用方法

### 1. 基础聊天 (chat.py)

```bash
python chat.py
```

或启用详细日志：

```bash
python chat.py --verbose
```

### 2. 文件读取 (read.py)

```bash
python read.py
```

尝试："读取 README.md"

### 3. 文件列表 (list_files.py)

```bash
python list_files.py
```

尝试："列出当前目录的所有文件"

### 4. Bash 命令 (bash_tool.py)

```bash
python bash_tool.py
```

尝试："运行 git status"

### 5. 文件编辑 (edit_tool.py)

```bash
python edit_tool.py
```

尝试："创建一个 Python hello world 脚本"

### 6. 代码搜索 (code_search_tool.py)

```bash
python code_search_tool.py
```

**注意**: 代码搜索功能需要安装 ripgrep：

```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
sudo apt-get install ripgrep

# 或使用 cargo
cargo install ripgrep
```

尝试："查找所有 Python 文件中的函数定义"

## 代码结构

每个文件都包含：

- `Agent` 类：管理对话和工具执行
- `ToolDefinition` 数据类：定义工具的结构
- 工具函数：实现具体的工具功能
- `main` 函数：程序入口点


## 故障排除

**API key 不工作？**

- 确保已添加正确的 api_key 和 base_url，可以再代码中打印 print(API_KEY)
- 检查 [Anthropic 控制台](https://www.anthropic.com) 中的配额

**Python 错误？**

- 确保使用 Python 3.8+
- 运行 `pip install -r requirements.txt`

**工具错误？**

- 使用 `--verbose` 查看详细日志
- 检查文件路径和权限

**代码搜索不工作？**

- 确保已安装 ripgrep：`which rg`
- 如果未安装，请按照上面的说明安装


## TODO

- 实现 ReAct 框架：添加思考-行动-观察循环机制
- 构建安全沙盒：隔离 Bash 执行环境，添加权限控制
- 增强代码能力：添加代码生成、编辑、格式化工具
- 实现状态管理：添加会话持久化和上下文记忆
- 集成测试环境：支持代码测试和验证