import json
from flask import Flask, abort, jsonify, render_template, redirect, request, session
import time
import queue
import logging
import docker
import copy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

topics = ["Alameda", "Contra Costa", "Marin", "San Francisco", "San Mateo", "San Benito", "Santa Clara", "Napa",
          "Solano", "Sonoma", "Merced", "Santa Cruz", "San Joaquin", "Stanislaus"]
client = docker.from_env()
# # Use a queue to store received data in a thread-safe manner
# data_queue = queue.Queue()
# subscribed_events = {}

#current_subscriber = ''
subscribers = {}
events = []
# Render the home page
@app.route('/')
def homepage():
    return render_template('index.html', topics=topics)
    

# Subscriber method gets the subscriber name and topics selected from frontend and runs the subscriber container with those details
@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    #global current_subscriber 
    selected_topics = request.form.getlist('topics')
    subscriber_name = request.form.get('name')
    container_name = ''.join(subscriber_name.split())
    t = {' '.join(map(lambda x: f'"{x}"', selected_topics))}
    logger.info(f"Sending data to subscribers: {subscriber_name},  topics={t}")
    try:
        container = client.containers.run("subscriber_image",
                        command="python3 ./subscriber.py broker1:8888 broker2:8889 broker3:8890 {}".format(' '.join(map(lambda x: '"{}"'.format(x), selected_topics))),
                        name="subscriber_{}".format(container_name),
                        network="traffic_network",
                        detach=True)
        # Get details about the container by ID or name
        container_id = container.id
        # Use the container ID to get the container instance
        container_instance = client.containers.get(container_id)
        # Get the bridge network information
        bridge_network_info = container_instance.attrs['NetworkSettings']['Networks']['traffic_network']
        # Update the subscribers dictionary
        subscribers[subscriber_name] = {
            'container_name': container_name,
            'ip_address': bridge_network_info['IPAddress'],
            'topics': selected_topics,
        }
        
        publisher_container = client.containers.run("publisher_image", 
                                      command="python3 ./publisher.py broker1:8888 broker2:8889 broker3:8890 " ,
                                      name=f"publisher_{container_name}",
                                      network="traffic_network",
                                      detach=True)
        
        return render_template('success.html', subscriber_name=subscriber_name, topics=selected_topics)
        # Additional code to manage or inspect the container
    except docker.errors.ContainerError as e:
        # Handle container errors
        logger.error(f"Container error: {e}")
    except docker.errors.ImageNotFound as e:
        # Handle case where the image is not found
        logger.error(f"Image not found: {e}")
    except docker.errors.APIError as e:
        # Handle other Docker API errors
        logger.error(f"Docker API error: {e}")
    except Exception as e:
        logger.error(f"Error running subprocess: {e}")
    
    return render_template('error.html')

@app.route('/publish-data/<subscriber_name>', methods=['POST'])
def publish_data(subscriber_name):
    # container_name = ''.join(subscriber_name.split())
    
    try:
    #     container = client.containers.run("publisher_image", 
    #                                   command="python3 ./publisher.py broker1:8888 broker2:8889 broker3:8890 " ,
    #                                   name=f"publisher_{container_name}",
    #                                   network="traffic_network",
    #                                   detach=True)
        #logger.info(f"Is subscriber events empty?: {not bool(subscribed_events)}")
        #logger.info(f"{subscribed_events[current_subscriber]}")
        if subscriber_name in subscribers:
            logger.info(f"Events for {subscriber_name}: {subscribers[subscriber_name]}")
            # event = list(data_queue.queue)
            logger.info(f"Data event: {events}")
            return render_template('subscriber_data.html', subscriber_name=subscriber_name, event=events)
        else:
            logger.warning(f"No events found for subscriber {subscriber_name}")
            return jsonify({'status': 'error', 'message': 'No events found'}), 404
        # Additional code to manage or inspect the container
    except docker.errors.ContainerError as e:
        # Handle container errors
        logger.error(f"Container error: {e}")
    except docker.errors.ImageNotFound as e:
        # Handle case where the image is not found
        logger.error(f"Image not found: {e}")
    except docker.errors.APIError as e:
        # Handle other Docker API errors
        logger.error(f"Docker API error: {e}")
    except Exception as e:
        logger.error(f"Error running subprocess: {e}")
    
    return render_template('error.html')

@app.route('/subscriber_data', methods=['GET','POST'])
def subscriber_data():
    try:
        # Assuming the incoming data is a dictionary
        data = request.json
        logger.info(f"Incoming data: {data}")
        
        for ip_address, events in data.items():
            # Find the matching subscriber for the given IP address
            matching_subscriber = None
            for subscriber_name, details in subscribers.items():
                if details['ip_address'] == ip_address:
                    matching_subscriber = subscriber_name
                    break
            
            if matching_subscriber:
                process_data(events)
            else:
                logger.warning(f"No matching subscriber found for IP {ip_address}")

        return jsonify({'status': 'success', 'data': data}), 200

    except Exception as e:
        # Handle any exceptions that might occur during data processing
        logger.exception(f"Error processing data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_data(data):
    global events
    events = data


if __name__ == "__main__":
    # Specify the port for the Flask app
    flask_app_port = 5002

    # Optionally, add a small delay to ensure the broker is fully up
    time.sleep(1)

    # Start Flask app
    app.run(host='0.0.0.0', port=flask_app_port, debug=True)
