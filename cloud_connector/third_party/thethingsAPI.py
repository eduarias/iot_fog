"""
https://github.com/theThings/thethings.iO-python-library
"""
import urllib
import urllib2
import json
import httplib
import Queue
import threading
import time
import datetime


class thethingsiO(object): # pragma: no cover

    URLROOT = "https://api.thethings.io/v2/things/"
    HEADERS_WRITE = {"Accept": "application/json", "Content-Type": "application/json"}
    HEADERS_READ = {"Accept": "application/json"}
    HEADERS_ACT = {"Accept": "application/json", "Content-Type": "application/json"}
    HEADERS_SUBS = {"Content-Type": "application/json"}

    _token = ""
    _urlWrite = ""
    _urlRead = ""
    _urlAct = ""
    _urlSubs = ""

    _data = []

    def __init__(self, token=None):
        if (token is not None):
            self.__initData(token)
        self._urlAct = self.URLROOT
        self._internalLogs = False
        self._sync = False
        self._monitorRes = None
        self._monitorAux = None

    # actCode: activation code
    def activate(self, actCode):
        """ Activates a non activated thing.

        Args:
            actCode: activation code string.
        Returns:
            true on sucess, False on malformed URL error.
            Any network problem raises an exception.
        Raises:
            URLError on errors (from urllib2.urlopen)"""

        data = '{"activationCode": "' + actCode + '"}'

        try:
            req = urllib2.Request(self._urlAct, data, self.HEADERS_ACT)
            response = urllib2.urlopen(req)
        except Exception:
            raise
        else:
            result = json.loads(response.read())
            if result["status"] == "created":
                self.__initData(result["thingToken"])
                return True
            else:
                print(result["message"])
                return False

    # key: string
    # value: number or string
    # dt: Custom timestamp format '2015-10-28T12:18:56.799Z' or datetime
    def addVar(self, key, value, dt=None):
        """ Add the pair {key : value} to the list of pending
        data to be written to thethings.io. This function can
        be called any times to add more variables to be sent.
        Call the "write" function to actually write the values.

        Args:
            key: string key to write.
            value: value
            dt: custom timestamp either string
            '2015-10-28T12:18:56.799Z' or
            python datetype.

        """

        if dt is None:
            self._data.append({'key': str(key), 'value': value})
        else:
            if not isinstance(dt, basestring):
                dt = TheThingsAPI.dt2str(dt)
                self._data.append({'key': str(key), 'value': value,
                                   'datetime': dt})


    def write(self):
        """ Actually write the values to theThings.iO. See
        function "addVar". internal list of data to be sent
        is cleared.

        Returns:
            Http code status
        Raises:
            URLError on errors (from urllib2.urlopen)

        """

        localData = {'values': self._data}
        localData = json.dumps(localData)
        ret = None
        try:
            req = urllib2.Request(self._urlWrite, localData, self.HEADERS_WRITE)
            response = urllib2.urlopen(req)
            ret = response.getcode()
        except Exception:
            raise
        else:
            self.clear()
        return ret

    def clear(self):
        """ Clear internal data buffer to be written """
        self._data = []

    def read(self, key, limit=1, startDate=None, endDate=None, to=10):
        """ Read a variable from the theThings.iO. If only the
        argument "key" is specified, the last value will be
        returned. This function will return "limit" number of
        values of the variable inside an array. The elements
        are returned from newest to oldest

        Args:
            key: name of the variable
            limit: max number of values to return.
            startDate: '2015-10-28T12:18:56.799Z' or datetime
            endDate: '2015-10-28T12:18:56.799Z' or datetime
            to: timeout in seconds
        Returns:
            None on connection timeout, 0 if the resource
            doesn't exist, otherwise a list with the readed
            values.
        """

        getUrl = self._urlRead + key + "/"
        getUrl += "?limit=" + str(limit)

        if startDate is not None:
            if not isinstance(startDate, basestring):
                startDate = TheThingsAPI.dt2str(startDate)
            getUrl += "&startDate=" + startDate
        if endDate is not None:
            if not isinstance(endDate, basestring):
                endDate = TheThingsAPI.dt2str(endDate)
            getUrl += "&endDate=" + endDate
        result = None
        try:
            req = urllib2.Request(getUrl, None, self.HEADERS_READ)
            response = urllib2.urlopen(req, timeout=to)
            result = json.loads(response.read())

        except Exception as e:
            if str(e) == "HTTP Error 404: Not Found":
                result = 0
            else:
                print "Error reading: " + str(e)

        return result

    def subscribe(self):
        """ Subscribe to thethings.iO. Calling this function
        will start a thread that will listen for incoming
        data from thethings.iO and will queue it as it is
        retrieved.

        Returns:
                A python queue to read the data.
        """

        queue = Queue.Queue()
        t = threading.Thread(target=self.__subscribeDaemon,
                args = (queue,))
        t.daemon = True
        t.start()

        return queue

    def activateSync(self, resource, act, auxResource=None):
        """ Turn on or off sync mechanism for subscribe.
        If sync is on, every time the class realises that
        the connection is lost, it will query thethings.io
        to recover lost data for a single specific resource.

        An auxiliary resource is needed to know which is
        the last processed data. i.e. Once internet connection is
        recovered, Sync will check the timestamp of the auxiliar
        resource (by default resource + "_ack") and the timestamp
        of the last value written for the specific resource
        that we want to recover lost data ("resource" argument
        of this function). If the timestamps differe, the
        subscribe thread will recover all the data between this
        two timestamps and will place it in the suscribe queue.

        Therefore, is the task of the user to:
         - Manually add a timestamp when writting the resource
           that we want to monitor (using third argument of
           addVar function).
         - Update the auxiliary resource with the timestamp
           of the last processed data. Otherwise, Sync may
           read an already processed value and put it again
           in the subscribe queue (to stash multiple data from
           once, it's enough to upddate the auxiliary resource
           with the oldest data). The function stashData can
           be used for this purpose.

        In summary, if Sync is on, after processing a value
        read from the subscribe queue, the function "stashData"
        should be called with the value of the timestamp of the
        readed value.

        Args:
                resource: resource that we want to recover
                        data if the connection is lost or the
                        application is closed.
                auxResource: name of the auxiliary resource.
        """

        self._sync = act
        self._monitorRes = resource
        if auxResource == None:
            self._monitorAux = resource + "_ack"
        else:
            self._monitorAux = auxResource


    def stashData(self, dt):
        """ Stash data up to dt datetime as processed. This
        function is only useful for the Sync feature. It won't
        return until the data has been written.

        Args:
                dt: datetime python object.
        """

        connected = False
        if not isinstance(dt, basestring):
            dt = TheThingsAPI.dt2str(dt)

        localLog = ('{"values":[{"key":"'+self._monitorAux +
                '","value":1, "datetime":"'+dt+'"}]}')

        while not connected:
            try:
                req = urllib2.Request(self._urlWrite,
                        localLog, self.HEADERS_WRITE)
                response = urllib2.urlopen(req)
            except Exception as e:
                print(("exception while trying to log: " +
                        str(e)))
                time.sleep(10)
            else:
                connected = True


    def getToken(self):
        """ Get function for internal token.

        Returns:
                current token.
        """

        return self._token

    def internalLogs(act):
        """ set on or off internal logs of this class
        that will provide information for developers. The
        logs will be written to thethings.io resources
        "err" and "log" for errors and other logs
        respectively.

        Args:
                act: true if on, false if off.

        """

        self._internalLogs = act

    @staticmethod
    def str2dt(strdate):
        """ Converts a formated string to python datetime.

        Args:
                strdate: string '2015-10-28T12:18:56.799Z'.
        Returns:
                datedime python object.
        """

        return datetime.datetime.strptime(strdate[:-1],
                "%Y-%m-%dT%H:%M:%S.%f")

    @staticmethod
    def dt2str(dt):
        """ Converts datetime python object to formated string.

        Args:
                dt: python datetime
        Returns:
                string '2015-10-28T12:18:56.799Z'.
        """

        aux = datetime.datetime.strftime(dt,"%Y-%m-%dT%H:%M:%S.%f")
        aux = aux[:-3] + "Z"

        return aux

    def __logWrite(self, txt):
        """ wrapper for __logWrite__ """
        if self._internalLogs:
            self.__logWrite__(txt)

    def __errWrite(self, txt):
        """ wrapper for __errWrite__ """
        if self._internalLogs:
            self.__errWrite__(txt)

    def __logWrite__(self, txt):
        """ Log internal events of this Class.

        Args:
                txt: text to log
        """
        localLog = '{"values":[{"key":"log","value":"'+ str(txt) + '"}]}'
        try:
            req = urllib2.Request(self._urlWrite, localLog,
            self.HEADERS_WRITE)
            response = urllib2.urlopen(req)
        except Exception as e:
            print("exception while trying to log: " +str(e))
            pass

    def __errWrite__(self, txt):
        """ Log internal events of this Class.

        Args:
                txt: text to log
        """
        localLog = '{"values":[{"key":"err","value":"'+ str(txt) + '"}]}'
        try:
            req = urllib2.Request(self._urlWrite, localLog,
            self.HEADERS_WRITE)
            response = urllib2.urlopen(req)
        except Exception as e:
            print("exception while trying to log: " +str(e))
            pass

    def __checkSync(self,queue):
        """ Check if there are values that have not been
        retrieved and get them.

        Args:
                queue: subscription queue.
        """
        resource = self._monitorRes
        ack = self._monitorAux

        print("synchronizing...")

        # get last ack timestamp
        connect = False
        data = None
        while not connect:
            data = self.read(ack)
            # can't connect, retry
            if data == None:
                print ("can't connect for sync")
                time.sleep(10)
            #resource not created yet
            elif data == 0:
                print ("resource empty, nothing to sync")
                return
            else:
                connect = True

        # read images since last ack to now
        maxl = 100
        nr = maxl

        dts = data[0]['datetime']
        dt = TheThingsAPI.str2dt(dts)
        dt += datetime.timedelta(milliseconds=1)

        start = dt
        end = None
        while maxl == nr:
            # try to retrive old resources
            connect = False
            while not connect:
                data = self.read(resource, limit=maxl,
                                 startDate=start, endDate=end)
                # can't connect, retry
                if data == None:
                    print ("can't connect for sync")
                    time.sleep(10)
                #resource not created yet
                elif data == 0:
                    print ("resource empty, nothing to sync")
                    return
                else:
                    connect = True

            # post process retrived resources if any
            nr = len(data)
            print("retrieved " + str(nr) + " lost files")

            if nr != 0:
                daux = []
                # adapting format of read data
                for d in data:
                    daux.append(
                         {'key':resource,
                          'value' : d['value'],
                          'datetime' : d['datetime']})

                # placing data to the queue
                queue.put(daux)

                if nr == maxl:
                    end = data[-1]['datetime']
                    end = TheThingsAPI.str2dt(end)
                    #end -= datetime.timedelta(milliseconds=1)

                    if end == start:
                        nr = 0

    def __subscribeDaemon(self, queue):
        """ Subscribe daemon wrapper """
        while True:
            try:
                self.__subscribeDaemonMain(queue)
            except Exception as e:
                msg=("Error in subscribe daemon "
                     "thread: " +str(e)+ " Restarting thread.")
                print(msg)
                self.__errWrite(msg)
                time.sleep(10)


    def __subscribeDaemonMain(self, queue):
        """ Main subscribe daemon  """
        while True:
            # Check if there are lost resources

            if self._sync:
                try:
                    self.__checkSync(queue)
                except Exception as e:
                    msg=("Error checking Sync: " + str(e))
                    print(msg)
                    self.__errWrite(msg)
                    time.sleep(10)
                    continue

            # send subscribe request
            try:
                conn = httplib.HTTPSConnection('api.thethings.io',
                timeout=10)
                conn.request('GET','/v2/things/' + self._token +
                '?keepAlive=60000', None, self.HEADERS_SUBS)
            except Exception as e:
                print "Connection Error, retrying: " + str(e)
                self.__errWrite("subscribe error: " +str(e))
                time.sleep(10)
                continue

            data = None
            r1 = None
            # Get first response
            try:
                r1 = conn.getresponse()
            except Exception as e:
                print "Error waiting first response: " + str(e)
                self.__errWrite("subscribe error: " +str(e))
                continue


            # Retrieving first response
            try:
                data = self.__parse(r1)
            except Exception as e:
                print "error waiting success: " + str(e)
                self.__errWrite("subscribe error: " +str(e))
                continue

            # Check if server is happy
            if data["status"] != "success":
                print "Error: " + data["status"]
                self.__errWrite("subscribe error: " +
                data["status"])
            else:
                self.__logWrite("subscribed correctly")
                print("subscribed correctly!")

            # Listen for new data
            toCount = 0; # TimeOutCount
            while True:

                try:
                    data = self.__parse(r1)
                except Exception as e:
                    #print("timeout")
                    toCount += 1
                    if toCount >= 18:
                        print ("Error, no keep alive "+
                        "received. Resetting connection")
                        self.__errWrite("subscribe " +
                        "error: No keep alive")
                        break
                    continue

                if data == None:
                    break
                # check if data is a theThings keepAlive
                if data == {}:
                    toCount = 0
                    continue
                queue.put(data)


    def __initData(self, token):
        """ Initialize data  """
        self._token = token
        self._urlWrite = self.URLROOT + self._token
        self._urlRead = self.URLROOT + self._token + "/resources/"
        self._urlSubs = self.URLROOT + self._token

    def __parse(self, r1):
        """ read data from socket and parse it  """
        buf = ""
        data = r1.read(1)

        if data == "[":
            buf = "["
            c = r1.read(1)
            while c != "]":
                buf += c
                c = r1.read(1)
            buf += ']'
        elif data == "{":
            count = 1
            buf = "{"
            while count != 0:
                c = r1.read(1)
                if c == "{":
                    count += 1
                elif c == "}":
                    count -= 1
                buf += c
        elif data == "":
            return None
        data = json.loads(buf)
        return data
