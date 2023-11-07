import socket
import json
import time
from dataclasses import asdict
from event.traffic_data_fetcher import TrafficDataFetcher  # make sure to import your fetcher
from event.traffic_data_fetcher import Event

def publisher(host, port):
    try:
        publisher_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        publisher_socket.connect((host, port))  # Connect to the broker
        print(f"Connected to broker at {host}:{port}")
    except ConnectionError as e:
        print(f"Failed to connect to broker: {e}")
        return

    fetcher = TrafficDataFetcher(api_url="http://api.traffic.com", api_key="your_api_key")

    try:
        raw_data = fetcher.fetch_data("events")  # Get JSON data from the TrafficDataFetcher class
        if raw_data:
            # Get the processed events
            fetcher.extract_data(raw_data) 
            events = fetcher.get_fetched_events()
            # Clear the fetched events after processing
            fetcher.events_fetched.clear()
            
            for event in events:
                # Use the 'area' attribute of the event as the topic
                topic = event.area
                # Convert the event object to a JSON-serializable dictionary
                event_dict = asdict(event)
                # Include the topic in the message
                message = json.dumps({'topic': topic, 'event': event_dict})
                publisher_socket.sendall(message.encode('utf-8'))
                # Optionally, add a delay between sending individual events
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("Publisher interrupted.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        publisher_socket.close()

if __name__ == "__main__":
    broker_host = 'localhost'
    broker_port = 8888
    publisher(broker_host, broker_port)
