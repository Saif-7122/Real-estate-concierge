import urllib.request
import json

url = 'http://localhost:8080/api/chat'
data = json.dumps({"message":"hi", "thread_id":"test-123", "buyer_profile": {}}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except Exception as e:
    print(e)
