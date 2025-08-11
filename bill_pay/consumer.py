# consumer.py
import asyncio
import os
import json
import logging
from aiokafka import AIOKafkaConsumer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def consume_messages():
    """
    Consumes messages from Kafka topics with a retry mechanism for connection.
    """
    # Get Kafka broker address from environment variable
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka-vm:9092")
    
    # Retry logic for Kafka connection
    retries = 5
    delay = 1
    consumer = None
    for i in range(retries):
        try:
            logging.info(f"Attempting to connect to Kafka at {kafka_broker} (attempt {i+1}/{retries})...")
            # Create an AIOKafkaConsumer instance
            consumer = AIOKafkaConsumer(
                'bill_payments',
                'recurring_payments',
                'payment_cancellations',
                bootstrap_servers=kafka_broker,
                group_id='bill-pay-consumer-group',
                auto_offset_reset='earliest'
            )
            await consumer.start()
            logging.info("Consumer connected successfully. Waiting for messages...")
            break
        except Exception as e:
            logging.error(f"Consumer connection error: {e}. Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
    else:
        logging.error("Failed to connect to Kafka after multiple retries. The consumer will not be able to run.")
        return # Exit the function if connection fails permanently

    try:
        # Consume messages indefinitely
        async for message in consumer:
            # Decode the message key and value
            topic = message.topic
            # The message value is a byte string, decode it to a UTF-8 string
            value = message.value.decode('utf-8')
            
            logging.info(f"Received message on topic '{topic}': {value}")
            
    except Exception as e:
        logging.error(f"Consumer encountered an error: {e}")
    finally:
        # Ensure the consumer is stopped on exit
        if consumer:
            await consumer.stop()
            logging.info("Consumer stopped.")

if __name__ == '__main__':
    asyncio.run(consume_messages())
