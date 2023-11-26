import json
import socket
import threading
import argparse
import time
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class TrafficBroker:
    def __init__(self, host, port, cluster_address=None):
        # Server
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # To resolve "address already in use" issue
        self.server.bind(('0.0.0.0', port))
        self.server.listen(10)
        # Subscription
        self.topic_subscribers = {} # key: topic, value: list of subscribers' socket objects
        self.topic_subscribers_addresses = {} # key: topic, value: list of subscribers' socket addresses
        self.subscriber_lock = threading.Lock()
        # Leader election 
        self.is_leader = False
        self.current_leader = None
        self.election_in_progress = False
        self.election_timeout = 2
        self.election_lock = threading.Lock()
        # Timestamp
        self.lamport_timestamp = 0
        self.timestamp_lock = threading.Lock()  # Lock for synchronizing timestamp updates
        # Cluster 
        self.last_gossip_time = {}
        self.timeout_lock = threading.Lock()
        self.cluster_sockets = {} # Dictionary to store connections example: {('localhost', 8889): <socket object>, ('localhost', 8890): <socket object>}.
        self.cluster_status = {} #dictionary to store details of every broker in the cluster
        self.cluster_address = cluster_address # example: [('localhost', 8889), ('localhost', 8890)].
        if self.cluster_address:
            self.setup_cluster()

        logger.info(f"Broker listening on {host}:{port}")

    
    # Sets up cluster of brokers conneced to each other
    def setup_cluster(self):
        # Connect to other brokers in the cluster
        for addr in self.cluster_address:
            self.connect_to_cluster_node(addr)
        # LEADER ELECTION ALGORITHM: start election after cluster is formed
        self.start_election_thread()
        time.sleep(1)
        # GOSSIP PROTOCOL ALGORITHM: Start a thread for gossip protocol
        self.increment_timestamp()
        gossip_thread = threading.Thread(target=self.start_gossip_protocol)
        gossip_thread.start()
        # Start a thread for gossip timeout
        timeout_check_thread = threading.Thread(target=self.check_gossip_timeouts)
        timeout_check_thread.start()


    def connect_to_cluster_node(self, addr, retry_count = 3, retry_delay=2):
        # Implement a mechanism to connect to other brokers in the cluster
        for attempt in range(retry_count):
            try:
                cluster_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cluster_socket.connect(addr)
                self.cluster_sockets[addr] = cluster_socket
                logger.info(f"\033[32m {self.port} Connected to cluster node at {addr}\033[0m")
                return
            except ConnectionRefusedError as e:
                if attempt < retry_count - 1:
                    logger.warning(f"Retry {attempt + 1}/{retry_count} connecting to {addr}")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"\n \033[31m Error connecting to cluster node at {addr}: {e} \033[0m")


    def handle_client(self, client_socket):
        while True:
            data = client_socket.recv(4096).decode()
            if not data:
                logger.info(f"\n\033[31mClient {client_socket} disconnected.\033[0m")
                break
            # Handle the messages
            messages = data.split('\n')
            for message in messages:
                if message:
                    self.process_message(message, client_socket)
        client_socket.close()
        
    # Processes different types of messages received by the broker based on the command {'PUBLISH', 'SUBSCRIBE', 'ELECTION', 'VICTORY', 'ELECTION_ACK', 'VICTORY' }
    def process_message(self, message, client_socket):
        logger.info(f"Got message: {message}")
        #Process individual message
        parts = message.split("*")
        command = parts[0]
        
        if command == "SUBSCRIBE":
            topic = parts[1]
            received_timestamp = int(parts[2])
            self.update_timestamp(received_timestamp)
            with self.subscriber_lock:
                if topic not in self.topic_subscribers:
                    self.topic_subscribers[topic] = []
                self.topic_subscribers[topic].append(client_socket)
                # Extract and add the address to the topic_subscriber_addresses
                client_address = client_socket.getpeername()  # Returns (IP, port)
                address_str = f"{client_address[0]}:{client_address[1]}"
                if topic not in self.topic_subscribers_addresses:
                    self.topic_subscribers_addresses[topic] = []
                self.topic_subscribers_addresses[topic].append(address_str)
        
        elif command == "PUBLISH":
            topic = parts[1]
            data = parts[2]
            received_timestamp = int(parts[3])
            self.update_timestamp(received_timestamp)
            
            if topic in self.topic_subscribers:
                disconnected_subscribers = []
                disconnected_addresses = []
                for subscriber in self.topic_subscribers[topic]:
                    try:
                        self.increment_timestamp()
                        subscriber.send(f"{data}*{self.lamport_timestamp}\n".encode())
                    except socket.error as e:
                        with self.subscriber_lock:
                            disconnected_subscribers.append(subscriber)
                            # Extract and store the address of the disconnected subscriber
                            disconnected_address = f"{subscriber.getpeername()[0]}:{subscriber.getpeername()[1]}"
                            disconnected_addresses.append(disconnected_address)
                with self.subscriber_lock:
                    # Removing disconnected subscribers from the list and their addresses
                    for subscriber in disconnected_subscribers:
                        self.topic_subscribers[topic].remove(subscriber)
                    for address in disconnected_addresses:
                        if address in self.topic_subscribers_addresses[topic]:
                            self.topic_subscribers_addresses[topic].remove(address)

        elif command == "ELECTION":
            sender_addr_str = parts[1]  # Assuming the sender's address is part of the message
            received_timestamp = int(parts[2])
            self.update_timestamp(received_timestamp)
            sender_host, sender_port_str = sender_addr_str.split(':')
            sender_port = int(sender_port_str)
            sender_addr = (sender_host, sender_port)
            self.respond_to_election(sender_addr)
            if not self.election_in_progress:
                self.start_election()
        
        elif command == "VICTORY":
            # A broker has announced it is the new leader
            sender_addr_str = parts[1]
            received_timestamp = int(parts[2])
            self.update_timestamp(received_timestamp)
            leader_host, leader_port = sender_addr_str.split(':')
            with self.election_lock:
                self.current_leader = (leader_host, int(leader_port))
                self.is_leader = (self.current_leader == (self.host, self.port))
                self.election_in_progress = False
                logger.info(f"\033[34mElection ended. Current leader is {self.current_leader}\033[0m")
        
        elif command == "ELECTION_ACK":
            sender_addr = parts[1]
            received_timestamp = int(parts[2])
            self.update_timestamp(received_timestamp)
            # Acknowledgement received from a higher broker
            print(f"Election Acknowledgement received from {sender_addr}")
            # If an ack is received, it means this broker should not become the leader
            # Reset or update relevant election flags
            with self.election_lock:
                self.election_in_progress = False
                self.is_leader = False
       
        elif command == "GOSSIP":
            # Process the incoming gossip message
            details = json.loads(parts[1])
            self.process_gossip_data(details)
        elif command == "GET_LEADER_ADDRESS":
            # Handle the GET_LEADER_ADDRESS request
            self.handle_get_leader_address(client_socket)


    def run(self):
        while True:
            client_socket, addr = self.server.accept()
            logger.info(f"\033[32mAccepted connection from {addr}\033[0m")
            client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_handler.start()


    # Leader election Algorithm implementation
    def start_election(self):
        if self.election_in_progress or self.is_leader:
            logger.warning(f"\nElection already in progress on {self.port}")
            return
        logger.info(f"\033[34m{self.host}:{self.port} starts an election\033[0m")
        with self.election_lock:
            self.election_in_progress = True
        # Compare only the port numbers to find higher brokers
        higher_brokers = [addr for addr in self.cluster_address if addr[1] > self.port]
        self.increment_timestamp()    
        if not higher_brokers:
            # This broker has the highest identifier and becomes the leader
            logger.info("No higher port number found")
            self.announce_leader()
            return
            
        for addr in higher_brokers:
            logger.info(f"Higher port number found at address:{addr}")
            # Send an election message to each higher broker
            self.send_election_message(addr)
            # Start a timer to wait for a response
            self.start_election_timeout()


    def start_election_timeout(self):
        threading.Timer(self.election_timeout, self.check_election_timeout).start()


    def check_election_timeout(self):
        if self.election_in_progress:
            # No response received within timeout, declare self as leader
            logger.warning(f"No response received within timeout, declare {self.port} as leader")
            self.announce_leader()
    
    
    def announce_leader(self):
        # Announce victory only if this broker is not already the leader
        if not self.is_leader:
            for addr in self.cluster_address:
                if addr != (self.host, self.port):
                    self.send_victory_message(addr)
        with self.election_lock:
            self.is_leader = True
            self.current_leader = (self.host, self.port)
            logger.info(f"\033[34mElection ended. Current leader: {self.current_leader}\033[0m")
    
    
    def send_election_message(self, addr):
        # Send an election message to the broker at addr
        try:
            self.increment_timestamp()
            election_message = f"ELECTION*{self.host}:{self.port}*{self.lamport_timestamp}\n"
            self.cluster_sockets[addr].send(election_message.encode())
            logger.info(f"{self.host}:{self.port} sending election message to {addr}")
        except Exception as e:
            logger.error(f"Error sending election message to {addr}: {e}")
    
    
    def send_victory_message(self, addr):
        # Announces to other brokers that the current broker has won the election.
        try:
            self.increment_timestamp()
            victory_message = f"VICTORY*{self.host}:{self.port}*{self.lamport_timestamp}\n"
            self.cluster_sockets[addr].send(victory_message.encode())
            print(f"{self.host}:{self.port} sending the victory message to {addr}")
        except Exception as e:
            logger.error(f"Error sending victory message to {addr}: {e}")
        
        
    def respond_to_election(self, addr):
        try:
            self.increment_timestamp()
            # Respond to the sender indicating that this broker is still active
            response_message = f"ELECTION_ACK*{self.host}:{self.port}*{self.lamport_timestamp}\n"
            self.cluster_sockets[addr].send(response_message.encode())
            print(f"{self.host}:{self.port} sending ack message to {addr}")
        except Exception as e:
            logger.error(f"Error responding to election message from {addr}: {e}")
    
    
    def start_election_thread(self):
        election_thread = threading.Thread(target=self.start_election)
        election_thread.start()
    
    
    def get_leader_address(self):
        return self.current_leader
    
    
    def handle_get_leader_address(self, client_socket):
        # Respond to the GET_LEADER_ADDRESS request by sending the current leader's address
        self.increment_timestamp()
        leader_address = f"{self.current_leader[0]}:{self.current_leader[1]}*{self.lamport_timestamp}\n"
        client_socket.send(leader_address.encode())


    # gossip protocol algorithm implementation
    def start_gossip_protocol(self):
        info = "\033[33mNo active brokers in cluster_sockets. Gossip ended.\033[0m"
        while True:
            # Check if there are no active brokers in cluster_sockets
            if not self.cluster_sockets:
                logger.info(info)
                info = "Continue sending heartbeat to all the subscribers..."
                # Keep sending heartbeat
                if self.is_leader:
                    self.send_heartbeat_message()
                time.sleep(3)
                continue
            
            # Choose a random broker from the cluster to gossip with
            random_broker = random.choice(list(self.cluster_sockets.keys()))
            logger.info(f"Starting gossip, {self.port} will gossip with: {random_broker}")
            # Send and receive gossip messages with the chosen broker
            self.send_gossip_message(random_broker)
            # Send heartbeat messages to all the subscribers
            if self.is_leader:
                logger.info("Sending heartbeat to all the subscribers...")
                self.send_heartbeat_message()
            # Introduce a delay before the next round of gossip
            time.sleep(3)  # Adjust the interval as needed
    
    
    def send_gossip_message(self, addr):
        try:
            # Create a gossip message with relevant information
            self.increment_timestamp()
            details = json.dumps(self.get_current_broker_details())
            gossip_message = f"GOSSIP*{details}\n"
            self.cluster_sockets[addr].send(gossip_message.encode())  
        except Exception as e:
            logger.error(f"Error sending gossip message to {addr}: {e}")
            self.handle_broker_failure(addr)

    # Heartbeat Mechanism
    def send_heartbeat_message(self):
        # Extract unique subscriber socket objects
        unique_subscriber_sockets = set()
        for subscribers in self.topic_subscribers.values():
            for subscriber in subscribers:
                unique_subscriber_sockets.add(subscriber)
        # Check if there are any subscribers to send heartbeat to
        if not unique_subscriber_sockets:
            print("No subscribers to send heartbeat.")
            return

        for subscriber in unique_subscriber_sockets:
            try:
                self.increment_timestamp()
                heartbeat_message = f"HEARTBEAT*{self.lamport_timestamp}\n"
                subscriber.send(heartbeat_message.encode())
            except Exception as e:
                logger.error(f"Error sending heartbeat message: {e}")


    def process_gossip_data(self, details):
        # Update your broker's state based on the received gossip data
        sender_addr = tuple(details['addr'])
        sender_subscribers = details['topic_subscribers']
        sender_timestamp = int(details['timestamp'])

        # Update your local information about the sender
        self.update_last_gossip_time(sender_addr)
        self.update_timestamp(sender_timestamp)
        
        with self.subscriber_lock:
            # Check if the current broker is not the leader
            if not self.is_leader:
                # Merge the topic subscriber addresses for non-leader nodes
                merged_subscribers = self.merge_subscribers(self.topic_subscribers_addresses, sender_subscribers)
                self.topic_subscribers_addresses = merged_subscribers

            # Update cluster status
            self.cluster_status[sender_addr] = details
            logger.info(f"Updated cluster status from gossip: {sender_addr}")
        
    
    # Merge local and remote subscribers, ensuring no duplicates.
    def merge_subscribers(self, local_subscribers, remote_subscribers):
        merged_subscribers = {}
        for topic in set(local_subscribers.keys()).union(remote_subscribers.keys()):
            local_subs = set(local_subscribers.get(topic, []))
            remote_subs = set(remote_subscribers.get(topic, []))
            merged_subscribers[topic] = list(local_subs.union(remote_subs))
        return merged_subscribers
    
    
    def get_current_broker_details(self):
        details = {
            "addr": (self.host, self.port),
            "status": "UP",
            "topic_subscribers": self.topic_subscribers_addresses,
            "timestamp": self.lamport_timestamp # Add a timestamp
        }
        return details
    
    def update_last_gossip_time(self, broker_addr):
        with self.timeout_lock:
            self.last_gossip_time[broker_addr] = time.time()

    def check_gossip_timeouts(self):
        timeout_threshold = 30  # seconds
        while True:
            current_time = time.time()
            for broker_addr, last_contact in list(self.last_gossip_time.items()):
                if current_time - last_contact > timeout_threshold:
                    logger.error(f"Timeout detected for broker {broker_addr}")
                    # Handle the broker failure
                    self.handle_broker_failure(broker_addr)
                    # Remove the failed broker from the last_gossip_time dictionary
                    with self.timeout_lock:
                        del self.last_gossip_time[broker_addr]
                        
            time.sleep(5)  # Check every 5 seconds
    
    # Broker Failure Handling Mechanism: If any broker fails, restart election among the active brokers to chose a new leader
    def handle_broker_failure(self, addr):
        print(f"\033[31mBroker at {addr} is considered failed.\033[0m")
        with self.subscriber_lock:
            if addr in self.cluster_status:
                self.cluster_status[addr]['status'] = 'DOWN'
            if addr in self.cluster_sockets:
                del self.cluster_sockets[addr]
            if addr in self.cluster_address:
                self.cluster_address.remove(addr)
                logger.info(f"Removed failed broker {addr} from cluster addresses.")
            # Check if the failed broker was the current leader
            if self.current_leader == addr:
                logger.warning(f"\033[33mCurrent leader {addr} has failed. Initiating new election.\033[0m")
                self.start_election_thread()


    # Lamport Timestamp 
    def increment_timestamp(self):
        with self.timestamp_lock:
            self.lamport_timestamp += 1

    
    def update_timestamp(self, received_timestamp):
        with self.timestamp_lock:
            self.lamport_timestamp = max(self.lamport_timestamp, received_timestamp) + 1


def parse_args():
    parser = argparse.ArgumentParser(description='Traffic Broker')
    parser.add_argument('--host', required=True, help='Actual address of the broker (container name or IP)')
    parser.add_argument('--port', type=int, required=True, help='Port for the broker')
    parser.add_argument('--cluster', nargs='*', help='List of other brokers in the cluster (host:port)', default=[])
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Convert cluster addresses from string "host:port" to tuple (host, port)
    cluster_addresses = []
    for addr in args.cluster:
        host, port = addr.split(":")
        cluster_addresses.append((host, int(port)))
    broker = TrafficBroker(args.host, args.port, cluster_addresses)
    # Run the broker server loop in a separate thread
    broker_thread = threading.Thread(target=broker.run)
    broker_thread.start()
    # Optionally, add a small delay to ensure the server is fully up
    time.sleep(1)
    # Keep the main thread alive or join the broker thread if you need to
    broker_thread.join()
    