import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crypto_monitor.settings')
os.environ['ALLOWED_HOSTS'] = 'localhost,127.0.0.1,testserver'
import django
django.setup()
from django.test import Client

client = Client()
response = client.get('/search/?q=BTC', HTTP_HOST='testserver')
content = response.content.decode('utf-8')

# Search for the percentile values in the rendered HTML
for term in ['75.7%', '84.0%', '75.0%', '100.0%', '75.7', '84.0', '75.0', '100.0']:
    idx = content.find(term)
    if idx >= 0:
        print('Found "' + term + '" at position ' + str(idx))
        print(content[max(0,idx-50):idx+50])
        print('---')
    else:
        print('"' + term + '" NOT FOUND')