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
