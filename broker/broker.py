import socket
import threading
import multiprocessing

class TrafficBroker:
    def __init__(self, host, port, cluster_address=None):
        self.topic_subscribers = {}
        self.lock = threading.Lock()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(5)
        self.cluster_manager = None
        self.cluster_address = cluster_address
        if self.cluster_address:
            self.setup_cluster()

        print(f"Broker listening on {host}:{port}")
        
    
    def setup_cluster(self):
        self.cluster_manager = multiprocessing.Manager()
        self.shared_subscribers = self.cluster_manager.dict()

        # Connect to other brokers in the cluster
        for addr in self.cluster_address:
            self.connect_to_cluster_node(addr)

    def connect_to_cluster_node(self, addr):
        # Implement a mechanism to connect to other brokers in the cluster
        try:
            cluster_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cluster_socket.connect(addr)
            print(f"Connected to cluster node at {addr}")
            
            # Send information about the local broker (e.g., address)
            local_info = f"LOCAL_INFO*{self.server.getsockname()}"
            cluster_socket.send(local_info.encode())

            # Receive information about the remote broker
            remote_info = cluster_socket.recv(1024).decode()
            print(f"Received remote info: {remote_info}")

            # Parse the received information and update local state accordingly

        except Exception as e:
            print(f"Error connecting to cluster node at {addr}: {e}")

        finally:
            cluster_socket.close()
        #pass


    def handle_client(self, client_socket):
        while True:
            message = client_socket.recv(1024).decode()
            if not message:
                print(f"Client {client_socket} disconnected.")
                break
            # Handle the message
            print("Got message: ", message)
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
                                subscriber.send(data.encode())
                            except socket.error as e:
                                disconnected_subscribers.append(subscriber)
                        for subscriber in disconnected_subscribers:
                            self.topic_subscribers[topic].remove(subscriber)
                        
            else:
                client_socket.send("Invalid command".encode())

        client_socket.close()

    def run(self):
        while True:
            client_socket, addr = self.server.accept()
            print(f"Accepted connection from {addr}")
            client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_handler.start()

if __name__ == "__main__":
    # Example: broker1
    broker1 = TrafficBroker('localhost', 8888, cluster_address=[('localhost', 8889)])
    broker1.run()

    # Example: broker2 (in the same script or run separately)
    broker2 = TrafficBroker('localhost', 8889, cluster_address=[('localhost', 8888)])
    broker2.run()
