
from hematite import Client

client = Client()

resp = client.get('http://en.wikipedia.org/wiki/Coffee')
resp_data = resp.get_data()

print resp_data[:1024]
