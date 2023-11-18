import socket
import json
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

lamport_timestamp = 0

def subscriber(subscriber_name, topics, broker_addresses):
    leader_address = None
    for broker_address in broker_addresses:
        try:
            # Attempt to connect to the current broker
            subscriber_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            leader_address = get_leader_address(broker_address)
            if leader_address:
                subscriber_socket.connect(leader_address)
                logger.info(f"Connected to broker: {leader_address}")
                break
            else:
                logger.error(f"Failed to get leader address from broker: {broker_address}")
        except (socket.error, ConnectionRefusedError) as e:
            logger.exception(f"Error connecting to broker {broker_address}: {e}")
            subscriber_socket.close()

    if not leader_address:
       logger.error("Failed to connect to any broker. Exiting.")
       return
    
    # Subscribe to each topic
    try:
        for topic in topics:
            global lamport_timestamp
            lamport_timestamp += 1
            subscriber_socket.send(f"SUBSCRIBE*{topic}*{lamport_timestamp}\n".encode())
            time.sleep(0.1)

        while True:
            message = subscriber_socket.recv(1024).decode()
            if message:
                parts = message.split('*')
                if len(parts) >= 2:
                    received_data = parts[0]
                    received_timestamp = int(parts[1])
                    lamport_timestamp = max(lamport_timestamp, received_timestamp) + 1
                    event_data = json.loads(received_data)
                    if event_data["area"] in topics:
                        print(f"Subscriber {subscriber_name} received traffic event:")
                        print(f"Event ID: {event_data['event_id']}")
                        print(f"Area: \033[91m{event_data['area']}\033[0m")
                        print(f"Event Type: {event_data['event_type']}")
                        print(f"Headline: {event_data['headline']}")
                        print(f"Updated: {event_data['updated']}")
                        print(f"\033[32mLamport timestamp: {lamport_timestamp}\033[0m")
                        print()
            
    except ConnectionResetError:
        logger.error("Connection reset by peer. Broker may have terminated. Attempting to reconnect...")
        subscriber_socket.close()
        return subscriber(subscriber_name, topics, broker_addresses)  # Recursively call subscriber to reconnect
    except KeyboardInterrupt:
        logger.error(f"Subscriber {subscriber_name} is shutting down.")
    finally:
        subscriber_socket.close()


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