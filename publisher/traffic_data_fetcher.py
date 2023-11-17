from dataclasses import dataclass
import requests
import json

# A data class that defines the structure for storing traffic event data
@dataclass
class Event:
    event_id: str         # Unique id
    area: str
    event_type: str
    headline: str
    updated: str

# A class that handles fetching and extracting traffic data from a given API endpoint
class TrafficDataFetcher:

    def __init__(self, api_url, api_key):
        self.api_url = api_url
        self.api_key = api_key
        self.events_fetched = []

    # Retrieve data from the API
    def fetch_data(self, endpoint):
        full_url = f"{self.api_url}{endpoint}?api_key={self.api_key}"
        try:
            response = requests.get(full_url)
            response.raise_for_status()
            # Adjusting decoding for potential UTF-8 BOM
            content = response.content.decode('utf-8-sig')
            return json.loads(content)
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            return None
    
    # Parse the JSON response and create 'Event' objects for each event
    def extract_data(self, raw_data):
        # Extract events
        events_data = raw_data.get('events', [])
        for event_data in events_data:
            event_id = event_data.get('id')
            event_type = event_data.get('event_type')
            headline = event_data.get('headline')
            updated = event_data.get('updated')
            areas = event_data.get('areas', [])
            for area in areas:
                area_name = area.get('name')
                # Create an Event object for each field
                event = Event(event_id, area_name, event_type, headline, updated)
                self.events_fetched.append(event)
                
    # Return the list of fetched 'Event' objects
    def get_fetched_events(self):
        return self.events_fetched

"""
A simple test code 
This test part can be used in our main program


if __name__ == '__main__':
    # Create an instance of the fetcher with the base API URL and the API key.
    base_url = "http://api.511.org/traffic/"
    api_key = "9d297b1d-eb23-4a0c-bd71-ec8bd076ab10"  
    fetcher = TrafficDataFetcher(base_url, api_key)

    # Endpoint for traffic events
    endpoint = "events"

    # Fetch and process the traffic data.
    raw_data = fetcher.fetch_data(endpoint)
    fetcher.extract_data(raw_data)
    
    # Get the processed events
    event_list = fetcher.get_fetched_events()
    for event in event_list:
        print(event)
        print()

"""