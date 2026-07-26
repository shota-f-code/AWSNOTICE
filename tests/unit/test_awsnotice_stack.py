import aws_cdk as core
import aws_cdk.assertions as assertions

from awsnotice.awsnotice_stack import AwsnoticeStack

# example tests. To run these tests, uncomment this file along with the example
# resource in awsnotice/awsnotice_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsnoticeStack(app, "awsnotice")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
