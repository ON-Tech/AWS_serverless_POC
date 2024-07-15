import aws_cdk as core
import aws_cdk.assertions as assertions

from po_c_serverless.po_c_serverless_stack import PoCServerlessStack

# example tests. To run these tests, uncomment this file along with the example
# resource in po_c_serverless/po_c_serverless_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = PoCServerlessStack(app, "po-c-serverless")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
