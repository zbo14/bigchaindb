import websocket
import pika

RABBITMQ_HOST = 'localhost'
WEBSOCKET_URL = 'ws://localhost:9985/api/v1/streams/valid_transactions'


def on_message(ws, message):
    print('Publishing to rabbitmq: {}'.format(message))
    channel.basic_publish(exchange='', routing_key='bigchaindb', body=message)


def on_close(ws):
    print('connection closed')
    connection.close()


# rabbitmq connection
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()
channel.queue_declare(queue='bigchaindb')


# websocket connection
websocket.enableTrace(True)
ws = websocket.WebSocketApp(WEBSOCKET_URL,
                            on_message=on_message,
                            on_close=on_close)

ws.run_forever()
