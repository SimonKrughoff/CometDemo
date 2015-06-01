# Comet VOEvent Broker.
# Example event handler: write an event to file.
# John Swinbank, <swinbank@trtransientskp.org>.

import requests 
from zope.interface import implementer
from twisted.plugin import IPlugin

from comet.icomet import IHandler, IHasOptions

def check_response(response):
    return (response.text == 'success')

def post_event(event, baseUrl, filterName):
    values = {'event':event.text}
    print values
    print baseUrl+'/'+filterName
    if not baseUrl.startswith('http'):
        baseUrl = 'http://'+baseUrl
    response = requests.post(baseUrl+'/'+filterName, data=values)
    if not check_response(response):
        raise IOError('Could not post message')


# Event handlers must implement IPlugin and IHandler.
# Implementing IHasOptions enables us to use command line options.
@implementer(IPlugin, IHandler, IHasOptions)
class EventPoster(object):

    # The name attribute enables the user to specify plugins they want on the
    # command line.
    name = "event-poster"

    def __init__(self):
        self.baseUrl = 'http://localhost:8880'

    # When the handler is called, it is passed an instance of
    # comet.utility.xml.xml_document.
    def __call__(self, event):
        """
        Send with GET message to HipChat.
        """
        print "Here"
        post_event(event, self.baseUrl, self.filterName)

    def get_options(self):
        return [('postUrl', None, 'base URL to POST to'),
                ('filterName', self.baseUrl, 'name of page to post to'),]

    def set_option(self, name, value):
        if name == 'postUrl':
            self.baseUrl = value
        if name == 'filterName':
            self.filterName = value

# This instance of the handler is what actually constitutes our plugin.
event_poster = EventPoster()
