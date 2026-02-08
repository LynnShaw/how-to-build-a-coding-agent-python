#!/usr/bin/env python3
"""
基础聊天功能 - 与 LLM 进行简单对话
"""

import argparse
import sys
from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()
BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "glm-4.7")

class Agent:
    def __init__(self, client: Anthropic, verbose: bool = False):
        self.client = client
        self.verbose = verbose

    def run(self):
        conversation = []

        if self.verbose:
            print("Starting chat session", file=sys.stderr)

        print("Chat with LLM (use 'ctrl-c' to quit)")

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
                print(f"Sending message to LLM, conversation length: {len(conversation)}", file=sys.stderr)

            message = self.run_inference(conversation)
            if message is None:
                return

            conversation.append({
                "role": "assistant",
                "content": message["content"]
            })

            if self.verbose:
                print(f"Received response from LLM with {len(message['content'])} content blocks", file=sys.stderr)

            for content in message["content"]:
                if content["type"] == "text":
                    print(f"\033[93m{MODEL_NAME}\033[0m: {content['text']}")

        if self.verbose:
            print("Chat session ended", file=sys.stderr)

    def run_inference(self, conversation):
        if self.verbose:
            print(f"Making API call to LLM with model: {MODEL_NAME}", file=sys.stderr)

        try:
            message = self.client.messages.create(
                model=MODEL_NAME,
                max_tokens=1024,
                messages=conversation
            )

            if self.verbose:
                print("API call successful, response received", file=sys.stderr)

            return {
                "content": [
                    {"type": "text", "text": block.text}
                    for block in message.content
                    if block.type == "text"
                ]
            }
        except Exception as e:
            if self.verbose:
                print(f"API call failed: {e}", file=sys.stderr)
            print(f"Error: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="Chat with LLM")
    parser.add_argument("--verbose", action="store_true", help="enable verbose logging")
    args = parser.parse_args()

    client = Anthropic(
        api_key=API_KEY,
        base_url=BASE_URL,
    )
    if args.verbose:
        print("Anthropic client initialized", file=sys.stderr)

    agent = Agent(client, args.verbose)
    agent.run()


if __name__ == "__main__":
    main()

