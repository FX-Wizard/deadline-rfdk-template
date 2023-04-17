import aws_cdk as core
import aws_cdk.assertions as assertions

from rfdk_deadline_template.rfdk_deadline_template_stack import RfdkDeadlineTemplateStack

# example tests. To run these tests, uncomment this file along with the example
# resource in rfdk_deadline_template/rfdk_deadline_template_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = RfdkDeadlineTemplateStack(app, "rfdk-deadline-template")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
