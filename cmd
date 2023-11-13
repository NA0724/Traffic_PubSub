#!/bin/zsh

osascript -e 'tell app "Terminal" 
	do script "python3 ./Desktop/Traffic_PubSub/broker/broker.py --port 8889 --cluster localhost:8888 localhost:8890"
end tell'

osascript -e 'tell app "Terminal" 
	do script "python3 ./Desktop/Traffic_PubSub/broker/broker.py --port 8890 --cluster localhost:8888 localhost:8889"
end tell'

osascript -e 'tell app "Terminal" 
	do script "python3 ./Desktop/Traffic_PubSub/broker/broker.py --port 8888 --cluster localhost:8889 localhost:8890"
end tell'
