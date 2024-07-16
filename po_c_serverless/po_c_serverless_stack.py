from aws_cdk import (
    Duration,
    Stack,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    BundlingOptions
)
import aws_cdk.aws_lambda_event_sources as eventsources
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from constructs import Construct
from aws_cdk import aws_iam as iam
import pathlib

first_lambda_file = pathlib.Path(__file__).parent / "functions" /"lambda_first"''
second_lambda_file = pathlib.Path(__file__).parent / "functions" /"lambda_second"''


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
            sid="LambdaWriteDDBPolicy"
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
            sid="SNSPolicy"
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
            sid="LambdaReadDDBsPolicy"
        )
        # Policy to allow writing logs to CloudWatch
        read_sqs_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            resources=["*"],
            actions=[
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "sqs:GetQueueUrl",
                "sqs:SendMessage"
            ],
            sid="ReadSQSPolicy"
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
        lambda_first_role = iam.Role(self, "LambdaExecutionRole1",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
        lambda_first_role.add_to_policy(lambda_write_ddb_policy)
        lambda_first_role.add_to_policy(read_sqs_policy)
        lambda_first_role.add_to_policy(cloud_watch_policy)
        
        # Define IAM role for lambda       
        lambda_second_role = iam.Role(self, "LambdaExecutionRole2",
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
        lambda_second_role.add_to_policy(sns_policy)
        lambda_second_role.add_to_policy(lambda_read_ddbs_policy)
        lambda_second_role.add_to_policy(cloud_watch_policy)
        
        # Define IAM role for API Gateway
        apigw_role = iam.Role(self, "apigwExecutionRole",
        assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com")
        )
        apigw_role.add_to_policy(cloud_watch_policy)
        apigw_role.add_to_policy(read_sqs_policy)
        
        
        # Create the orders table in dynamodb
        orders_table = dynamodb.TableV2(
            self, "OrdersTable",
            table_name="POC_orders",
            partition_key=dynamodb.Attribute(
                name="orderID",
                type=dynamodb.AttributeType.STRING
            ),
            dynamo_stream=dynamodb.StreamViewType.OLD_IMAGE
        )
        

        # Create a sqs queue for orders
        orders_queue = sqs.Queue(
            self, "POCQueue",
            queue_name="POC_Queue",
            visibility_timeout=Duration.minutes(5)
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
                # bundling=BundlingOptions(
                #     image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                #     command=[
                #         "bash", "-c",
                #         "pip install --no-cache -r requirements.txt -t /asset-output && cp -au . /asset-output"
                #     ],
                # ),
            ),
            role=lambda_first_role
        )
        
        # Define the second Lambda functi
        second_lambda = _lambda.Function(
            self, 'secondFunction',
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler='lambda_second.lambda_handler',
            timeout=Duration.minutes(5),
            code=_lambda.Code.from_asset(
                str(second_lambda_file),
                # bundling=BundlingOptions(
                #     image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                #     command=[
                #         "bash", "-c",
                #         "pip install --no-cache -r requirements.txt -t /asset-output && cp -au . /asset-output"
                #     ],
                # ),
            ),
            role=lambda_second_role
        )
        
        # Add the SQS trigger to the Lambda function
        first_lambda.add_event_source(SqsEventSource(orders_queue, batch_size=10))
        
        # Add the DDB stream trigger to the Lambda function
        second_lambda.add_event_source(eventsources.DynamoEventSource(
            orders_table,
            starting_position=_lambda.StartingPosition.TRIM_HORIZON,
            batch_size=10,
            bisect_batch_on_error=True,
            retry_attempts=10,
        ))
        
        # Create an SNS topic
        topic = sns.Topic(
            self, "POCTopic",
            topic_name="POC-Topic"
        )
        
        # Add an email subscription to the SNS topic
        topic.add_subscription(subs.EmailSubscription("omar.alnaji00@gmail.com"))
        
        # Create API Gateway REST API
        api = apigw.RestApi(
            self, "POCAPI",
            rest_api_name="POC-API",
            description="This is a POC API",
            endpoint_configuration=apigw.EndpointConfiguration(types=[apigw.EndpointType.REGIONAL])
        )

        # Create a resource and method for the API
        api_resource = api.root.add_resource("resource_orders")
        post_integration = apigw.AwsIntegration(
            service="sqs",
            integration_http_method="POST",
            path=f"{self.account}/POC_Queue",
            options=apigw.IntegrationOptions(
                credentials_role=apigw_role,
                request_parameters={
                    "integration.request.header.Content-Type": "'application/x-www-form-urlencoded'"
                },
                request_templates={
                    "application/json": "Action=SendMessage&MessageBody=$input.body"
                },
                integration_responses=[
                    apigw.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": ""
                        }
                    )
                ]
            )
        )
        
        # Add POST method to the API resource
        api_resource.add_method(
            "POST",
            post_integration,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_models={
                        "application/json": apigw.Model.EMPTY_MODEL
                    }
                )
            ]
        )