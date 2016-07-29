import sys
from gattlib import GATTRequester
from bleSuite import bleConnectionManager
from bleSuite import bleServiceManager
from bleSuite import bleSmartScan
from bleSuite import utils
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def bleServiceRead(address, adapter, addressType, securityLevel, handles, UUIDS, maxTries=5):
    """
    Used by command line tool to read data from device by handle

    :param address: Address of target BTLE device
    :param adapter: Host adapter (Empty string to use host's default adapter)
    :param addressType: Type of address you want to connect to [public | random]
    :param securityLevel: Security level [low | medium | high]
    :param handles: List of handles to read from
    :param UUIDS: List of UUIDs to read from
    :param maxTries: Maximum number of times to attempt each write operation. Default: 5
    :type address: str
    :type adapter: str
    :type addressType: str
    :type securityLevel: str
    :type handles: list of base 10 ints
    :type UUIDS: list of strings
    :type maxTries: int
    :return: uuidData, handleData
    :rtype: list of (UUID, data) tuples and list of (handle, data) tuples
    """
    connectionManager = bleConnectionManager.BLEConnectionManager(address, adapter, addressType, securityLevel)
    connectionManager.connect()
    uuidData = []
    handleData = []
    for handle in handles:
        if handle is not None:
            tries = 0
            while True:
                try:
                    if not connectionManager.isConnected():
                        connectionManager.connect()
                    data = bleServiceManager.bleServiceReadByHandle(connectionManager, int(handle, 16))
                    break
                except RuntimeError as e:
                    if "Invalid handle" in str(e):
                        data = -1
                        break
                    elif "Attribute can't be read" in str(e):
                        data = -2
                        break
                    else:
                        if tries >= maxTries:
                            raise RuntimeError(e)
                        else:
                            tries += 1
                #print "\nHandle:", format(ord(binascii.unhexlify(handle)), "#8x")
                #printDataAndHex(data, 10)
            handleData.append((handle, data))
    for UUID in UUIDS:
        if UUID is not None:
            tries = 0
            while True:
                try:
                    if not connectionManager.isConnected():
                        connectionManager.connect()
                    data, handle = bleServiceManager.bleServiceReadByUUID(connectionManager, UUID)
                    break
                except RuntimeError as e:
                    if "Invalid handle" in str(e):
                        data = -1
                        break
                    elif "Attribute can't be read" in str(e):
                        data = -2
                        break
                    else:
                        if tries >= maxTries:
                            raise RuntimeError(e)
                        else:
                            tries += 1
            #print "\nUUID:", UUID
            #printDataAndHex(data, 10)
            uuidData.append((UUID, handle, data))
    #returns list of tuples (handle, data)
    return uuidData, handleData


def bleServiceReadAsync(address, adapter, addressType, securityLevel, handles, UUIDS, maxTries=5, timeout=5):
    """
    Used by command line tool to read data from device by handle using the async
    method. As of now, errors are not returned when reading asynchronously, so a
    timeout must be specified to determine when we should stop looking for a response
    from a device. (Note: This call is blocking until responses are received or a timeout
    is reached).

    :param address: Address of target BTLE device
    :param adapter: Host adapter (Empty string to use host's default adapter)
    :param addressType: Type of address you want to connect to [public | random]
    :param securityLevel: Security level [low | medium | high]
    :param handles: List of handles to read from
    :param UUIDS: List of UUIDs to read from
    :param maxTries: Maximum number of times to attempt each write operation. Default: 5
    :param timeout: Time (in seconds) until each read times out if there's an issue. Default: 5
    :type address: str
    :type adapter: str
    :type addressType: str
    :type securityLevel: str
    :type handles: list of base 10 ints
    :type UUIDS: list of strings
    :type maxTries: int
    :type timeout: int
    :return: uuidData, handleData
    :rtype: list of (UUID, data) tuples and list of (handle, data) tuples
    """
    import time

    def asyncHandleCallback(data):
        #print "\nHandle:", "0x" + handle
        #"".join("{:02x}".format(ord(c)) for c in handle)
        logger.debug("Raw callback data: %s" % data)
        utils.printHelper.printDataAndHex([data], False)
    logger.debug("Creating connection manager")
    connectionManager = bleConnectionManager.BLEConnectionManager(address, adapter, addressType, securityLevel)
    #connectionManager.createResponse(responseFunction=asyncHandleCallback)
    #connectionManager.createResponse()
    connectionManager.connect()
    logger.debug("Connected")
    uuidResponses = []
    handleResponses = []

    handleResponseQueue = []
    uuidResponseQueue = []
    for handle in handles:
        if handle is not None:
            tries = 0
            while True:
                try:
                    if not connectionManager.isConnected():
                        connectionManager.connect()
                    resp = bleServiceManager.bleServiceReadByHandleAsync(connectionManager, int(handle, 16), None)
                    handleResponseQueue.append((handle, resp, time.time()))
                    break
                except RuntimeError as e:
                        if "Invalid handle" in str(e):
                            handleResponses.append((handle, ["Invalid handle"]))
                            break
                        elif "Attribute can't" in str(e):
                            handleResponses.append((handle, ["Attribute can't be read"]))
                            break
                        else:
                            if tries >= maxTries:
                                logger.debug("%s Tries exceeded, throwing Runtime error and aborting write" % maxTries)
                                raise RuntimeError(e)
                            else:
                                logger.debug("Error: %s Trying Again" % e)
                                tries += 1
    for UUID in UUIDS:
        if UUID is not None:
            tries = 0
            while True:
                try:
                    if not connectionManager.isConnected():
                        connectionManager.connect()
                    resp = bleServiceManager.bleServiceReadByUUIDAsync(connectionManager, UUID)
                    uuidResponseQueue.append((UUID, resp, time.time()))
                    break
                except RuntimeError as e:
                        if "Invalid handle" in str(e):
                            uuidResponses.append((UUID, ["Invalid UUID"]))
                            break
                        elif "Attribute can't" in str(e):
                            uuidResponses.append((UUID, ["Attribute can't be read"]))
                            break
                        else:
                            if tries >= maxTries:
                                logger.debug("%s Tries exceeded, throwing Runtime error and aborting write" % maxTries)
                                raise RuntimeError(e)
                            else:
                                logger.debug("Error: %s Trying Again" % e)
                                tries += 1
    #returns list of tuples (handle, data)
    while True:
        for i in handleResponseQueue:
            if i[1][1].received():
                data = i[1][1].received()
                logger.debug("Handle: %s Received data: %s" % (i[0], data))
                handleResponses.append((i[0], i[1]))
                handleResponseQueue.remove(i)
            elif time.time() - i[2] >= timeout:
                handleResponses.append((i[0], ["Error: Timeout reached for action"]))
                handleResponseQueue.remove(i)
            logger.debug("Response creation time: %s current time: %s" % (i[2], time.time()))
                #utils.printHelper.printDataAndHex()
                #handleResponses.remove(i)
                #connectionManager.responses.remove(i[1])
            #if not i.is_alive():
            #    handleThreads.remove(i)
        for i in uuidResponseQueue:
            if i[1][1].received():
                data = i[1][1].received()
                handle = data[:2][::-1]
                data = data[2:]
                logger.debug("UUID: %s HANDLE: %s Received data: %s" % (i[0], handle, data))
                uuidResponses.append((i[0], i[1], handle))
                uuidResponseQueue.remove(i)
            elif time.time() - i[2] >= timeout:
                uuidResponses.append((i[0], ["Error: Timeout reached for action"]))
                uuidResponseQueue.remove(i)
            logger.debug("Response creation time: %s current time: %s" % (i[2], time.time()))
        if len(handleResponseQueue) <= 0 and len(uuidResponseQueue) <= 0:
            logger.debug("Out of responses")
            break
        logger.debug("Number of responses that haven't received: %s" % (len(handleResponseQueue) + len(uuidResponseQueue)))
        time.sleep(0.1)

    return uuidResponses, handleResponses


def bleServiceWrite(address, adapter, addressType, securityLevel, handles, inputs, maxTries=5):
    """
    Used by command line tool to wrtie data to a device handle

    :param address: Address of target BTLE device
    :param adapter: Host adapter (Empty string to use host's default adapter)
    :param addressType: Type of address you want to connect to [public | random]
    :param securityLevel: Security level [low | medium | high]
    :param handles: List of handles to write to
    :param inputs: List of strings to write to handles
    :param maxTries: Maximum number of times to attempt each write operation. Default: 5
    :type address: str
    :type adapter: str
    :type addressType: str
    :type securityLevel: str
    :type handles: list of base 10 ints
    :type inputs: list of strings
    :type maxTries: int
    :return: list of (handle, data, input)
    :rtype: list of tuples (int, str, str)
    """
    connectionManager = bleConnectionManager.BLEConnectionManager(address, adapter, addressType, securityLevel)
    connectionManager.connect()
    #print "Input:",input
    handleData = []
    for inputVal in inputs:
        for handle in handles:
            if handle is not None:
                tries = 0
                while True:
                    try:
                        if not connectionManager.isConnected():
                            connectionManager.connect()
                        data = bleServiceManager.bleServiceWriteToHandle(connectionManager, int(handle, 16), inputVal)
                        break
                    except RuntimeError as e:
                        if "Invalid handle" in str(e):
                            data = -1
                            break
                        elif "Attribute can't" in str(e):
                            data = -2
                            break
                        else:
                            if tries >= maxTries:
                                logger.debug("%s Tries exceeded, throwing Runtime error and aborting write" % maxTries)
                                raise RuntimeError(e)
                            else:
                                logger.debug("Error: %s Trying Again" % e)
                                tries += 1
                handleData.append((handle, data, inputVal))
    return handleData

def bleServiceWriteAsync(address, adapter, addressType, securityLevel, handles, inputs, maxTries=5, timeout=5):
    """
    Used by command line tool to write data to device by handle using the async
    method. As of now, errors are not returned when reading asynchronously, so a
    timeout must be specified to determine when we should stop looking for a response
    from a device. (Note: This call is blocking until responses are received or a timeout
    is reached).

    :param address: Address of target BTLE device
    :param adapter: Host adapter (Empty string to use host's default adapter)
    :param addressType: Type of address you want to connect to [public | random]
    :param securityLevel: Security level [low | medium | high]
    :param handles: List of handles to read from
    :param inputs: List of input strings to send
    :param maxTries: Maximum number of times to attempt each write operation. Default: 5
    :param timeout: Time (in seconds) until each read times out if there's an issue. Default: 5
    :type address: str
    :type adapter: str
    :type addressType: str
    :type securityLevel: str
    :type handles: list of base 10 ints
    :type inputs: list of str
    :type maxTries: int
    :type timeout: int
    :return: list of (handle, data, inputVal) tuples
    :rtype: list of (int, str, str) tuples
    """
    import time

    def asyncHandleCallback(data):
        #print "\nHandle:", "0x" + handle
        #"".join("{:02x}".format(ord(c)) for c in handle)
        logger.debug("Raw callback data: %s" % data)
        utils.printHelper.printDataAndHex([data], False)
    logger.debug("Creating connection manager")
    connectionManager = bleConnectionManager.BLEConnectionManager(address, adapter, addressType, securityLevel)
    #connectionManager.createResponse(responseFunction=asyncHandleCallback)
    #connectionManager.createResponse()
    connectionManager.connect()
    logger.debug("Connected")
    handleResponses = []

    handleResponseQueue = []

    for inputVal in inputs:
        for handle in handles:
            if handle is not None:
                while True:
                    tries = 0
                    try:
                        if not connectionManager.isConnected():
                            connectionManager.connect()
                        logger.debug("Attempting to send %s to handle %s" % (inputVal, handle))
                        resp = bleServiceManager.bleServiceWriteToHandleAsync(connectionManager, int(handle, 16),
                                                                              inputVal, None)
                        handleResponseQueue.append((handle, resp, time.time(), [inputVal]))
                        break
                    except RuntimeError as e:
                        if "Invalid handle" in str(e):
                            handleResponses.append((handle, ["Invalid handle"], inputVal))
                            break
                        elif "Attribute can't" in str(e):
                            handleResponses.append((handle, ["Attribute can't be written to"], inputVal))
                            break
                        else:
                            if tries >= maxTries:
                                logger.debug("%s Tries exceeded, throwing Runtime error and aborting write" % maxTries)
                                raise RuntimeError(e)
                            else:
                                logger.debug("Error: %s Trying Again" % e)
                                tries += 1

    #returns list of tuples (handle, data)
    while True:
        for i in handleResponseQueue:
            if i[1][1].received():
                data = i[1][1].received()
                logger.debug("Handle: %s Received data: %s" % (i[0], data))
                handleResponses.append((i[0], i[1], i[3]))
                handleResponseQueue.remove(i)
            elif time.time() - i[2] >= timeout:
                handleResponses.append((i[0], ["Error: Timeout reached for action"], i[3]))
                handleResponseQueue.remove(i)
            logger.debug("Response creation time: %s current time: %s" % (i[2], time.time()))
                #utils.printHelper.printDataAndHex()
                #handleResponses.remove(i)
                #connectionManager.responses.remove(i[1])
            #if not i.is_alive():
            #    handleThreads.remove(i)
        if len(handleResponseQueue) <= 0:
            logger.debug("Out of responses")
            break
        logger.debug("Number of responses that haven't received: %s" % len(handleResponseQueue))
        time.sleep(0.1)

    return handleResponses


def bleHandleSubscribe(address, handles, adapter, addressType, securityLevel, mode):
    """
    Used by command line tool to enable specified handles' notify mode
    and listen until user interrupts.

    :param address: Address of target BTLE device
    :param handles: List of handle descriptors to write 0100 (enable notification) to
    :param adapter: Host adapter (Empty string to use host's default adapter)
    :param addressType: Type of address you want to connect to [public | random]
    :param securityLevel: Security level [low | medium | high]
    :param mode: Mode to set for characteristic configuration (0=off,1=notifications,2=indications,
    3=notifications and inidications)
    :type address: str
    :type handles: list of base 10 ints
    :type adapter: str
    :type addressType: str
    :type securityLevel: str
    :type mode: int
    :return:
    """
    logger.debug("Beginning Subscribe Function")
    if address is None:
        raise Exception("%s Bluetooth address is not valid. Please supply a valid Bluetooth address value." % address)

    if mode == 0:
        configVal = str(bytearray([00, 00]))
    elif mode == 1:
        configVal = str(bytearray([01, 00]))
    elif mode == 2:
        configVal = str(bytearray([02, 00]))
    elif mode == 3:
        configVal = str(bytearray([03, 00]))
    else:
        raise Exception("%s is not a valid mode. Please supply a value between 0 and 3 (inclusive)" % mode)



    class Requester(GATTRequester):
        def __init__(self, *args):
            GATTRequester.__init__(self, *args)

        def on_notification(self, originHandle, data):
            print "\nNotification on Handle"
            print "======================="
            print format(originHandle, "#8x")
            utils.printHelper.printDataAndHex([data], False)
            #self.wakeup.set()

        def on_indication(self, originHandle, data):
            print "\nIndication on Handle"
            print "======================="
            print format(originHandle, "#8x")
            utils.printHelper.printDataAndHex([data], False)
            #self.wakeup.set()

    class ReceiveNotification(object):
        def __init__(self, connectionManager, handles, configVal):
            logger.debug("Initializing receiver")
            self.connectionManager = connectionManager
            self.configVal = configVal
            self.handles = handles
            self.wait_notification()

        def connect(self):
            logger.debug("Connecting...")
            sys.stdout.flush()

            self.connectionManager.connect()
            #self.requester.connect(True)
            logger.debug("OK!")

        def wait_notification(self):
            print "Listening for communications"
            logger.debug("Listening for communications")
            #self.received.wait()
            while True:
                if self.connectionManager.isConnected():
                    continue
                logger.debug("Connection Lost, re-connecting subscribe")
                self.connectionManager.connect()
                for i in self.handles:
                    bleServiceManager.bleServiceWriteToHandle(connectionManager, int(i, 16), self.configVal)
    #print "About to try to receive"


    connectionManager = bleConnectionManager.BLEConnectionManager(address, adapter, addressType, securityLevel,
                                                                  createRequester=False)
    #Special requester that has an overridden on_notification handler
    requester = Requester(address, False)
    connectionManager.setRequester(requester)
    connectionManager.connect()
    for handle in handles:
        logger.debug("Writing %s to handle %s" % (configVal, handle))
        try:
            bleServiceManager.bleServiceWriteToHandle(connectionManager, int(handle, 16), configVal)
        except RuntimeError as e:
            if "Invalid handle" in str(e):
                data = -1
            elif "Attribute can't be read" in str(e):
                data = -2
            else:
                raise RuntimeError(e)


    ReceiveNotification(connectionManager, handles, configVal)


def bleServiceScan(address, adapter, addressType, securityLevel):
    """
    Used by command line tool to initiate and print results for
    a scan of all services and
    characteristics present on a BTLE device.

    :param address: Address of target BTLE device
    :param adapter: Host adapter (Empty string to use host's default adapter)
    :param addressType: Type of address you want to connect to [public | random]
    :param securityLevel: Security level [low | medium | high]
    :type address: str
    :type adapter: str
    :type addressType: str
    :type securityLevel: str
    :return:
    """
    if address is None:
        raise Exception("%s Bluetooth address is not valid. Please supply a valid Bluetooth address value." % address)

    connectionManager = bleConnectionManager.BLEConnectionManager(address, adapter, addressType, securityLevel)
    bleDevice = bleServiceManager.bleServiceDiscovery(address, connectionManager)
    bleDevice.printDeviceStructure()


def bleRunSmartScan(address, adapter, addressType, securityLevel):
    """
    Used by command line tool to initiate and print results for
    a scan of all services,
    characteristics, and descriptors present on a BTLE device.

    :param address: Address of target BTLE device
    :param adapter: Host adapter (Empty string to use host's default adapter)
    :param addressType: Type of address you want to connect to [public | random]
    :param securityLevel: Security level [low | medium | high]
    :type address: str
    :type adapter: str
    :type addressType: str
    :type securityLevel: str
    :return:
    """
    if address is None:
        raise Exception("%s Bluetooth address is not valid. Please supply a valid Bluetooth address value." % address)

    connectionManager = bleConnectionManager.BLEConnectionManager(address, adapter, addressType, securityLevel)
    bleDevice = bleSmartScan.bleSmartScan(address, connectionManager)

    print "**********************"
    print "Smart Scan Results"
    print "**********************"
    #print"BD_ADDR:", args.addr[0], "\n"


    #Print services and characteristics with data in between
    bleDevice.printDeviceStructure()

    print "**********************"
    print "Finished"
    print "**********************"
