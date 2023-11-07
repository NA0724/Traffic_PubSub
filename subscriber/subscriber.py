import socket
import json
import sys

def subscriber(subscriber_name):
    subscriber_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    subscriber_socket.connect(('localhost', 8888))  # Connect to the broker

    topic = "traffic_notifications"  # Specify the topic
    subscriber_socket.send(f"SUBSCRIBE {topic}".encode())

    while True:
        message = subscriber_socket.recv(1024).decode()

        # Split the received message into parts
        parts = message.split(" ")
        if len(parts) == 3 and parts[0] == "PUBLISH":
            published_topic, json_data = parts[1], parts[2]

            if published_topic == topic:
                # Parse the JSON data
                event_data = json.loads(json_data)

                # Process the event data (you can modify this part as needed)
                print(f"Subscriber {subscriber_name} received traffic event:")
                print(f"Event ID: {event_data['event_id']}")
                print(f"Area: {event_data['area']}")
                print(f"Event Type: {event_data['event_type']}")
                print(f"Headline: {event_data['headline']}")
                print(f"Updated: {event_data['updated']}")
                print()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python subscriber.py <subscriber_name>")
    else:
        subscriber_name = sys.argv[1]
        subscriber(subscriber_name)
