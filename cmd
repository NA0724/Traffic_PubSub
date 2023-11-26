#!/bin/zsh

osascript -e 'tell app "Terminal" 
	do script "python3 ./Traffic_PubSub/broker/broker.py --host localhost --port 8889 --cluster localhost:8888 localhost:8890"
end tell'

osascript -e 'tell app "Terminal" 
	do script "python3 ./Traffic_PubSub/broker/broker.py --host localhost --port 8890 --cluster localhost:8888 localhost:8889"
end tell'

osascript -e 'tell app "Terminal" 
	do script "python3 ./Traffic_PubSub/broker/broker.py --host localhost --port 8888 --cluster localhost:8889 localhost:8890"
end tell'