import aws_cdk as cdk
from aws_cdk import assertions

from awsnotice.awsnotice_stack import AwsnoticeStack


def test_resources_created():
    app = cdk.App()
    stack = AwsnoticeStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    # Lambda 関数が2つ定義されているか検証
    template.resource_count_is("AWS::Lambda::Function", 2)
    # EventBridge ルールが1つ定義されているか検証
    template.resource_count_is("AWS::Events::Rule", 1)