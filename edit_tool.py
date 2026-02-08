#!/usr/bin/env python3
"""
编辑文件工具 - Claude 可以修改文件
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


def edit_file(input_data: Dict[str, Any]) -> Tuple[str, Optional[Exception]]:
    """编辑文件 - 替换 old_str 为 new_str"""
    try:
        path = input_data.get("path")
        old_str = input_data.get("old_str", "")
        new_str = input_data.get("new_str", "")

        if not path or old_str == new_str:
            return "", ValueError("invalid input parameters")

        # 如果文件不存在且 old_str 为空，创建新文件
        if not os.path.exists(path) and old_str == "":
            return create_new_file(path, new_str)

        # 读取文件
        with open(path, "r", encoding="utf-8") as f:
            old_content = f.read()

        # 如果 old_str 为空，追加内容
        if old_str == "":
            new_content = old_content + new_str
        else:
            # 检查 old_str 出现的次数
            count = old_content.count(old_str)
            if count == 0:
                return "", ValueError("old_str not found in file")
            if count > 1:
                return "", ValueError(f"old_str found {count} times in file, must be unique")

            new_content = old_content.replace(old_str, new_str, 1)

        # 写入文件
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return "OK", None
    except Exception as e:
        return "", e


def create_new_file(file_path: str, content: str) -> Tuple[str, Optional[Exception]]:
    """创建新文件"""
    try:
        dir_path = os.path.dirname(file_path)
        if dir_path and dir_path != ".":
            os.makedirs(dir_path, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully created file {file_path}", None
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

EditFileInputSchema = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "The path to the file"
        },
        "old_str": {
            "type": "string",
            "description": "Text to search for - must match exactly and must only have one match exactly"
        },
        "new_str": {
            "type": "string",
            "description": "Text to replace old_str with"
        }
    },
    "required": ["path", "old_str", "new_str"],
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

EditFileDefinition = ToolDefinition(
    name="edit_file",
    description="Make edits to a text file.\n\nReplaces 'old_str' with 'new_str' in the given file. 'old_str' and 'new_str' MUST be different from each other.\n\nIf the file specified with path doesn't exist, it will be created.",
    input_schema=EditFileInputSchema,
    function=edit_file
)


def main():
    parser = argparse.ArgumentParser(description="Chat with Claude - File Reading, Listing, Bash, and Editing Tools")
    parser.add_argument("--verbose", action="store_true", help="enable verbose logging")
    args = parser.parse_args()

    client = Anthropic()
    if args.verbose:
        print("Anthropic client initialized", file=sys.stderr)

    tools = [ReadFileDefinition, ListFilesDefinition, BashDefinition, EditFileDefinition]
    if args.verbose:
        print(f"Initialized {len(tools)} tools", file=sys.stderr)

    agent = Agent(client, tools, args.verbose)
    agent.run()


if __name__ == "__main__":
    main()

