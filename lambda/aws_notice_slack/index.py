import json
import logging
import os
import urllib.error
import urllib.request

import boto3

# ログ設定：Lambda標準ロガーの出力レベルをINFOに設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 1.環境変数の読み込み
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# Bedrockクライアントの初期化（関数の外で定義して再利用）
bedrock_runtime = boto3.client(service_name="bedrock-runtime", region_name="us-east-1")

def summary_bedrock(health_text: str) -> str:
    """Bedrock (Claude) を呼び出して通知内容を要約する関数"""
    # 1. プロンプトの組み立て
    prompt_content = f"""
以下のAWS Health通知の内容をインフラエンジニア向けに日本語で分かりやすく要約し、必ず指定されたフォーマットを厳密に守って出力してください。

【出力フォーマット】
*概要*
*緊急度*
*対応策*

⚠️【最重要ルール】
・「AWS Health通知 要約」や「# AWS Health通知の要約」といった、独自のタイトルや全体の見出しは【絶対に】出力しないでください。
・挨拶や前置き、まとめの言葉も一切不要です。必ず「*概要*」の文字列から書き始めてください。

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

def notify_slack(description: str) -> None:
    """Slack Webhook を使用して通知を送信する関数"""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL が未設定のため送信をスキップします。")
        return

    logger.info("Slackへの送信を開始します。")

    # Slack 用のペイロード作成
    payload = {"text": description}
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        SLACK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            logger.info("Slack通知成功 (Status: %s)", response.status)
    except urllib.error.HTTPError as e:
        logger.error("Slack通知失敗 (HTTP Error: %s %s)", e.code, e.reason)
        raise
    except urllib.error.URLError as e:
        logger.error("Slack通知失敗 (URL Error: %s)", e.reason)
        raise

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

        # 3. slack課題用の本文組み立て（Markdown記法）
        slack_body = f"""🚨 *【AWS Health通知】{event_title}* 🚨

*AWS Health通知 要約*
{summary_result}

---
*通知原文*
```{health_text}```
• *対象リソース:* `{affected_resources}`
• *リージョン:* `{event_region}`
"""

        # 4. Slackへの通知の実行
        notify_slack(description=slack_body)

        # 5. 正常終了レスポンスの返却
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Successfully processed event and notified Slack"}
            ),
        }

    except Exception:
        # 6. 例外時のログ記録と自動リトライのための再投げ
        logger.exception("Error processing event")
        raise