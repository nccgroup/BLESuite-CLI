import argparse
from bleSuite import bleScan
from bleSuite import bleSmartScan
from cmdLineToolWrappers import bleServiceRead, bleServiceReadAsync, bleServiceWrite, \
    bleHandleSubscribe, bleServiceScan, bleServiceWriteAsync, bleRunSmartScan
from bleSuite import utils
from bleSuite import validators
import logging
from logging.config import fileConfig
import binascii
import os

#import bdaddr


__version__ = "0.1"
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def parseCommand():
    """
    Creates parser and parses command line tool call.

    :return: parsed arguments
    """
    #cmd = None
    global __version__
    #Dictionary of available commands. Place new commands here
    cmdChoices = {'leScan': "Scan for BTLE devices",
                  'smartScan': "Scan specified BTLE device for device information, services, characteristics "
                               "(including associated descriptors). Note: This scan takes longer than the service scan",
                  'serviceScan': 'Scan specified address for all services and characteristics',
                  'readVal': "Read value from specified device and handle",
                  'writeVal': "Write value to specific handle on a device. Specify the --data or --files options"
                              "to set the payload data. Only data or file data can be specified, not both"
                              "(data submitted using the data flag takes precedence over data in files).",
                  'subscribe': "Write specified value (0000,0100,0200,0300) to chosen handle and initiate listener.",
                  'spoof': 'Modify your Bluetooth adapter\'s BT_ADDR. Use --addr to set the address. Some chipsets'
                           ' may not be supported.'}

    addressTypeChoices = ['public', 'random']
    securityLevelChoices = ['low', 'medium', 'high']

    parser = argparse.ArgumentParser(prog="bleSuite",
                                     description='Bluetooh Low Energy (BTLE) tool set for communicating and '
                                                 'testing BTLE devices on the application layer.')#,
                                     #formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('command', metavar='command', type=str, nargs=1,
                        action='store', choices=cmdChoices.keys(),
                        help='BLESuite command you would like to execute.' +
                             'The following are the currently supported commands:\n' +
                             '\n'.join(['\033[1m{}\033[0m: {}'.format(k, v) for k, v in cmdChoices.iteritems()]))

    parser.add_argument('--async', action='store_true', help='\033[1m<readVal, writeVal>\033[0m '
                                                             'Enable asynchronous writing/reading. Any output'
                                                             'will be displayed when received. This prevents'
                                                             'blocking.')
    parser.add_argument('--mode', metavar='mode', default=[1],
                        type=int, nargs=1, required=False,
                        action='store', help='\033[1m<subscribe>\033[0m '
                                                             'Selects which configuration to set'
                                                            'for a characteristic configuration descriptor.'
                                                            '0=off,1=notifications,2=indications,'
                                                            '3=notifications and inidications')
    parser.add_argument('--asyncTimeout', metavar='asyncTimeout', default=[5],
                        type=int, nargs=1,
                        required=False, action='store',
                        help='\033[1m<readVal, writeVal>\033[0m '
                             'Timeout for attempting to retrieve data from a device '
                             '(ie reading from a device handle). (Default: 5 seconds)')

    parser.add_argument('--maxTries', metavar='maxTries', default=[5],
                        type=int, nargs=1,
                        required=False, action='store',
                        help='\033[1m<readVal, writeVal>\033[0m '
                             'The amount of times to try each read/write operation before giving up. '
                             'If a operation fails and we continue, a re-connection is performed'
                             '(if applicable) and the operation is repeated. (Default: 5)')

    #using default [5] since parsed values are placed in a list
    parser.add_argument('--scanTimeout', metavar='scanTimeout', default=[5],
                        type=int, nargs=1,
                        required=False, action='store',
                        help='\033[1m<leScan>\033[0m '
                        'Device discovery timeout (seconds) for BTLE scan. (Default: 5 seconds Maximum: 15 seconds)')

    #Device for discovery service can be specified
    parser.add_argument('--adapter', metavar='adapter', default=[""],
                        type=str, nargs=1,
                        required=False, action='store',
                        help='\033[1m<all commands>\033[0m '
                             'Specify which Bluetooth adapter should be used. '
                             'These can be found by running (hcitool dev).')


    parser.add_argument('--addr', metavar='deviceAddress', type=validators.checkValidBTAddr, nargs=1,
                        required=False, action='store',
                        help='\033[1m<all commands>\033[0m '
                             'Bluetooth address (BD_ADDR) of the target Bluetooth device')

    parser.add_argument('--handles', metavar='handles', type=str, nargs="+",
                        required=False, action='store', default=[None],
                        help='\033[1m<readVal, writeVal>\033[0m '
                             'Hexadecimal handel list of characteristics to access (ex: 005a 006b). If '
                             'you want to access the value of a characteristic, use the handle_value '
                             'value from the service scan.')
    parser.add_argument('--uuids', metavar='uuids', type=str, nargs="+",
                        required=False, action='store', default=[None],
                        help='\033[1m<readVal>\033[0m '
                             'UUID list of characteristics to access. If '
                             'you want to access the value of a characteristic, use the UUID '
                             'value from the service scan.')

    parser.add_argument('--data', metavar='data', type=str, nargs="+",
                        required=False, action='store', default=[None],
                        help='\033[1m<writeVal>\033[0m '
                             'Strings that you want to write to a handle (separated by spaces).')

    parser.add_argument('--files', metavar='files', type=str, nargs="+",
                        required=False, action='store', default=[None],
                        help='\033[1m<writeVal>\033[0m '
                             'Files that contain data to write to handle (separated by spaces)')

    parser.add_argument('--payloadDelimiter', metavar='payloadDelimiter', type=str, nargs=1,
                    required=False, action='store', default=["EOF"],
                    help='\033[1m<writeVal>\033[0m '
                         'Specify a delimiter (string) to use when specifying data for BLE payloads.'
                         'For instance, if I want to send packets with payloads in a file separated'
                         'by a comma, supply \'--payloadDelimiter ,\'. Supply EOF if you want the entire contents'
                         'of a file sent. (Default: EOF)')


    parser.add_argument('--addrType', metavar='addrType', type=str, nargs=1,
                    required=False, action='store', default=['public'], choices=addressTypeChoices,
                    help='\033[1m<all commands>\033[0m '
                         'Type of BLE address you want to connect to [public | random].')

    parser.add_argument('--security', metavar='security', type=str, nargs=1,
                    required=False, action='store', default=['low'], choices=securityLevelChoices,
                    help='\033[1m<all commands>\033[0m '
                         'Level of security for connection to BLE device [low | medium | high]')

    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

    parser.add_argument('--debug', action='store_true', help='\033[1m<all commands>\033[0m '
                                                             'Enable logging for debug statements.')

    return parser.parse_args()

def processArgs(args):
    """
    Process command line tool arguments parsed by argparse
    and call appropriate bleSuite functions.

    :param args: parser.parse_args()
    :return:
    """
    command = args.command[0]
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)



    if command  == 'spoof':
        import bdaddr
        if args.addr[0] == "":
            print "Please specify an address to spoof."
        else:
            logger.debug("About to spoof to address %s", args.addr[0])
            ret = bdaddr.bdaddr(args.adapter[0], args.addr[0])
            logger.debug("bdaddr return value: %d", ret)
            if ret == -1:
                raise ValueError('Spoofing failed. Your device may not be supported.')



    if command == 'leScan':
        print "BTLE Scan beginning"
        devices = bleScan.bleScanMain(args.scanTimeout[0], args.adapter[0])
        print "Name\tAddress"
        print "================"
        for address, name in devices.items():
            if name == '':
                name = "Unavailable"
            print("{}\t{}".format(name, address))

    if command == 'smartScan':
        print "BTLE Smart Scan beginning"
        device = bleRunSmartScan(args.addr[0], args.adapter[0],
                                           args.addrType[0], args.security[0])
        #print device mac and info from deviceInformationQueryList


    if command == 'serviceScan':
        print "BTLE Scanning Services"
        bleServiceScan(args.addr[0], args.adapter[0],
                       args.addrType[0], args.security[0])

    if command == 'readVal':
        print "Reading value from handle or UUID"
        if args.async:
            uuidData, handleData = bleServiceReadAsync(args.addr[0], args.adapter[0],
                                                       args.addrType[0], args.security[0],
                                                       args.handles, args.uuids,
                                                       args.asyncTimeout[0], args.maxTries[0])
            for dataTuple in handleData:
                print "\nHandle:", "0x" + dataTuple[0]
                #"".join("{:02x}".format(ord(c)) for c in handle)
                if isinstance(dataTuple[1][0], str):
                    utils.printHelper.printDataAndHex(dataTuple[1], False)
                else:
                    utils.printHelper.printDataAndHex(dataTuple[1][1].received(), False)
            for dataTuple in uuidData:
                print "\nUUID:", dataTuple[0]
                if isinstance(dataTuple[2][0], str):
                    utils.printHelper.printDataAndHex(dataTuple[1], False)
                else:
                    utils.printHelper.printDataAndHex(dataTuple[1][1].received(), False)
        else:
            uuidData, handleData = bleServiceRead(args.addr[0], args.adapter[0],
                                                  args.addrType[0], args.security[0],
                                                  args.handles, args.uuids, args.maxTries[0])
            for dataTuple in handleData:
                print "\nHandle:", "0x" + dataTuple[0]
                #"".join("{:02x}".format(ord(c)) for c in handle)
                utils.printHelper.printDataAndHex(dataTuple[1], False)
            for dataTuple in uuidData:
                print "\nUUID:", dataTuple[0]
                utils.printHelper.printDataAndHex(dataTuple[1], False, handle=dataTuple[2])

    if command == 'writeVal':
        print "Writing value to handle"
        if args.async:
            logger.debug("Async Write")
            if args.data != [None]:
                handleData = bleServiceWriteAsync(args.addr[0], args.adapter[0],
                                                  args.addrType[0], args.security[0],
                                                  args.handles, args.data, args.maxTries[0],
                                                  args.asyncTimeout[0])
            elif args.payloadDelimiter[0] == 'EOF':
                logger.debug("Payload Delimiter: EOF")
                dataSet = []
                for dataFile in args.files:
                    if dataFile is None:
                        continue
                    logger.debug("Reading file: %s", dataFile)
                    f = open(dataFile, 'r')
                    dataSet.append(f.read())
                    f.close()
                logger.debug("Sending data set: %s" % dataSet)
                handleData = bleServiceWriteAsync(args.addr[0], args.adapter[0],
                                                  args.addrType[0], args.security[0],
                                                  args.handles, dataSet, args.maxTries[0],
                                                  args.asyncTimeout[0])
                logger.debug("Received data: %s" % handleData)
                '''for dataTuple in handleData:
                    print "\nHandle:", "0x" + dataTuple[0]
                    utils.printHelper.printDataAndHex(dataTuple[1], False)'''
            else:
                logger.debug("Payload Delimiter: %s", args.payloadDelimiter[0])
                dataSet = []
                for dataFile in args.files:
                    if dataFile is None:
                        continue
                    f = open(dataFile, 'r')
                    data = f.read()
                    f.close()
                    data = data.split(args.payloadDelimiter[0])
                    dataSet.extend(data)

                logger.debug("Sending dataSet: %s" % dataSet)

                handleData = bleServiceWriteAsync(args.addr[0], args.adapter[0],
                                                  args.addrType[0], args.security[0],
                                                  args.handles, dataSet, args.maxTries[0],
                                                  args.asyncTimeout[0])
            for dataTuple in handleData:
                print "\nHandle:", "0x" + dataTuple[0]
                #"".join("{:02x}".format(ord(c)) for c in handle)
                print "Input:"
                utils.printHelper.printDataAndHex(dataTuple[2], False, prefix="\t")
                print "Output:"
                #if tuple[1][0] is a string, it means our cmdLineToolWrapper removed the GattResponse object
                #due to a timeout, else we grab the GattResponse and its response data
                if isinstance(dataTuple[1][0], str):
                    utils.printHelper.printDataAndHex(dataTuple[1], False, prefix="\t")
                else:
                    utils.printHelper.printDataAndHex(dataTuple[1][1].received(), False, prefix="\t")
        else:
            logger.debug("Sync Write")
            if args.data != [None]:
                #bleServiceWrite(args.deviceAddr[0], args.adapter[0], args.handle[0], args.data[0])
                handleData = bleServiceWrite(args.addr[0], args.adapter[0],
                                             args.addrType[0], args.security[0],
                                             args.handles, args.data, args.maxTries[0])

                '''for dataTuple in handleData:
                    print "\nHandle:", "0x" + dataTuple[0]
                    utils.printHelper.printDataAndHex(dataTuple[1], False)'''

            elif args.payloadDelimiter[0] == 'EOF':
                logger.debug("Payload Delimiter: EOF")
                dataSet = []
                for dataFile in args.files:
                    if dataFile is None:
                        continue
                    logger.debug("Reading file: %s", dataFile)
                    f = open(dataFile, 'r')
                    dataSet.append(f.read())
                    f.close()
                logger.debug("Sending data set: %s" % dataSet)
                handleData = bleServiceWrite(args.addr[0], args.adapter[0],
                                             args.addrType[0], args.security[0],
                                             args.handles, dataSet, args.maxTries[0])
                logger.debug("Received data: %s" % handleData)
                '''for dataTuple in handleData:
                    print "\nHandle:", "0x" + dataTuple[0]
                    utils.printHelper.printDataAndHex(dataTuple[1], False)'''
            else:
                logger.debug("Payload Delimiter: %s", args.payloadDelimiter[0])
                dataSet = []
                for dataFile in args.files:
                    if dataFile is None:
                        continue
                    f = open(dataFile, 'r')
                    data = f.read()
                    f.close()
                    data = data.split(args.payloadDelimiter[0])
                    dataSet.extend(data)
                logger.debug("Sending dataSet: %s" % dataSet)
                handleData = bleServiceWrite(args.addr[0], args.adapter[0],
                                             args.addrType[0], args.security[0],
                                             args.handles, dataSet, args.maxTries[0])
            for dataTuple in handleData:
                print "\nHandle:", "0x" + dataTuple[0]
                print "Input:"
                utils.printHelper.printDataAndHex([dataTuple[2]], False, prefix="\t")
                print "Output:"
                utils.printHelper.printDataAndHex(dataTuple[1], False, prefix="\t")

    if command == 'subscribe':
        print "Subscribing to device"
        bleHandleSubscribe(args.addr[0], args.handles, args.adapter[0],
                           args.addrType[0], args.security[0], args.mode[0])

    return

def main():
    """
    Main loop for BLESuite command line tool.

    :return:
    """
    args = parseCommand()
    processArgs(args)

    logger.debug("Args: %s" % args)


