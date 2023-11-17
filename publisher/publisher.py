import json
import socket
import time
from dataclasses import asdict
from traffic_data_fetcher import TrafficDataFetcher
from traffic_data_fetcher import Event


def get_leader_address(broker_address):
    try:
        leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        leader_socket.connect(broker_address)
        # Send a request for the current leader's address
        leader_socket.send("GET_LEADER_ADDRESS\n".encode())
        # Receive the leader's address as "<host>:<port>"
        leader_address = leader_socket.recv(1024).decode()
        print("Leader broker address", leader_address)
        # Convert the leader's address to a tuple (host, port)
        leader_host, leader_port = leader_address.split(":")
        leader_address = (leader_host, int(leader_port))
        return leader_address
    
    except (socket.error, ConnectionRefusedError) as e:
        print(f"Error getting leader address: {e}")
        # Handle the error, e.g., return a default address or raise an exception
        return None  # Return a default value or None to indicate failure

def publisher(broker_address):
    leader_address = get_leader_address(broker_address)
    if leader_address is None:
        print("Failed to retrieve the leader's address. Exiting.")
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as publisher_socket:
        try:
            publisher_socket.connect(leader_address)  # Connect to the broker
            print(f"Connected to broker at {leader_address}")
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
                    message = f"PUBLISH*{topic}*{json.dumps(event_dict)}\n"
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
    publisher(broker_address)