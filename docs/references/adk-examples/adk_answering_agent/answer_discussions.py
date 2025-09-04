# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import asyncio
import sys
import time

from adk_answering_agent import agent
from adk_answering_agent.settings import OWNER
from adk_answering_agent.settings import REPO
from adk_answering_agent.utils import call_agent_async
from adk_answering_agent.utils import run_graphql_query
from google.adk.runners import InMemoryRunner
import requests

APP_NAME = "adk_discussion_answering_app"
USER_ID = "adk_discussion_answering_assistant"


async def list_most_recent_discussions(count: int = 1) -> list[int] | None:
  """取得指定數量的最近更新的討論。

  Args:
      count: 要檢索的討論數量。預設為 1。

  Returns:
      一個包含討論編號的列表。
  """
  print(
      f"正在嘗試從 {OWNER}/{REPO} 取得 {count} 個最近更新的討論..."
  )

  query = """
    query($owner: String!, $repo: String!, $count: Int!) {
      repository(owner: $owner, name: $repo) {
        discussions(
          first: $count
          orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
          nodes {
            title
            number
            updatedAt
            author {
              login
            }
          }
        }
      }
    }
    """
  variables = {"owner": OWNER, "repo": REPO, "count": count}

  try:
    response = run_graphql_query(query, variables)

    if "errors" in response:
      print(f"GitHub API 錯誤：{response['errors']}", file=sys.stderr)
      return None

    discussions = (
        response.get("data", {})
        .get("repository", {})
        .get("discussions", {})
        .get("nodes", [])
    )
    return [d["number"] for d in discussions]

  except requests.exceptions.RequestException as e:
    print(f"請求失敗：{e}", file=sys.stderr)
    return None


def process_arguments():
  """解析命令列參數。"""
  parser = argparse.ArgumentParser(
      description="一個為 Github 討論回答問題的腳本。",
      epilog=(
          "使用範例：\n"
          "\tpython -m adk_answering_agent.answer_discussions --recent 10\n"
          "\tpython -m adk_answering_agent.answer_discussions --numbers 21 31\n"
      ),
      formatter_class=argparse.RawTextHelpFormatter,
  )

  group = parser.add_mutually_exclusive_group(required=True)

  group.add_argument(
      "--recent",
      type=int,
      metavar="COUNT",
      help="回答 N 個最近更新的討論編號。",
  )

  group.add_argument(
      "--numbers",
      type=int,
      nargs="+",
      metavar="NUM",
      help="回答指定的討論編號列表。",
  )

  if len(sys.argv) == 1:
    parser.print_help(sys.stderr)
    sys.exit(1)

  return parser.parse_args()


async def main():
  args = process_arguments()
  discussion_numbers = []

  if args.recent:
    discussion_numbers = await list_most_recent_discussions(count=args.recent)
  elif args.numbers:
    discussion_numbers = args.numbers

  if not discussion_numbers:
    print("未指定討論。正在結束...", file=sys.stderr)
    sys.exit(1)

  print(f"將嘗試回答以下討論：{discussion_numbers}...")

  runner = InMemoryRunner(
      agent=agent.root_agent,
      app_name=APP_NAME,
  )

  for discussion_number in discussion_numbers:
    print("#" * 80)
    print(f"開始處理討論 #{discussion_number}...")
    # 為每個討論建立一個新會話以避免干擾。
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID
    )
    prompt = (
        f"請檢查討論 #{discussion_number}，看看您是否可以協助回答問題或提供一些資訊！"
    )
    response = await call_agent_async(runner, USER_ID, session.id, prompt)
    print(f"<<<< 代理最終輸出：{response}\n")


if __name__ == "__main__":
  start_time = time.time()
  print(
      f"開始為 {OWNER}/{REPO} 的討論回答問題，開始時間："
      f" {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(start_time))}"
  )
  print("-" * 80)
  asyncio.run(main())
  print("-" * 80)
  end_time = time.time()
  print(
      "討論回答完成於"
      f" {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(end_time))}",
  )
  print("腳本總執行時間：", f"{end_time - start_time:.2f} 秒")
