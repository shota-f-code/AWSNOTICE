import os

import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_lambda as lambda_
from aws_cdk import Duration, Stack, aws_iam
from constructs import Construct
from dotenv import load_dotenv

# .env ファイルの環境変数を読み込み
load_dotenv()

class AwsnoticeStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # EventBridge ルールの作成
        rule = events.Rule(
            self,
            "aws-notice-rule",
            event_pattern=events.EventPattern(
                source=["aws.health"]
            )
        )
        
        # Lambda backlog通知関数の作成
        lambda_backlog = lambda_.Function(
            self, 
            "aws_notice_backlog",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda/aws_notice_backlog"),
            timeout=Duration.seconds(30),
            environment={
                "BACKLOG_API_KEY": os.getenv("BACKLOG_API_KEY", ""),
                "BACKLOG_ISSUE_TYPE_ID": os.getenv("BACKLOG_ISSUE_TYPE_ID", ""),
                "BACKLOG_PROJECT_ID": os.getenv("BACKLOG_PROJECT_ID", ""),
                "BACKLOG_SPACE_ID": os.getenv("BACKLOG_SPACE_ID", ""),
                "BACKLOG_USER_ID": os.getenv("BACKLOG_USER_ID", "")
            }
        )
        
        # Lambda slack通知関数の作成
        lambda_slack = lambda_.Function(
            self, 
            "aws_notice_slack",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda/aws_notice_slack"),
            timeout=Duration.seconds(30),
            environment={
                "SLACK_WEBHOOK_URL": os.getenv("SLACK_WEBHOOK_URL", "")
            }
        )
        
        # EventBridge ルールに Lambda 関数をターゲットとして追加
        rule.add_target(targets.LambdaFunction(lambda_backlog))
        rule.add_target(targets.LambdaFunction(lambda_slack))
        
        # Bedrock & Health 用のポリシー定義
        bedrock_policy = aws_iam.PolicyStatement(
                actions=["health:DescribeEvents", 
                         "health:DescribeEventDetails",
                         "bedrock:InvokeModel",
                        ],
                resources=["*"]
        )
        
        # Lambda 関数に Bedrock & Health 用のポリシーをアタッチ
        lambda_backlog.add_to_role_policy(bedrock_policy)   
        lambda_slack.add_to_role_policy(bedrock_policy)
        