import socket
import json
import sys
import time

def subscriber(subscriber_name, topics):
    subscriber_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    subscriber_socket.connect(('localhost', 8888))  # Connect to the broker

    # Subscribe to each topic
    for topic in topics:
        subscriber_socket.send(f"SUBSCRIBE*{topic}".encode())
        time.sleep(0.1)

    try:
        while True:
            message = subscriber_socket.recv(1024).decode()

            # Note:
            # Subscriber code should not expect to receive the command "PUBLISH" or the topic as part of the message. 
            # It should only expect to receive the data, which is a JSON string.
            if message:
                # Parse the JSON data
                event_data = json.loads(message)
                
                # Check if the event's area is one of the interested topics
                if event_data["area"] in topics:
                    # Process the event data (you can modify this part as needed)
                    print(f"Subscriber {subscriber_name} received traffic event:")
                    print(f"Event ID: {event_data['event_id']}")
                    print(f"Area: \033[91m{event_data['area']}\033[0m")
                    print(f"Event Type: {event_data['event_type']}")
                    print(f"Headline: {event_data['headline']}")
                    print(f"Updated: {event_data['updated']}")
                    print()
    except KeyboardInterrupt:
        print(f"Subscriber {subscriber_name} is shutting down.")
    finally:
        subscriber_socket.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python subscriber.py <subscriber_name> <topic1> <topic2> ...")
    else:
        subscriber_name = sys.argv[1]
        interested_topics = sys.argv[2:]
        subscriber(subscriber_name, interested_topics)

    
    """Topic(area) List:
        Alameda
        Contra Costa
        Marin
        San Francisco
        San Mateo
        San Benito
        Santa Clara
        Napa
        Solano
        Sonoma
        Merced
        Santa Cruz
        San Joaquin
        Stanislaus
    """