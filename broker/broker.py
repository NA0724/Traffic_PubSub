import json
import socket
import threading
import multiprocessing
import argparse
import time
import random
class TrafficBroker:
    def __init__(self, host, port, cluster_address=None):
        self.host = host
        self.port = port
        self.topic_subscribers = {}
        self.lock = threading.Lock()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # To resolve "address already in use" issue
        self.server.bind((host, port))
        self.server.listen(5)
        self.cluster_sockets = {} # Dictionary to store connections example: {('localhost', 8889): <socket object>, ('localhost', 8890): <socket object>}.
        #self.cluster_manager = None
        self.is_leader = False
        self.current_leader = None
        self.election_in_progress = False
        self.election_timeout = 10
        self.cluster_status = {} #dictionary to store details of every broker in the cluster
        self.cluster_address = cluster_address # example: [('localhost', 8889), ('localhost', 8890)].
        if self.cluster_address:
            self.setup_cluster()

        print(f"\nBroker listening on {host}:{port}", flush=True)
        
    
    def setup_cluster(self):
        # self.cluster_manager = multiprocessing.Manager()
        # self.shared_subscribers = self.cluster_manager.dict()

        # Connect to other brokers in the cluster
        for addr in self.cluster_address:
            self.connect_to_cluster_node(addr)
        # start election after cluster is formed
        self.start_election_thread()
        
        # Start a thread for gossip protocol
        gossip_thread = threading.Thread(target=self.start_gossip_protocol)
        gossip_thread.start()
        
        # failure_detection_thread = threading.Thread(target=self.start_failure_detection)
        # failure_detection_thread.daemon = True
        # failure_detection_thread.start()

    def connect_to_cluster_node(self, addr, retry_count = 3, retry_delay=2):
        # Implement a mechanism to connect to other brokers in the cluster
        for attempt in range(retry_count):
            try:
                cluster_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cluster_socket.connect(addr)
                self.cluster_sockets[addr] = cluster_socket
                print(f"\033[32m {self.port} Connected to cluster node at {addr}\033[0m")
                return
            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"Retry {attempt + 1}/{retry_count} connecting to {addr}")
                    time.sleep(retry_delay)
                else:
                    print(f"\nError connecting to cluster node at {addr}: {e}")


    def handle_client(self, client_socket):
        while True:
            data = client_socket.recv(4096).decode()
            if not data:
                print(f"\n\033[31mClient {client_socket} disconnected.\033[0m")
                break
            # Handle the messages
            messages = data.split('\n')
            for message in messages:
                if message:
                    if message == "GET_LEADER_ADDRESS":
                        # Handle the GET_LEADER_ADDRESS request
                        self.handle_get_leader_address(client_socket)
                    else:
                        self.process_message(message, client_socket)
        client_socket.close()


    def process_message(self, message, client_socket):
        print("\nGot message: ", message)
        #Process individual message
        parts = message.split("*")
        command = parts[0]
        if command == "SUBSCRIBE":
            with self.lock:
                topic = parts[1]
                if topic not in self.topic_subscribers:
                    self.topic_subscribers[topic] = []
                self.topic_subscribers[topic].append(client_socket)
        elif command == "PUBLISH":
            with self.lock:
                topic = parts[1]
                data = parts[2]
                if topic in self.topic_subscribers:
                    disconnected_subscribers = []
                    for subscriber in self.topic_subscribers[topic]:
                        try:
                            subscriber.send((data + '\n').encode())
                        except socket.error as e:
                            disconnected_subscribers.append(subscriber)
                    for subscriber in disconnected_subscribers:
                        self.topic_subscribers[topic].remove(subscriber)
                # Parse the received information and update local state accordingly
        elif command == "ELECTION":
            if self.is_leader:
                print(f"\n{self.port} ignoring election message as it's already the leader or election has ended.")
                return
            sender_addr_str = parts[1]  # Assuming the sender's address is part of the message
            sender_host, sender_port_str = sender_addr_str.split(':')
            sender_port = int(sender_port_str)
            sender_addr = (sender_host, sender_port)
            self.respond_to_election(sender_addr)
            if not self.election_in_progress:
                self.start_election()
        elif command == "VICTORY":
            # A broker has announced it is the new leader
            sender_addr_str = parts[1]
            leader_host, leader_port = sender_addr_str.split(':')
            self.current_leader = (leader_host, int(leader_port))
            self.is_leader = (self.current_leader == (self.host, self.port))
            self.election_in_progress = False
            print(f"\n\033[34mElection ended. Current leader is {self.current_leader}\033[0m")
        elif command == "ELECTION_ACK":
            sender_addr = parts[1]
            # Acknowledgement received from a higher broker
            print(f"\nElection Acknowledgement received from {sender_addr}")
            # If an ack is received, it means this broker should not become the leader
            # Reset or update relevant election flags
            self.election_in_progress = False
            self.is_leader = False
        elif command == "GOSSIP":
            with self.lock:
                # Process the incoming gossip message
                details = json.loads(parts[1])
                self.process_gossip_data(details)
                    


    def run(self):
        while True:
            client_socket, addr = self.server.accept()
            print(f"\033[32mAccepted connection from {addr}\033[0m")
            client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_handler.start()

    # Leader election
    def start_election(self):
        with self.lock:
            if self.election_in_progress or self.is_leader:
                print(f"\nElection already in progress on {self.port}")
                return
            print(f"\n{self.host}:{self.port} starts an election")
            self.election_in_progress = True
            higher_brokers = [addr for addr in self.cluster_address if addr > (self.host, self.port)]
            
            if not higher_brokers:
                # This broker has the highest identifier and becomes the leader
                print("\nNo higher address found")
                self.announce_leader()
                return
            
            for addr in higher_brokers:
                print("\nHigher address:", addr)
                # Send an election message to each higher broker
                self.send_election_message(addr)
                # Start a timer to wait for a response
                self.start_election_timeout()

    def start_election_timeout(self):
        threading.Timer(self.election_timeout, self.check_election_timeout).start()

    def check_election_timeout(self):
        with self.lock:
            if self.election_in_progress:
                # No response received within timeout, declare self as leader
                print(f"\nNo response received within timeout, declare {self.port} as leader")
                self.announce_leader()
    
    def announce_leader(self):
        # Announce victory only if this broker is not already the leader
        if not self.is_leader:
            for addr in self.cluster_address:
                if addr != (self.host, self.port):
                    self.send_victory_message(addr)
        self.is_leader = True
        self.current_leader = (self.host, self.port)
        print(f"\n\033[34mElection ended. Current leader: {self.current_leader}\033[0m")
    
    def send_election_message(self, addr):
        # Send an election message to the broker at addr
        try:
            election_message = f"ELECTION*{self.host}:{self.port}\n"
            self.cluster_sockets[addr].send(election_message.encode())
            print(f"\n{self.host}:{self.port} sending election message to {addr}")
        except Exception as e:
            print(f"\nError sending election message to {addr}: {e}")
    
    def send_victory_message(self, addr):
        # Announces to other brokers that the current broker has won the election.
        try:
            victory_message = f"VICTORY*{self.host}:{self.port}\n"
            self.cluster_sockets[addr].send(victory_message.encode())
            print(f"\n{self.host}:{self.port} sending the victory message to {addr}")
        except Exception as e:
            print(f"\nError sending victory message to {addr}: {e}")
        
    def respond_to_election(self, addr):
        try:
            # Respond to the sender indicating that this broker is still active
            response_message = f"ELECTION_ACK*{self.host}:{self.port}\n"
            self.cluster_sockets[addr].send(response_message.encode())
            print(f"\n{self.host}:{self.port} sending ack message to {addr}")
        except Exception as e:
            print(f"\nError responding to election message from {addr}: {e}")
    
    def start_election_thread(self):
        election_thread = threading.Thread(target=self.start_election)
        election_thread.start()
    
    def get_leader_address(self):
        return self.current_leader
    
    def handle_get_leader_address(self, client_socket):
        # Respond to the GET_LEADER_ADDRESS request by sending the current leader's address
        leader_address = f"{self.current_leader[0]}:{self.current_leader[1]}\n"
        client_socket.send(leader_address.encode())

    #gossip protocol
    def start_gossip_protocol(self):
        while True:
            # Check if there are no active brokers in cluster_sockets
            if not self.cluster_sockets:
                print("\n\033[33mNo active brokers in cluster_sockets. Gossip ended.\033[0m")
                break
            # Choose a random broker from the cluster to gossip with
            random_broker = random.choice(list(self.cluster_sockets.keys()))
            print(f"\nStarting gossip, {self.port} will gossip with: {random_broker}")
            # Send and receive gossip messages with the chosen broker
            self.send_gossip_message(random_broker)

            # Introduce a delay before the next round of gossip
            time.sleep(5)  # Adjust the interval as needed
    
    def send_gossip_message(self, addr):
        try:
            # Create a gossip message with relevant information
            details = json.dumps(self.get_current_broker_details())
            gossip_message = f"GOSSIP*{details}\n"
            self.cluster_sockets[addr].send(gossip_message.encode())  
            print(f"\nSent gossip message to {addr}")
        except Exception as e:
            print(f"\nError sending gossip message to {addr}: {e}")
            self.handle_broker_failure(addr)

    def process_gossip_data(self, details):
        # Update your broker's state based on the received gossip data
        sender_addr = tuple(details['addr'])
        sender_status = details['status']
        sender_subscribers = details['topic_subscribers']
        sender_last_updated = details['last_updated']
        print(sender_addr, sender_status, sender_subscribers, sender_last_updated)

        # Update your local information about the sender
        current_data = self.cluster_status.get(sender_addr, {})
        current_last_updated = current_data.get("last_updated", 0)
            
        if sender_last_updated > current_last_updated:
            # The received data is newer, update the local information
            self.cluster_status[sender_addr] = details
            print(f"\nUpdated cluster status from gossip: {sender_addr}")
        else:
            # The received data is older or the same, no action needed
            print(f"\nIgnored older gossip data from: {sender_addr}")
            
    def get_current_broker_details(self):
        details = {
            "addr": (self.host, self.port),
            "status": "UP",
            "topic_subscribers": self.topic_subscribers,
            "last_updated": time.time() # Add a timestamp
        }
        return details
    
    def handle_broker_failure(self, addr):
        print(f"\n\033[31mBroker at {addr} is considered failed.\033[0m")
        with self.lock:
            if addr in self.cluster_status:
                self.cluster_status[addr]['status'] = 'DOWN'
            if addr in self.cluster_sockets:
                del self.cluster_sockets[addr]
                print(f"\nRemoved failed broker {addr} from cluster sockets.")
            # Check if the failed broker was the current leader
            if self.current_leader == addr:
                print(f"\033[33mCurrent leader {addr} has failed. Initiating new election.\033[0m")
                self.start_election_thread()


def parse_args():
    parser = argparse.ArgumentParser(description='Traffic Broker')
    parser.add_argument('--host', default='localhost', help='Host for the broker')
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
    