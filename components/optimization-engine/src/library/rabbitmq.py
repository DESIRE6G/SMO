# ProcessingSystems/rabbitmq.py

import asyncio
import os
import time
import yaml
import logging
from aio_pika import connect, IncomingMessage, ExchangeType, Message
from .config import rabbitmq_host, input_topic, output_topic, d6g_site
import base64

# Functionality
import library.optimization_engine as optimization_engine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

async def process_message(message: IncomingMessage, message_counter):
    try:
        body = message.body.decode('utf-8')
        body = base64.b64decode(body).decode('utf-8')
        parsed_yaml = yaml.safe_load(body)
        # clear_screen()
        # logger.info(f"Processing message {message_counter}...")
        logger.info("Received service optimization request number:" + str(message_counter) + ", with ns instance id:" + parsed_yaml["lnsd"]["ns-instance-id"]) # parsed_yaml["local-nsd"]["info"]["ns"]["id"])
        logger.info("---parsed_yaml---")
        logger.info(parsed_yaml)
        logger.info("---parsed_yaml---")

        #modified_message = f"Processed: {base64.b64decode(message.body).decode()}"
        # modified_message = message.body

        # logger.info(f"Message {message_counter} processing complete.")

        # ----- Service Request -----

        start_time = time.time()
        # modified_message = optimization_engine.optimization_engine(message.body, d6g_site)
        modified_message = optimization_engine.optimization_engine(parsed_yaml, d6g_site)
        logger.info("COMPLETE.")
        logger.info("Total handling time: " + str((time.time() - start_time) * 1000) + " milliseconds.")
        if modified_message == -1:
            logger.error(f"Optimization Engine returned an error. Error during optimization pipeline.")
            # return yaml.dumps({"Error": "Error during optimization pipeline"})
            # modified_message = message.body
        
        # ----- Optimized Service Request -----
        
        # Manually acknowledge the message
        await message.ack()

        logger.info("Optimized request ready for dispatch.")
        return modified_message
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        
        # Optionally reject the message in case of an error
        await message.reject(requeue=False)
        
        return None

async def consume_messages():
    try:
        # Connect to RabbitMQ
        connection = await connect(f"amqp://{rabbitmq_host}/")
        channel = await connection.channel()

        # Declare queues and get the default exchange
        input_queue = await channel.declare_queue(input_topic)
        output_queue = await channel.declare_queue(output_topic)
        default_exchange = channel.default_exchange

        message_counter = 0  # Initialize message counter here

        async def on_message(message: IncomingMessage):
            nonlocal message_counter  # Use nonlocal to modify the outer variable
            message_counter += 1
            modified_message = await process_message(message, message_counter)
            if modified_message:
                await default_exchange.publish(
                    Message(modified_message),
                    routing_key=output_topic  # Provide the routing_key here
                )
                # logger.info(f"Processed message {message_counter}: {message.body.decode()}")

        await input_queue.consume(on_message)
        logger.info("Waiting for messages to process. To exit, press CTRL+C")

        return connection
    except Exception as e:
        logger.error(f"Error in consuming messages: {str(e)}")
        raise  # Reraise the exception to propagate it up the call stack
