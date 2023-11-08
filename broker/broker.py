import socket
import threading

class TrafficBroker:
    def __init__(self):
        self.topic_subscribers = {}
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('0.0.0.0', 8888))
        self.server.listen(5)
        print("Broker listening on port 8888")

    def handle_client(self, client_socket):
        while True:
            message = client_socket.recv(1024).decode()
            if not message:
                print("No message")
                break
            parts = message.split("*")
            if len(parts) == 3:
                command, topic, data = parts
                print(command, topic, data)
                if command == "SUBSCRIBE":
                    if topic not in self.topic_subscribers:
                        self.topic_subscribers[topic] = []
                    self.topic_subscribers[topic].append(client_socket)
                elif command == "PUBLISH":
                    if topic in self.topic_subscribers:
                        for subscriber in self.topic_subscribers[topic]:
                            subscriber.send(data.encode())

            else:
                client_socket.send("Invalid command".encode())

        client_socket.close()

    def run(self):
        while True:
            client_socket, addr = self.server.accept()
            client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_handler.start()

if __name__ == "__main__":
    broker = TrafficBroker()
    broker.run()
