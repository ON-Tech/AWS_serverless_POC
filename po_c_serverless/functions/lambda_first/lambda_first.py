import boto3, uuid

client = boto3.resource('dynamodb')
table = client.Table("POC_orders")

def handler(event, context):
    for record in event['Records']:
        print("test")
        payload = record["body"]
        print(str(payload))
        table.put_item(Item= {'orderID': str(uuid.uuid4()),'POC_order':  payload})