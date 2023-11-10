import json
import socket
import time
from dataclasses import asdict
from traffic_data_fetcher import TrafficDataFetcher
from traffic_data_fetcher import Event

def publisher(host, por, broker_address):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as publisher_socket:
        try:
            publisher_socket.connect(broker_address)  # Connect to the broker
            print(f"Connected to broker at {broker_address}")
        except ConnectionError as e:
            print(f"Failed to connect to broker: {e}")
            return

        fetcher = TrafficDataFetcher(api_url="http://api.511.org/traffic/", api_key="9d297b1d-eb23-4a0c-bd71-ec8bd076ab10")

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
                    message = f"PUBLISH*{topic}*{json.dumps(event_dict)}"
                    print("Sending data:", message)
                    publisher_socket.sendall(message.encode('utf-8'))
                    print("Data sent\n")
                    # Optionally, add a delay between sending individual events
                    time.sleep(0.1)
            else:
                print("No raw data")

        except KeyboardInterrupt:
            print("Publisher interrupted.")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    broker_host = 'localhost'
    broker_port = 8888
    #publisher(broker_host, broker_port)
    broker_address = (broker_host, broker_port)
    publisher(broker_host, broker_port, broker_address)