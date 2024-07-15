from aws_cdk import (
    Duration,
    Stack,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_lambda as _lambda,
    BundlingOptions
)
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from constructs import Construct
from aws_cdk import aws_iam as iam
import pathlib

first_lambda_file = pathlib.Path(__file__).parent / "functions" /"lambda_first"''
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
        read_sqs_policy = iam.PolicyStatement(
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
        cloud_watch_policy = iam.PolicyStatement(
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            resources=["*"]
        )
        
        # Define IAM role for lambda
        lambda_first_role = iam.Role(self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
        lambda_first_role.add_to_policy(lambda_write_ddb_policy, read_sqs_policy, cloud_watch_policy)
        
        # Define IAM role for lambda       
        lambda_second_role = iam.Role(self, "LambdaExecutionRole",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
        lambda_second_role.add_to_policy(sns_policy, lambda_read_ddbs_policy, cloud_watch_policy)
        
        # Define IAM role for API Gateway
        apigw_role = iam.Role(self, "ApiGatewayExecutionRole",
        assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com")
        )
        apigw_role.add_to_policy(cloud_watch_policy,read_sqs_policy)
        
        
        # Create the orders table in dynamodb
        orders_table = dynamodb.TableV2(
            self, "OrdersTable",
            table_name="orders",
            partition_key=dynamodb.Attribute(
                name="orderID",
                type=dynamodb.AttributeType.STRING
            )
        )
        

        # Create a sqs queue for orders
        orders_queue = sqs.Queue(
            self, "POCQueue",
            queue_name="POC_Queue"
            )
        orders_queue.grant_send_messages(lambda_first_role)
        orders_queue.grant_consume_messages(lambda_second_role)
        
        # Define the First Lambda function
        first_lambda = _lambda.Function(
            self, 'firstFunction',
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler='lambda_first.handler',
            timeout=Duration.minutes(5),
            code=_lambda.Code.from_asset(
                str(first_lambda_file),
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install --no-cache -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                ),
            ),
            role=lambda_first_role
        )
        # Add the SQS trigger to the Lambda function
        first_lambda.add_event_source(SqsEventSource(orders_queue, batch_size=10))
                                      