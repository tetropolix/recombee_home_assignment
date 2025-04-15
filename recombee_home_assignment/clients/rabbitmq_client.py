from typing import Optional
import aio_pika


class RabbitMQClient:
    def __init__(
        self,
        user: str,
        password: str,
        host: str,
        exchange: Optional[str],
        queue: str,
        routing_key: Optional[str],
    ):
        self.user = user
        self.password = password
        self.host = host
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.connection = None
        self.channel = None
        self.exchange_declared = None
        self.queue_declared = None

    async def connect_for_publishing(self):
        if(self.exchange is None or self.routing_key is None):
            raise RuntimeError("Provide exchange and routing_key for publishing")

        self.connection = await aio_pika.connect_robust(
            f"amqp://{self.user}:{self.password}@{self.host}/"
        )
        self.channel = await self.connection.channel()

        self.exchange_declared = await self.channel.declare_exchange(
            self.exchange, aio_pika.ExchangeType.DIRECT, durable=True
        )
        self.queue_declared = await self.channel.declare_queue(self.queue, durable=True)
        await self.queue_declared.bind(
            self.exchange_declared, routing_key=self.routing_key
        )

    async def connect_for_consuming(self):
        self.connection = await aio_pika.connect_robust(
            f"amqp://{self.user}:{self.password}@{self.host}/"
        )
        self.channel = await self.connection.channel()

        self.queue_declared = await self.channel.declare_queue(self.queue, durable=True)        

    async def close(self):
        if self.connection:
            await self.connection.close()

    def get_channel(self):
        if not self.channel:
            raise RuntimeError("RabbitMQ channel not established.")
        return self.channel
    
    def get_queue(self):
        if not self.queue_declared:
            raise RuntimeError("RabbitMQ queue not declared.")
        return self.queue_declared
