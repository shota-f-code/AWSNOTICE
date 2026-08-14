import json
import logging
import os
import urllib.parse
import urllib.request

import boto3

# ログ設定：Lambda標準ロガーの出力レベルをINFOに設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 1.環境変数の読み込み
BACKLOG_API_KEY = os.environ.get("BACKLOG_API_KEY")
BACKLOG_ISSUE_TYPE_ID = os.environ.get("BACKLOG_ISSUE_TYPE_ID")
BACKLOG_PROJECT_ID = os.environ.get("BACKLOG_PROJECT_ID")
BACKLOG_SPACE_ID = os.environ.get("BACKLOG_SPACE_ID")
BACKLOG_USER_ID = os.environ.get("BACKLOG_USER_ID")

# Bedrockクライアントの初期化（関数の外で定義して再利用）
bedrock_runtime = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")

def summary_bedrock(health_text: str) -> str:
    """Bedrock (Claude) を呼び出して通知内容を要約する関数"""
    # 1. プロンプトの組み立て
    prompt_content = f"""
以下のAWS Health通知の内容を読み、日本語で分かりやすく要約して指定のフォーマットで出力（Backlog記法）してください。

【出力フォーマット】
** 概要
** 緊急度
** 対応策

【出力ルール】
・独自のタイトルや前置き、結びの言葉は一切含めず、必ず「** 概要」から書き始めてください。
・フォーマットの見出し記号（** ）は変更しないでください。

【通知内容】
{health_text}
"""
    # 2. リクエストボディの組み立て
    model_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt_content}],
            "temperature": 0.5,
        }
    )

    # 3. Bedrock APIの呼び出しとレスポンス解析
    response = bedrock_runtime.invoke_model(modelId=model_id, body=body)
    response_body = json.loads(response.get("body").read())
    return response_body.get("content")[0].get("text")

def notify_backlog(summary: str, description: str) -> None:
    """Backlog API を叩いて課題を作成する関数"""
    # 1. リクエストURLおよびペイロードの組み立て
    url = f"https://{BACKLOG_SPACE_ID}.backlog.com/api/v2/issues?apiKey={BACKLOG_API_KEY}"
    payload = {
        "projectId": BACKLOG_PROJECT_ID,
        "summary": summary,
        "issueTypeId": BACKLOG_ISSUE_TYPE_ID,
        "priorityId": "3",
        "description": description,
    }
    if BACKLOG_USER_ID:
        payload["notifiedUserId[]"] = BACKLOG_USER_ID

    # 2. HTTPリクエストオブジェクトの生成
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    # 3. APIリクエストの送信
    logger.info("Sending issue to Backlog...")
    with urllib.request.urlopen(req) as response:
        logger.info("Backlog notification succeeded: %s", response.status)

def handler(event, context):
    """EventBridgeからAWS Healthイベントを受け取るエントリーポイント"""
    logger.info("Received event: %s", json.dumps(event, ensure_ascii=False))

    try:
        # 1. イベントデータからの情報抽出
        detail = event.get("detail", {})
        descriptions = detail.get("eventDescription", [])
        event_title = detail.get("eventTypeCode", "AWS_HEALTH_EVENT")
        affected_resources = (
            ", ".join(event.get("resources", []))
            if event.get("resources")
            else "なし"
        )
        event_region = event.get("region", "不明")

        health_text = (
            descriptions[0].get("latestDescription", "通知内容が空です。")
            if descriptions
            else "Healthイベントのパースに失敗しました。"
        )

        # 2. Bedrockによる通知本文の要約処理
        summary_result = summary_bedrock(health_text)

        # 3. Backlog課題用の本文組み立て（Backlog記法）
        backlog_body = f"""* AWS Health通知 要約
{summary_result}

* 通知原文
{health_text}
** 対象リソース
{affected_resources}
** リージョン
{event_region}
"""

        # 4. Backlogへの通知（課題作成）の実行
        notify_backlog(
            summary=f"【AWS Health】{event_title}", 
            description=backlog_body
        )

        # 5. 正常終了レスポンスの返却
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Successfully processed event and notified Backlog"}
            ),
        }

    except Exception:
        # 6. 例外時のログ記録と自動リトライのための再投げ
        logger.exception("Error processing event")
        raise