import json
import socket
import time
from dataclasses import asdict
from traffic_data_fetcher import TrafficDataFetcher, Event

class GossipPublisher:
    # Gossip protopol
    def __init__(self, host, port, api_url, api_key):
        self.host = host
        self.port = port
        self.fetcher = TrafficDataFetcher(api_url=api_url, api_key=api_key)

    def connect_to_broker(self): # Brokers registration using Resource discovery and Allocation alorithm
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to broker at {self.host}:{self.port}")
            return True
        except socket.error as e:
            print(f"Failed to connect to broker: {e}")
            return False

    def publish_events(self): # Replication and Concurrency control to prevent data discrepancy
        try:
            raw_data = self.fetcher.fetch_data("events")
            if raw_data:
                self.fetcher.extract_data(raw_data)
                events = self.fetcher.get_fetched_events()
                for event in events:
                    self.publish_event(event)
                    time.sleep(0.1)  # Timestamp
            else:
                print("No raw data available.")
        except KeyboardInterrupt:
            print("Publisher interrupted.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def publish_event(self, event):
        topic = event.area
        event_dict = asdict(event)
        message = f"PUBLISH {topic} {json.dumps(event_dict)}"
        print("Sending data:", message)
        self.socket.sendall(message.encode('utf-8'))
        print("Data sent\n")

    def close_connection(self):
        self.socket.close()
        print("Disconnected from broker.")

if __name__ == "__main__":
    broker_host = 'localhost'
    broker_port = 8888
    api_url = "http://api.511.org/traffic/"
    api_key = "9d297b1d-eb23-4a0c-bd71-ec8bd076ab10"

    publisher = GossipPublisher(broker_host, broker_port, api_url, api_key)
    if publisher.connect_to_broker():
        publisher.publish_events()
        publisher.close_connection()
