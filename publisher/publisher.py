import json
import socket
import time
import sys
from dataclasses import asdict
from traffic_data_fetcher import TrafficDataFetcher
from traffic_data_fetcher import Event
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

lamport_timestamp = 0

def publisher(broker_addresses):
    leader_address = None
    for broker_address in broker_addresses:
        try:
            publisher_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            leader_address = get_leader_address(broker_address)
            if leader_address:
                publisher_socket.connect(leader_address)  # Connect to the broker
                logger.info(f"Connected to broker at {leader_address}")
                break
            else:
                logger.error(f"Failed to get leader address from broker: {broker_address}")
        except (socket.error, ConnectionRefusedError) as e:
            logger.error(f"Error connecting to broker {broker_address}: {e}")
            publisher_socket.close()

    if not leader_address:
        logger.error("Failed to connect to any broker. Exiting.")
        return

    fetcher = TrafficDataFetcher(api_url="http://api.511.org/traffic/", api_key="9d297b1d-eb23-4a0c-bd71-ec8bd076ab10")
    global lamport_timestamp
    try:
        raw_data = fetcher.fetch_data("events")  # Get JSON data from the TrafficDataFetcher class
        if raw_data:
            # Get the processed events
            fetcher.extract_data(raw_data) 
            events = fetcher.get_fetched_events()
            # Clear the fetched events after processing
            #fetcher.events_fetched.clear()
            for event in events:
                # Use the 'area' attribute of the event as the topic
                topic = event.area
                # Convert the event object to a JSON-serializable dictionary
                event_dict = asdict(event)
                # Include the topic in the message
                lamport_timestamp += 1
                message = f"PUBLISH*{topic}*{json.dumps(event_dict)}*{lamport_timestamp}\n"
                logger.info(f"Sending data:{message}")
                publisher_socket.sendall(message.encode('utf-8'))
                print("Data sent\n")
                # Optionally, add a delay between sending individual events
                time.sleep(0.1)
        else:
            logger.error("No raw data")

    except KeyboardInterrupt:
        logger.error("Publisher interrupted.")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")


def get_leader_address(broker_address):
    try:
        global lamport_timestamp
        lamport_timestamp += 1
        leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        leader_socket.connect(broker_address)
        # Send a request for the current leader's address
        leader_socket.send(f"GET_LEADER_ADDRESS*{lamport_timestamp}\n".encode())
        # Receive the leader's address as "<host>:<port>"
        message = leader_socket.recv(1024).decode()
        address_str, timestamp_str = message.split("*")
        # Convert the leader's address to a tuple (host, port)
        leader_host, leader_port = address_str.split(":")
        leader_address = (leader_host, int(leader_port))
        lamport_timestamp = max(lamport_timestamp, int(timestamp_str)) + 1

        return leader_address
    except (socket.error, ConnectionRefusedError) as e:
        logger.error(f"Error getting leader address: {e}")
        return None  # Return None to indicate failure

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python publisher.py <broker_address1> <broker_address2> ...")
    else:
        broker_addresses = []
        for arg in sys.argv[1:]:
            host, port = arg.split(':')
            broker_addresses.append((host, int(port)))
        publisher(broker_addresses)
