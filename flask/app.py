import json
from flask import Flask, abort, jsonify, render_template, redirect, request, session
import time
import subprocess
import logging
import docker

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


# Render the home page
@app.route('/')
def homepage():
    return render_template('index.html', topics=topics)
    

# Subscriber method gets the subscriber name and topics selected from frontend and runs the subscriber container with those details
@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
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
                        detach=True
                )   

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
    container_name = ''.join(subscriber_name.split())
    
    try:
        container = client.containers.run("publisher_image", 
                                      command="python3 ./publisher.py broker1:8888 broker2:8889 broker3:8890 " ,
                                      name=f"publisher_{container_name}",
                                      network="traffic_network",
                                      detach=True)
        return render_template('subscriber_data.html', subscriber_name=subscriber_name)
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

@app.route('/subscriber_data', methods=['POST'])
def subscriber_data():
    try:
        # Assuming the incoming data is a dictionary
        data = request.get_json()

        # Process the data as needed
        # For now, just print it to the console
        print('Received data:', data)
        return data

    except Exception as e:
        # Handle any exceptions that might occur during data processing
        print(f"Error processing data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500



if __name__ == "__main__":
    # Specify the port for the Flask app
    flask_app_port = 5002

    # Optionally, add a small delay to ensure the broker is fully up
    time.sleep(1)

    # Start Flask app
    app.run(host='0.0.0.0', port=flask_app_port, debug=True)
