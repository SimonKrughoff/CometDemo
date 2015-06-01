# Imports
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor

import cgi, shutil, os, signal, tempfile, subprocess

# Globals to keep track of spawned processes
procDict = {}
filterInfo = {}


def runSubscriber(brokerAddress, filterString, filterName, postUrl):
    """ Run an instance of comet in subscriber mode.  I this mode it only provides a filter
    and a plugin to run on each alert.  In this example, it runs the plugin to post to this 
    web listener.

    @param[in] brokerAddress  Address of the broker (typically localhost:8809
    @param[in] filterString  XPATH filter string to use as the filter
    @param[in] filterName  Short name used to refer to this subscriber
    @param[in] postUrl  Base url of the web listener to post to
    @return PID of the subscriber process and the directory on the filesystem where the process is running
    """

    command_str = "twistd comet --remote={brokerAddress} --local-ivo={ivorn} "+\
                  "--eventdb={eventdbdir} --event-poster --event-poster-postUrl={postUrl} "+\
                  "--event-poster-filterName={filterName} --filter={filterString}"

    rundir = tempfile.mkdtemp()
    ivorn = 'ivo://me.mysubscriber/%s'%(filterName)
    args = {'brokerAddress':brokerAddress, 'ivorn':ivorn, 'eventdbdir':rundir, 'postUrl':postUrl, 
            'filterName':filterName, 'filterString':filterString}
    os.chdir(rundir)
    print "Running new subscriber in directory %s"%rundir
    comm_str = command_str.format(**args)
    subprocess.call(comm_str.split())
    fh = open('twistd.pid')
    pid = fh.readline().rstrip()
    return int(pid), rundir

def add_page(name, filterString):
    """ Add a page to this web listener.
    @param[in] name  Name of the page to add (this is also an identifier for the filter)
    @param[in] filterString  String containing the XPATH filter string
    """

    root.putChild(name, PostPage())
    if name in filterInfo:
        filterInfo[name].append(filterString)
    else:
        filterInfo[name] = [filterString,]

def add_proc(proc, rundir):
    """ Update the dictionary with proc information
    @param[in] proc  Process PID
    @param[in] rundir Absolute path to the directory where the process is running
    """
    procDict[rundir] = proc

def tearDown(*args, **kwargs):
    """ Clean up by killing all spawned processes.
    """
    for k in procDict:
        print "Cleaning up from pid %i at %s"%(procDict[k], k)
        os.kill(procDict[k], signal.SIGQUIT)
        shutil.rmtree(k)

class PostPage(Resource):
    """ This is the page where alerts that pass a certain filter are posted.
    """
    def __init__(self, *args, **kwargs):
        """ Add a class variable to hold the alert text
        """
        self.pageTxt = "<hr>\n"
        Resource.__init__(self, *args, **kwargs)

    def render_GET(self, request):
        """ This allows users to use this endpoint to view the alerts
        @param[in] request  The request object
        @returns a formatted string to be rendered by the browser
        """
        return '<head><meta http-equiv="refresh" content="3"></head><html><body>'+self.pageTxt+"</body></html>"

    def render_POST(self, request):
        """ Recieve alert packet.
        @param[in] request The request object containing the alert
        @return a string indicating success
        """
        tstr = cgi.escape(request.args["event"][0])
        self.pageTxt += tstr.replace('\n','<br>').replace(' ', '&nbsp;')
        self.pageTxt += "<hr>\n"
        return 'success'

class FormPage(Resource):
    """ This is the page that registers the filter and spawnes the subscriber
    """
    def render_GET(self, request):
        """ Render the form and info on previously registered filters
        @param[in] request Request object
        @returns a formatted string to be rendered by the browser
        """
        tabString = ''
        for k in filterInfo:
            tabString += '<tr><td><a href="http://localhost:8880/%s">%s</a></td><td>%s</td></tr>'%(k,k, ",".join(filterInfo[k]))
        return '<html><body><form method="POST">'+\
               '<b>Broker Address: </b><input name="broker-address" value="localhost:8809" type="text"/><br>'+\
               '<b>Filter String: </b><input name="filter-string" value="." type="text"/><br>'+\
               '<b>Filter Name: </b><input name="filter-name" value="AllAlerts" type="text"/><br>'+\
               '<input type="submit" value="Submit">'+\
               '</form>'+\
               '<hr><br><b>Installed filters'+\
               '<table>'+\
               '<tr><td>Filter Name</td><td>Filter String(s)</td></tr>%s'%(tabString)+\
               '</body></html>'

    def render_POST(self, request):
        """ Handle the post request from the form rendered in render_GET
        @param[in] request Request object
        @return a string containing the URL of the generated filter endpoint
        """
        add_page(cgi.escape(request.args['filter-name'][0]), request.args['filter-string'][0])
        pid, rundir = runSubscriber(request.args['broker-address'][0], request.args['filter-string'][0],
                      cgi.escape(request.args['filter-name'][0]), 'localhost:8880')
        add_proc(pid, rundir)
        return '<html><body>Click <a href="http://localhost:8880/%s">here</a> to view events. '%cgi.escape(request.args['filter-name'][0])+\
               'Or go <a href="http://localhost:8880/">back</a> to the registry page.</body></html>'

""" Spin up the web server and register the tear down callback.
"""
root = Resource()
root.putChild("", FormPage())
factory = Site(root)
reactor.listenTCP(8880, factory)
reactor.addSystemEventTrigger('before', 'shutdown', tearDown)
reactor.run()