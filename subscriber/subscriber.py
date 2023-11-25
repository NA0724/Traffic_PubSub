import socket
import json
import sys
import time
import logging
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
event_sub_data={}
lamport_timestamp = 0
heartbeat_timeout = 6

def subscriber(subscriber_name, topics, broker_addresses):
    leader_address = None
    for broker_address in broker_addresses:
        try:
            # Attempt to connect to the current broker
            subscriber_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            leader_address = get_leader_address(broker_address)
            if leader_address:
                subscriber_socket.connect(leader_address)
                logger.info(f"{subscriber_socket.getsockname()} Connected to broker: {leader_address}")
                break
            else:
                logger.error(f"Failed to get leader address from broker: {broker_address}")
        except (socket.error, ConnectionRefusedError) as e:
            logger.exception(f"Error connecting to broker {broker_address}: {e}")
            subscriber_socket.close()

    if not leader_address:
        logger.error("Failed to connect to any broker. Exiting.")
        return

    last_send_time = time.time()
    send_interval = 5
    sent = False
    # Subscribe to each topic
    try:
        for topic in topics:
            global lamport_timestamp
            lamport_timestamp += 1
            subscriber_socket.send(f"SUBSCRIBE*{topic}*{lamport_timestamp}\n".encode())
            time.sleep(0.1)
            
        last_heartbeat_time = time.time()
        while True:
            message = subscriber_socket.recv(1024).decode()
            logger.info(f"\033[91m Message received from broker: {message}\033[0m")
            if message:
                parts = message.split('*')
                if parts[0] == "HEARTBEAT":
                    last_heartbeat_time = time.time()
                    logger.info("Heartbeat received")
                    received_timestamp = int(parts[1])
                    lamport_timestamp = max(lamport_timestamp, received_timestamp) + 1
                else:
                    received_data = parts[0]
                    ip_address = subscriber_socket.getsockname()[0]
                    if ip_address not in event_sub_data:
                        event_sub_data[ip_address] = []
                    event_sub_data[ip_address].append(received_data)
                    received_timestamp = int(parts[1])
                    lamport_timestamp = max(lamport_timestamp, received_timestamp) + 1
                # Check if it's time to send data to Flask
                if not sent and time.time() - last_send_time > send_interval:
                    send_data_to_flask(event_sub_data)
                    sent = True
                    event_sub_data.clear()  # Clear the data after sending
                    last_send_time = time.time()
            # Check for heartbeat timeout
            if time.time() - last_heartbeat_time > heartbeat_timeout:
                logger.error("Heartbeat missed. Reconnecting...")
                time.sleep(30)
                subscriber_socket.close()
                return subscriber(subscriber_name, topics, broker_addresses)
            
    except ConnectionResetError:
        logger.error("Connection reset by peer. Broker may have terminated. Attempting to reconnect...")
        subscriber_socket.close()
        return subscriber(subscriber_name, topics, broker_addresses)  # Recursively call subscriber to reconnect
    except KeyboardInterrupt:
        logger.error(f"Subscriber {subscriber_name} is shutting down.")
    finally:
        subscriber_socket.close()
         

def send_data_to_flask(data):
    flask_url = 'http://flask:5002/subscriber_data'  # Replace with your Flask app's URL and endpoint
    try:    
        headers = {'Content-Type': 'application/json'}
        response = requests.post(flask_url, json=data, headers=headers)
        response.raise_for_status()
        logger.info(f"\033[92m Successfully send data to flask \033[0m")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending data to Flask: {e}")


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
    if len(sys.argv) < 4:
        print("Usage: python subscriber.py <subscriber_name> <broker_address1> <broker_address2> ... <topic1> <topic2> ...")
    else:
        subscriber_name = sys.argv[1]
        broker_addresses = []
        topics = []
        for arg in sys.argv[2:]:
            if ':' in arg:  # Simple way to differentiate broker addresses and topics
                host, port = arg.split(':')
                broker_addresses.append((host, int(port)))
            else:
                topics.append(arg)
        subscriber(subscriber_name, topics, broker_addresses)

    """
    
    Sample command:
        python3 subscriber.py "Sub1" "localhost:8888" "localhost:8889" "localhost:8890" "Santa Clara" "Santa Cruz"
    
        Topic(area) List:
    

        Alameda
        Contra Costa
        Marin
        San Francisco
        San Mateo
        San Benito
        Santa Clara
        Napa
        Solano
        Sonoma
        Merced
        Santa Cruz
        San Joaquin
        Stanislaus
    """