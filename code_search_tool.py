#!/usr/bin/env python3
"""
代码搜索工具 - 使用 ripgrep 搜索代码模式
"""

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, Any, Callable, Tuple, Optional
from anthropic import Anthropic
from dataclasses import dataclass


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    function: Callable[[Dict[str, Any]], Tuple[str, Optional[Exception]]]


class Agent:
    def __init__(self, client: Anthropic, tools: list[ToolDefinition], verbose: bool = False):
        self.client = client
        self.tools = tools
        self.verbose = verbose

    def run(self):
        conversation = []

        if self.verbose:
            print("Starting chat session with tools enabled", file=sys.stderr)

        print("Chat with Claude (use 'ctrl-c' to quit)")

        while True:
            try:
                print("\033[94mYou\033[0m: ", end="", flush=True)
                user_input = input()
            except (EOFError, KeyboardInterrupt):
                if self.verbose:
                    print("User input ended, breaking from chat loop", file=sys.stderr)
                break

            # Skip empty messages
            if not user_input.strip():
                if self.verbose:
                    print("Skipping empty message", file=sys.stderr)
                continue

            if self.verbose:
                print(f'User input received: "{user_input}"', file=sys.stderr)

            conversation.append({
                "role": "user",
                "content": user_input
            })

            if self.verbose:
                print(f"Sending message to Claude, conversation length: {len(conversation)}", file=sys.stderr)

            message = self.run_inference(conversation)
            if message is None:
                return

            conversation.append({
                "role": "assistant",
                "content": message["content"]
            })

            # Keep processing until Claude stops using tools
            while True:
                tool_results = []
                has_tool_use = False

                if self.verbose:
                    print(f"Processing {len(message['content'])} content blocks from Claude", file=sys.stderr)

                for content in message["content"]:
                    if content["type"] == "text":
                        print(f"\033[93mClaude\033[0m: {content['text']}")
                    elif content["type"] == "tool_use":
                        has_tool_use = True
                        tool_use = content
                        tool_name = tool_use["name"]
                        tool_input = tool_use["input"]

                        if self.verbose:
                            print(f"Tool use detected: {tool_name} with input: {json.dumps(tool_input)}", file=sys.stderr)

                        print(f"\033[96mtool\033[0m: {tool_name}({json.dumps(tool_input)})")

                        # Find and execute the tool
                        tool_result = None
                        tool_error = None
                        tool_found = False

                        for tool in self.tools:
                            if tool.name == tool_name:
                                if self.verbose:
                                    print(f"Executing tool: {tool.name}", file=sys.stderr)

                                try:
                                    tool_result, tool_error = tool.function(tool_input)
                                    print(f"\033[92mresult\033[0m: {tool_result}")
                                    if tool_error:
                                        print(f"\033[91merror\033[0m: {tool_error}", file=sys.stderr)
                                except Exception as e:
                                    tool_error = str(e)
                                    print(f"\033[91merror\033[0m: {tool_error}")

                                if self.verbose:
                                    if tool_error:
                                        print(f"Tool execution failed: {tool_error}", file=sys.stderr)
                                    else:
                                        print(f"Tool execution successful, result length: {len(tool_result)} chars", file=sys.stderr)

                                tool_found = True
                                break

                        if not tool_found:
                            tool_error = f"tool '{tool_name}' not found"
                            print(f"\033[91merror\033[0m: {tool_error}")

                        # Add tool result to collection
                        if tool_error:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use["id"],
                                "content": tool_error,
                                "is_error": True
                            })
                        else:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use["id"],
                                "content": tool_result,
                                "is_error": False
                            })

                # If there were no tool uses, we're done
                if not has_tool_use:
                    break

                # Send all tool results back and get Claude's response
                if self.verbose:
                    print(f"Sending {len(tool_results)} tool results back to Claude", file=sys.stderr)

                conversation.append({
                    "role": "user",
                    "content": tool_results
                })

                # Get Claude's response after tool execution
                message = self.run_inference(conversation)
                if message is None:
                    return

                conversation.append({
                    "role": "assistant",
                    "content": message["content"]
                })

                if self.verbose:
                    print(f"Received followup response with {len(message['content'])} content blocks", file=sys.stderr)

        if self.verbose:
            print("Chat session ended", file=sys.stderr)

    def run_inference(self, conversation):
        anthropic_tools = []
        for tool in self.tools:
            anthropic_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })

        if self.verbose:
            print(f"Making API call to Claude with model: claude-3-7-sonnet-20250219 and {len(anthropic_tools)} tools", file=sys.stderr)

        try:
            message = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1024,
                messages=conversation,
                tools=anthropic_tools
            )

            if self.verbose:
                print("API call successful, response received", file=sys.stderr)

            content = []
            for block in message.content:
                if block.type == "text":
                    content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })

            return {"content": content}
        except Exception as e:
            if self.verbose:
                print(f"API call failed: {e}", file=sys.stderr)
            print(f"Error: {e}")
            return None


def read_file(input_data: Dict[str, Any]) -> Tuple[str, Optional[Exception]]:
    """读取文件内容"""
    try:
        path = input_data.get("path")
        if not path:
            return "", ValueError("path is required")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return content, None
    except Exception as e:
        return "", e


def list_files(input_data: Dict[str, Any]) -> Tuple[str, Optional[Exception]]:
    """列出目录中的文件和文件夹"""
    try:
        dir_path = input_data.get("path", ".")
        if not dir_path:
            dir_path = "."

        files = []
        for root, dirs, filenames in os.walk(dir_path):
            # Skip .devenv directory
            if ".devenv" in dirs:
                dirs.remove(".devenv")

            rel_root = os.path.relpath(root, dir_path)
            if rel_root == ".":
                rel_root = ""

            for d in dirs:
                rel_path = os.path.join(rel_root, d) if rel_root else d
                files.append(rel_path + "/")

            for f in filenames:
                rel_path = os.path.join(rel_root, f) if rel_root else f
                files.append(rel_path)

        result = json.dumps(files, ensure_ascii=False)
        return result, None
    except Exception as e:
        return "", e


def bash(input_data: Dict[str, Any]) -> Tuple[str, Optional[Exception]]:
    """执行 bash 命令"""
    try:
        command = input_data.get("command")
        if not command:
            return "", ValueError("command is required")

        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = f"Command failed with error: {result.stderr}\nOutput: {result.stdout}"
            return error_msg, None

        return result.stdout.strip(), None
    except subprocess.TimeoutExpired:
        return "", TimeoutError("Command timed out after 30 seconds")
    except Exception as e:
        return "", e


def code_search(input_data: Dict[str, Any]) -> Tuple[str, Optional[Exception]]:
    """使用 ripgrep 搜索代码模式"""
    try:
        pattern = input_data.get("pattern")
        if not pattern:
            return "", ValueError("pattern is required")

        path = input_data.get("path", ".")
        file_type = input_data.get("file_type", "")
        case_sensitive = input_data.get("case_sensitive", False)

        # 构建 ripgrep 命令
        args = ["rg", "--line-number", "--with-filename", "--color=never"]

        # 添加大小写敏感标志
        if not case_sensitive:
            args.append("--ignore-case")

        # 添加文件类型过滤
        if file_type:
            args.extend(["--type", file_type])

        # 添加搜索模式
        args.append(pattern)

        # 添加路径
        args.append(path)

        # 执行 ripgrep
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30
        )

        # ripgrep 返回退出码 1 表示没有找到匹配，这不是错误
        if result.returncode == 1:
            return "No matches found", None
        elif result.returncode != 0:
            return "", ValueError(f"search failed: {result.stderr}")

        output = result.stdout.strip()
        lines = output.split("\n") if output else []

        # 限制输出以防止响应过大
        if len(lines) > 50:
            output = "\n".join(lines[:50]) + f"\n... (showing first 50 of {len(lines)} matches)"

        return output, None
    except subprocess.TimeoutExpired:
        return "", TimeoutError("Search timed out after 30 seconds")
    except FileNotFoundError:
        return "", ValueError("ripgrep (rg) not found. Please install ripgrep first.")
    except Exception as e:
        return "", e


# 工具定义
ReadFileInputSchema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "The relative path of a file in the working directory."
        }
    },
    "required": ["path"],
    "additionalProperties": False
}

ListFilesInputSchema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Optional relative path to list files from. Defaults to current directory if not provided."
        }
    },
    "additionalProperties": False
}

BashInputSchema = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "The bash command to execute."
        }
    },
    "required": ["command"],
    "additionalProperties": False
}

CodeSearchInputSchema = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "The search pattern or regex to look for"
        },
        "path": {
            "type": "string",
            "description": "Optional path to search in (file or directory)"
        },
        "file_type": {
            "type": "string",
            "description": "Optional file extension to limit search to (e.g., 'go', 'js', 'py')"
        },
        "case_sensitive": {
            "type": "boolean",
            "description": "Whether the search should be case sensitive (default: false)"
        }
    },
    "required": ["pattern"],
    "additionalProperties": False
}

ReadFileDefinition = ToolDefinition(
    name="read_file",
    description="Read the contents of a given relative file path. Use this when you want to see what's inside a file. Do not use this with directory names.",
    input_schema=ReadFileInputSchema,
    function=read_file
)

ListFilesDefinition = ToolDefinition(
    name="list_files",
    description="List files and directories at a given path. If no path is provided, lists files in the current directory.",
    input_schema=ListFilesInputSchema,
    function=list_files
)

BashDefinition = ToolDefinition(
    name="bash",
    description="Execute a bash command and return its output. Use this to run shell commands.",
    input_schema=BashInputSchema,
    function=bash
)

CodeSearchDefinition = ToolDefinition(
    name="code_search",
    description="Search for code patterns using ripgrep (rg).\n\nUse this to find code patterns, function definitions, variable usage, or any text in the codebase.\nYou can search by pattern, file type, or directory.",
    input_schema=CodeSearchInputSchema,
    function=code_search
)


def main():
    parser = argparse.ArgumentParser(description="Chat with Claude - File Reading, Listing, Bash, and Code Search Tools")
    parser.add_argument("--verbose", action="store_true", help="enable verbose logging")
    args = parser.parse_args()

    client = Anthropic()
    if args.verbose:
        print("Anthropic client initialized", file=sys.stderr)

    tools = [ReadFileDefinition, ListFilesDefinition, BashDefinition, CodeSearchDefinition]
    if args.verbose:
        print(f"Initialized {len(tools)} tools", file=sys.stderr)

    agent = Agent(client, tools, args.verbose)
    agent.run()


if __name__ == "__main__":
    main()

