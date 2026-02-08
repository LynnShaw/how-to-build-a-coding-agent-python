# Python-based Coding Assistant
[中文版说明](readme_cn.md)

This is a Python implementation of the coding assistant from [https://github.com/ghuntley/how-to-build-a-coding-agent](https://github.com/ghuntley/how-to-build-a-coding-agent). We build a powerful AI coding assistant step by step.

## Features

This project includes 6 progressively enhanced versions:

1. **chat.py** - Basic chat functionality
2. **read.py** - Add file reading tool
3. **list_files.py** - Add file listing tool
4. **bash_tool.py** - Add bash command execution tool
5. **edit_tool.py** - Add file editing tool
6. **code_search_tool.py** - Add code search tool (using ripgrep)

## Installation

### Prerequisites

- Python 3.8+
- LLM API Key

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Set API Key, BASE URL, and MODEL_NAME

The default MODEL_NAME is glm-4.7.  
Set these values in the .env file:
```
API_KEY=your-api-key-here
BASE_URL=base-url-here
MODEL_NAME=glm-4.7
```

Alternatively, set them directly in the code (**not recommended for production environments**):

```python
from anthropic import Anthropic
client = Anthropic(api_key="your-api-key-here", base_url="base-url-here")
```

## Usage

### 1. Basic Chat (chat.py)

```bash
python chat.py
```

Or enable verbose logging:

```bash
python chat.py --verbose
```

### 2. File Reading (read.py)

```bash
python read.py
```

Try: "Read README.md"

### 3. File Listing (list_files.py)

```bash
python list_files.py
```

Try: "List all files in the current directory"

### 4. Bash Commands (bash_tool.py)

```bash
python bash_tool.py
```

Try: "Run git status"

### 5. File Editing (edit_tool.py)

```bash
python edit_tool.py
```

Try: "Create a Python hello world script"

### 6. Code Search (code_search_tool.py)

```bash
python code_search_tool.py
```

**Note**: The code search feature requires ripgrep to be installed:

```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
sudo apt-get install ripgrep

# Or using cargo
cargo install ripgrep
```

Try: "Find all function definitions in Python files"

## Code Structure

Each file contains:

- `Agent` class: Manages conversations and tool execution
- `ToolDefinition` dataclass: Defines the structure of tools
- Tool functions: Implement specific tool functionalities
- `main` function: Program entry point

## Tool Descriptions

### read_file

Reads the content of a file.

**Input**:
- `path` (string): File path

### list_files

Lists files and folders in a directory.

**Input**:
- `path` (string, optional): Directory path, defaults to the current directory

### bash

Executes bash commands.

**Input**:
- `command` (string): Command to execute

### edit_file

Edits a file by replacing `old_str` with `new_str`.

**Input**:
- `path` (string): File path
- `old_str` (string): Text to be replaced
- `new_str` (string): Replacement text

### code_search

Searches code patterns using ripgrep.

**Input**:
- `pattern` (string): Search pattern or regular expression
- `path` (string, optional): Search path
- `file_type` (string, optional): File type filter (e.g., 'py', 'js', 'go')
- `case_sensitive` (boolean, optional): Case sensitivity, defaults to false

## Troubleshooting

**API key not working?**

- Ensure you have added the correct api_key and base_url, you can print them in code with print(API_KEY)
- Check your quota in the [Anthropic Console](https://www.anthropic.com)

**Python errors?**

- Ensure you are using Python 3.8+
- Run `pip install -r requirements.txt`

**Tool errors?**

- Use `--verbose` to view detailed logs
- Check file paths and permissions

**Code search not working?**

- Ensure ripgrep is installed: `which rg`
- If not installed, follow the installation instructions above

