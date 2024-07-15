from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
)
from constructs import Construct
from aws_cdk import aws_iam as iam

class PoCServerlessStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Policy to put items into the DynamoDB table.
        lambda_write_ddb_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=[
                "dynamodb:PutItem",
                "dynamodb:DescribeTable"
            ],
            sid="VisualEditor0"
        )
        # Policy to get, list, and publish topics that are received by Lambda
        sns_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=[
                "sns:Publish",
                "sns:GetTopicAttributes",
                "sns:ListTopics"
            ],
            sid="VisualEditor0"
        )
        # Policy to get records from DynamoDB Streams
        lambda_read_ddbs_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=[
                "dynamodb:GetShardIterator",
                "dynamodb:DescribeStream",
                "dynamodb:ListStreams",
                "dynamodb:GetRecords"
            ],
            sid="VisualEditor0"
        )
        # Policy to allow writing logs to CloudWatch
        lambda_read_sqs_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=[
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "sqs:GetQueueUrl"
            ],
            sid="VisualEditor0"
        )

        # Policy to allow writing logs to CloudWatch
        cloid_watch_policy = iam.PolicyStatement(
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            resources=["*"]
        )
        
        # Define IAM role
        lambda_role = iam.Role(self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
