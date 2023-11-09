import socket
import threading

class TrafficBroker:
    def __init__(self):
        self.topic_subscribers = {}
        self.lock = threading.Lock()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', 8888))
        self.server.listen(5)
        print("Broker listening on port 8888")

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
    broker = TrafficBroker()
    broker.run()
