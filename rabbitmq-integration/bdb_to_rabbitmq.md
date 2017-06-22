# BigchainDB Integration with RabbitMQ

There may be situations where the websockets api is not enough and we may want
to use a message broker to publish BigchainDB events.

This document presents a solution to integrate BigchainDB with RabbitMQ using
the latest version of BigchainDB.

The idea is to have a separate process that listen to events from the
BigchainDB events api and publishes it to RabbitMQ.

If we don't want to expose the websockets api we can bind it the `localhost` by
changing the BigchainDB configuration file or by setting the
`BIGCHAINDB_WSSERVER_HOST` environment variable.

- **websocket_to_rabbitmq.py**

This code connects to the BigchainDB events api and to a RabbitMQ instance and
publishes the messages received by the events api to a RabbitMQ queue.

```python
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
```

- **listener.py**

This is just an example of a client consuming messages from RabbitMQ.

```python
import pika

RABBITMQ_HOST = 'localhost'


def on_receive(channel, method, properties, body):
    print('received: {}'.format(body))


connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=RABBITMQ_HOST))
channel = connection.channel()
channel.queue_declare(queue='bigchaindb')
channel.basic_consume(on_receive, queue='bigchaindb', no_ack=True)

print('Waiting for messages...')
channel.start_consuming()
```

- **requirements.txt**

```text
websocket-client==0.40.0
pika==0.10.0
```
