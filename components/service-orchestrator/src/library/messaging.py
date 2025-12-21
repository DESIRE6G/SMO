from abc import ABC, abstractmethod
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from typing import Optional
import asyncio
#from aio_pika import connect_robust, Message
from aio_pika import connect_robust, connect, IncomingMessage, ExchangeType, Message
from aio_pika.exceptions import QueueEmpty, AMQPConnectionError
import os
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class MessageClient(ABC):
    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def send_message(self, message: bytes):
        pass

    @abstractmethod
    async def receive_message(self) -> str | None:
        pass


def get_message_client() -> MessageClient:
    backend = os.getenv("MESSAGING_SYSTEM", "rabbitmq")
    if backend == "kafka":
        return KafkaClient(
            kafka_bootstrap_servers=os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            input_topic=os.getenv("INPUT_TOPIC", "input_topic"),
            final_topic=os.getenv("FINAL_TOPIC", "final_topic")
        )

    if backend == "rabbitmq":
        return RabbitMQClient(
            rabbitmq_host=os.getenv("RABBITMQ_HOST", "localhost"),
            input_topic=os.getenv("INPUT_TOPIC", "input_topic"),
            final_topic=os.getenv("FINAL_TOPIC", "final_topic"),
            max_retries=int(os.getenv("RABBITMQ_MAX_RETRIES", 15000))
        )
    raise ValueError(f"Invalid messaging system specified: {backend}")


class KafkaClient(MessageClient):
    producer: Optional[KafkaProducer]
    consumer: Optional[KafkaConsumer]

    def __init__(self, kafka_bootstrap_servers: str, input_topic: str, final_topic: str):
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.input_topic = input_topic
        self.final_topic = final_topic
        self.producer = None
        self.consumer = None

    async def connect(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers)
            self.consumer = KafkaConsumer(
                self.final_topic, bootstrap_servers=self.kafka_bootstrap_servers)
        except KafkaError as e:
            print(f"Error connecting to Kafka: {e}")
            self.producer = None  # Explicitly set to None on failure
            self.consumer = None

    async def send_message(self, message: bytes):
        try:
            if self.producer is None:
                await self.connect()
            if self.producer is None:
                raise KafkaError("Producer is not connected")

            future = self.producer.send(self.input_topic, message)
            record_metadata = future.get(timeout=10)
            print("Message sent successfully:", record_metadata)
        except KafkaError as e:
            print("Error sending message:", e)

    async def receive_message(self) -> str | None:
        try:
            if self.consumer is None:
                await self.connect()
            if self.consumer is None:
                raise KafkaError("Consumer is not connected")
            for message in self.consumer:
                return message.value.decode()
        except KafkaError as e:
            print("Error receiving message:", e)


class RabbitMQClient:
    def __init__(self, rabbitmq_host: str, input_topic: str, final_topic: str, max_retries: int):
        self.rabbitmq_host = rabbitmq_host
        self.input_topic = input_topic
        self.final_topic = final_topic
        self.channel = None
        self.connection = None
        self.max_retries = max_retries
        self.channel = None
        self.reply_queue = None  # ← CREATE ONCE
        self.futures = {}
        self.consumer_tag = None
        logger.info("input_topic: %s, output_topic:%s, rabbitmqhost=%s " %
              (input_topic, final_topic, rabbitmq_host))

    async def connect(self):
        try:
            self.connection = await connect_robust(f"amqp://{self.rabbitmq_host}/")
            self.channel = await self.connection.channel()
            await self.channel.declare_queue(self.input_topic,durable=True,exclusive=False, auto_delete=False)
            await self.channel.declare_queue(self.final_topic)

            # Create reply queue ONCE per worker
            self.reply_queue = await self.channel.declare_queue(
                exclusive=True,
                auto_delete=True
            )

            # Start consumer ONCE
            self.consumer_tag = await self.reply_queue.consume(self._on_response)
            logger.info(f"Worker {os.getpid()} created reply queue: {self.reply_queue.name}")  # ← Should see this ONCE per worker

        except AMQPConnectionError as e:
            logger.error(f"Error connecting to RabbitMQ: {e}")

    async def _on_response(self, msg: IncomingMessage):
        """Central handler for ALL responses"""
        future = self.futures.pop(msg.correlation_id, None)
        if future and not future.done():
            future.set_result(msg.body)
        await msg.ack()

    async def call_oe(self, message: bytes, timeout=5):
        if self.reply_queue is None:
            await self.connect()

        correlation_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self.futures[correlation_id] = future

        logger.info(f"correlation_id: {correlation_id}")
        # DO NOT LOG reply_queue here - it's always the same!

        try:
            await self.channel.default_exchange.publish(
                Message(
                    body=message,
                    correlation_id=correlation_id,
                    reply_to=self.reply_queue.name  # ← REUSE same queue
                ),
                routing_key=self.input_topic
            )

            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self.futures.pop(correlation_id, None)
            raise


