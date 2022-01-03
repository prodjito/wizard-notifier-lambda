import os
import json
import base64
import urllib.parse
import hashlib
import hmac
from slack_sdk import WebClient
from slack_sdk.webhook import WebhookClient

def lambda_handler(event, context):

    token = os.environ['BOT_USER_OAUTH_TOKEN']
    client = WebClient(token)

    product_to_channel_mapping = json.loads(os.environ['PRODUCT_TO_CHANNEL_MAPPING'])

    request_body = event['body']
    if event['isBase64Encoded']:
        request_body = base64.b64decode(request_body).decode("utf-8")

    signing_secret = os.environ['BOT_SIGNING_SECRET']
    slack_signing_secret = bytes(signing_secret, "utf-8")
    headers = event['headers']
    slack_signature = headers['x-slack-signature']
    slack_request_timestamp = headers['x-slack-request-timestamp']
    basestring = f"v0:{slack_request_timestamp}:{request_body}".encode('utf-8')
    my_signature = 'v0=' + hmac.new(slack_signing_secret, basestring, hashlib.sha256).hexdigest()
    verified = hmac.compare_digest(my_signature, slack_signature)

    data = dict(item.split("=") for item in request_body.split("&"))

    user_name = data['user_name']
    customer_channel_id = data['channel_id']
    customer_channel_name = data['channel_name']
    text = urllib.parse.unquote_plus(data['text'])

    if verified and customer_channel_name.startswith('shared'):
        parsed = text.split(' ', 1)
        product = parsed[0]
        if product in product_to_channel_mapping:
            message = parsed[1]
            wizard_webhook_url = product_to_channel_mapping[product]
            webhook = WebhookClient(wizard_webhook_url)
            webhook.send(text='`%s` in `#%s` posted: ```%s```'%(user_name, customer_channel_name, message))
            client.chat_postMessage(channel=customer_channel_id, text='`%s`, your message: ```%s``` has been reposted on `#wizards-%s`.'%(user_name, message, product))
        else:
            client.chat_postMessage(channel=customer_channel_id, text='Your message must start with one of the following: ' + str(", ".join(list(product_to_channel_mapping.keys()))))

    return {
        'statusCode': 200,
        #'body': json.dumps('Hello from Lambda!')
    }
