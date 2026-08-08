#!/usr/bin/env python3
import os

import aws_cdk as cdk
from dotenv import load_dotenv

from awsnotice.awsnotice_stack import AwsnoticeStack

# .env ファイルの環境変数を読み込み
load_dotenv()

app = cdk.App()
AwsnoticeStack(
    app, 
    "AwsnoticeStack",
    env=cdk.Environment(
        account=os.getenv('AWS_ACCOUNT_ID'), 
        region=os.getenv('AWS_DEFAULT_REGION')
    ),
)

app.synth()
