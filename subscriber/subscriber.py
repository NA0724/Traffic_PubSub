import socket
import json
import sys
import time

def subscriber(subscriber_name, topics, broker_address):
    while True:
        subscriber_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            # Connect to the broker
            leader_address = get_leader_address(broker_address)
            subscriber_socket.connect(leader_address)
            print("Connected to broker:" ,leader_address)
        
            # Subscribe to each topic
            for topic in topics:
                subscriber_socket.send(f"SUBSCRIBE*{topic}\n".encode())
                time.sleep(0.1)
        
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
        except ConnectionResetError:
            print("Connection reset by peer. Broker may have terminated. Attempting to reconnect...")
        except KeyboardInterrupt:
            print(f"Subscriber {subscriber_name} is shutting down.")
            break
        finally:
            subscriber_socket.close()


def get_leader_address(broker_address):
    try:
        leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        leader_socket.connect(broker_address)
        # Send a request for the current leader's address
        leader_socket.send("GET_LEADER_ADDRESS\n".encode())
        # Receive the leader's address as "<host>:<port>"
        leader_address = leader_socket.recv(1024).decode()
        # Convert the leader's address to a tuple (host, port)
        leader_host, leader_port = leader_address.split(":")
        leader_address = (leader_host, int(leader_port))

        return leader_address
    except (socket.error, ConnectionRefusedError) as e:
        print(f"Error getting leader address: {e}")
        # Handle the error, e.g., return a default address or raise an exception
        return None  # Return a default value or None to indicate failure

if __name__ == "__main__":
    """if len(sys.argv) < 2:
        print("Usage: python subscriber.py <subscriber_name> <topic1> <topic2> ...")
    else:
        subscriber_name = sys.argv[1]
        interested_topics = sys.argv[2:]
        subscriber(subscriber_name, interested_topics)
    """
    if len(sys.argv) < 3:
        print("Usage: python subscriber.py <subscriber_name> <broker_address> <topic1> <topic2> ... ")
    else:
        subscriber_name = sys.argv[1]
        broker_address = (sys.argv[2], 8888)
        interested_topics = sys.argv[3:]
        #subscriber(subscriber_name, interested_topics, broker_address)
        while True:
            subscriber(subscriber_name, interested_topics, broker_address)
            print("Reconnecting to a new leader in 2 seconds...")
            time.sleep(2)
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