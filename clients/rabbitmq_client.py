from typing import Optional
import aio_pika

from logger import get_logger

logger = get_logger(__name__)

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
        logger.info(f"Creating connection for publishing using {f'amqp://{self.user}:{self.password}@{self.host}/'}")
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
        logger.info("Connection for publishing created")

    async def connect_for_consuming(self):
        logger.info(f"Creating connection for consuming using {f'amqp://{self.user}:{self.password}@{self.host}/'}")
        self.connection = await aio_pika.connect_robust(
            f"amqp://{self.user}:{self.password}@{self.host}/"
        )
        self.channel = await self.connection.channel()

        self.queue_declared = await self.channel.declare_queue(self.queue, durable=True)     
        logger.info("Connection for consuming created")   

    async def close(self):
        if self.connection:
            await self.connection.close()
            logger.info("Connection closed")   

    def get_channel(self):
        if not self.channel:
            raise RuntimeError("RabbitMQ channel not established.")
        return self.channel
    
    def get_queue(self):
        if not self.queue_declared:
            raise RuntimeError("RabbitMQ queue not declared.")
        return self.queue_declared
