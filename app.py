import json
from flask import Flask, abort, jsonify, render_template, redirect, request, session
import time
import subprocess

app = Flask(__name__)

# Global variables
broker = None
broker_containers = []
subscribers = {}

topics = ["Alameda", "Contra Costa", "Marin", "San Francisco", "San Mateo", "San Benito", "Santa Clara", "Napa",
          "Solano", "Sonoma", "Merced", "Santa Cruz", "San Joaquin", "Stanislaus"]


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
    print(container_name)
    for topic in selected_topics:
        if topic not in subscribers:
            subscribers[topic] = []
        subscribers[topic].append(subscriber_name)  
    # Store subscriber data in session
    #session['subscriber_data'] = {
    #    'subscriber_name': subscriber_name,
    #    'selected_topics': selected_topics
    #} 
    print("Sending data to subscribers", subscriber_name, selected_topics)
    result = subprocess.run(['docker', 'run', '-d', '--name', f'subscriber_{container_name}', '--network','traffic_network', 'subscriber_image', 'python3', './subscriber.py', 'broker1:8888','broker2:8889','broker3:8890', *selected_topics])
    if result.returncode == 0:
        # Redirect to subscriber.html on success
        return render_template('success.html', subscriber_name=subscriber_name, topics=selected_topics)
    else:
        return render_template('error.html')


@app.route('/publish-data', methods=['POST'])
def publish_data():
    selected_topics = request.form.get('selected_topics')
    subscriber_name = request.form.get('subscriber_name')
    container_name = ''.join(subscriber_name.split())
    # TODO: Implement logic to process the submitted data
    # For now, just print the values to the terminal
    print('Subscriber Name:', subscriber_name)
    print('Selected Topics:', selected_topics)
    
    # TODO: Run the publisher to publish data
    result = subprocess.run(['docker', 'run', '-d', '--name', f'publisher_{container_name}', '--network', 'traffic_network', 'publisher_image', 'python3', './publisher.py', 'broker1:8888', 'broker2:8889', 'broker3:8890'], capture_output=True, text=True)
    if result.returncode != 0:
        abort(500, description=f"Failed to start Docker container: {result.stderr}")
    
    # TODO: Implement logic to read data from the subscriber container

    # Render a template or return a response as needed
    return render_template('subscriber_data.html', subscriber_name=subscriber_name, topics=selected_topics)





if __name__ == "__main__":
    # Specify the port for the Flask app
    flask_app_port = 5002

    # Optionally, add a small delay to ensure the broker is fully up
    time.sleep(1)

    # Start Flask app
    app.run(host='0.0.0.0', port=flask_app_port, debug=True)
