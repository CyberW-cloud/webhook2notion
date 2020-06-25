import upwork
from upwork.routers import auth
import os


def get_desktop_client():
    config = upwork.Config({
          'consumer_key': os.environ.get("ConsumerKey"),            
          'consumer_secret': os.environ.get("ConsumerSecret"),            
          'access_token': os.environ.get("AccessToken"),            
          'access_token_secret': os.environ.get("AccessSecret")})
     
    client = upwork.Client(config)
    try:        
        config.access_token        
        config.access_token_secret
    except AttributeError:
        print('Token Error')
    return client