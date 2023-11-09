import time
import numpy as np
import can
from enum import IntEnum
import struct

# idList = np.arange(0x40B, 0x7F0, 1)
idList = np.arange(0x68C, 0x68E, 1)
receivedCorrectMsg = False
receivedReadDatabyIDDone = False
udsClientID = 0x0000    #
udsServerID = 0x0000    #
cab500IpID = 0x0000     #
udsClientIDnew = 0x0000    #
udsServerIDnew = 0x0000    #
cab500IpIDnew = 0x0000     #


def print_hi(name):
    print(f'Msg:, {name}')


class CAB500(IntEnum):
    udsClientID = 0x0000
    udsServerID = 0x0000
    cab500IpID = 0x0000
    receivedCorrectMsg: bool = False
    receivedReadDatabyIDDone: bool = False
    SINGLE_FRAME_1_BYTE = 0x01  # Frame consists of 1 msg with 1 byte of data
    SINGLE_FRAME_2_BYTE = 0x02  # Frame consists of 1 msg with 2 byte of data
    SINGLE_FRAME_3_BYTE = 0x03
    SINGLE_FRAME_4_BYTE = 0x04
    SINGLE_FRAME_5_BYTE = 0x05
    SINGLE_FRAME_6_BYTE = 0x06
    SINGLE_FRAME_7_BYTE = 0x07
    SINGLE_FRAME_8_BYTE = 0x08
    SINGLE_FRAME_9_BYTE = 0x09
    firstMessage = 0x10
    secondMessage = 0x21
    nineUsableData = 0x09

    # ECU reset function --- does not work ---
    ecuResetMsg = 0x11
    ecuResetMsg_send_hard = 0x01
    ecuResetMsg_send_soft = 0x03

    # Read data by identifier, single frame composed of 3 byte, \x03\x22\x then choose function
    readDataById = 0x22
    # Read CAN ID, \x03\x22\xF0\x10, then response, then transmit flow controll \x03\x00\x00
    canIDread = 0xF010
    # canIDread2 = 0x10
    flowControl = 0x30  # 00 00
    canIDreadPos = 0x62
    canIDreadNeg = 0x7F

    # WriteDataByIdentifier
    writeDataById = 0x2E
    # Frequency of filter
    TEN_HZ = 0x01
    TWENTY_HZ = 0x02
    THIRTY_HZ = 0x03
    AVERAGE_TEN_MS = 0xFF


def ecuResetService(msg_id):  # does not work on this version of CAB500 !!
    msg = can.Message(
        arbitration_id=msg_id,
        data=[CAB500.SINGLE_FRAME_2_BYTE, CAB500.ecuResetMsg, CAB500.ecuResetMsg_send_soft],
        is_extended_id=False
    )
    try:
        bus.ch.send(msg)
        # print(f"Message sent on {bus.ch.channel_info}")
        # print(f"Data sent: {msg}")
    except can.CanError:
        print("Message NOT sent")


def readDatabyIdentifier(msg_id):
    msg = can.Message(
        arbitration_id=msg_id,
        data=[CAB500.SINGLE_FRAME_3_BYTE, CAB500.readDataById, CAB500.canIDread>>8, CAB500.canIDread&255],
        is_extended_id=False
    )
    try:
        bus.ch.send(msg)
        # print(f"Message sent on {bus.ch.channel_info}")
        # print(f"Data sent: {msg}")
    except can.CanError:
        print("Message NOT sent")


def flowControl(msg_id):
    msg = can.Message(
        arbitration_id=msg_id,
        data=[CAB500.flowControl, 0x00, 0x00],
        is_extended_id=False
    )
    try:
        bus.ch.send(msg)
        # print(f"Message sent on {bus.ch.channel_info}")
        # print(f"Data sent: {msg}")
    except can.CanError:
        print("Message NOT sent")

def writeDatabyIdentifier(msg_id):
    msg = can.Message(
        arbitration_id=msg_id,
        data=[CAB500.firstMessage, CAB500.SINGLE_FRAME_9_BYTE, CAB500.writeDataById, CAB500.canIDread, ],
        is_extended_id=False
    )
    try:
        bus.ch.send(msg)
        print(f"Message sent on {bus.ch.channel_info}")
        print(f"Data sent: {msg}")
    except can.CanError:
        print("Message NOT sent")


class CanInterface:

    def __init__(self, node_id=0x11, channel='can0', bustype='socketcan', bitrate='500000'):
        self.node_id = node_id
        self.channel = channel
        self.bustype = bustype
        self.bitrate = bitrate
        self.accept_virtual = 1

        # TODO move to function to connect to network
        # TODO add function to disconnect network.disconnect()
        # Try to find a CAN-Bus interface
        for interface, channel in [('kvaser', 0), ('kvaser', 1)]:
            try:
                self._can_bus = can.ThreadSafeBus(interface=interface, channel=channel, bitrate=self.bitrate)
                break
            except (OSError, can.CanError, NameError, ImportError):
                pass
        else:
            raise Exception('No CAN-Bus interface was found')
        self.ch = self._can_bus
        #  TODO add filter to notifier
        #  _can_listener = can.Listener()
        #  _can_listener.on_message_received = self._msg_callback
        #  self._can_notifier = can.Notifier(self._can_bus, [_can_listener])
        #  self._can_notifier = can.Notifier()

    def add_can_msg_callback(self):
        pass

    def remove_can_msg_callback(self):
        pass

    def close_bus(self):
        # self._can_notifier.stop(timeout=1)
        self._can_bus.shutdown()


def receive_can_data(msg):
    global receivedCorrectMsg, cab500IpID, udsClientID, udsServerID, receivedReadDatabyIDDone

    # print(f"Recieved data: {msg.data}, id: {hex(msg.arbitration_id)}")
    if msg.is_rx == True and msg.dlc == 8:
        # print("Message recieved and dlc=8")
        if msg.data[0] == CAB500.firstMessage:  # First frame of message
            if msg.data[1] == CAB500.nineUsableData:
                if msg.data[2] == CAB500.canIDreadPos:
                    # print(f"Positive response")
                    if int.from_bytes(msg.data[3:5]) == CAB500.canIDread:
                        receivedCorrectMsg = True
                        cab500IpID = int.from_bytes(msg.data[5:7])
                        # print(cab500IpID)
                        udsClientID = msg.data[7]
                        # print(udsClientID)
                else:
                    print("Negative response, wrong format" + msg.data)

        elif msg.data[0] == CAB500.secondMessage:
            # print("Second message received")
            udsClientID = int.from_bytes([udsClientID, msg.data[1]])
            udsServerID = int.from_bytes(msg.data[2:4])
            receivedReadDatabyIDDone = True

    # data_unpack = struct.unpack(">IB3x", msg.data)
    # print(data_unpack)


if __name__ == '__main__':
    print_hi('Start program')
    print_hi(f'Min: {hex(min(idList))}, Max: {hex(max(idList))}')
    bus = CanInterface()
    notifier = can.Notifier(bus.ch, [receive_can_data])

    for id in idList:
        readDatabyIdentifier(id)
        time.sleep(0.01)
        if receivedCorrectMsg:
            flowControl(id)
            time.sleep(0.01)
            break
    if receivedReadDatabyIDDone:
        print_hi('Done, udsClientID: ' + hex(udsClientID) + ' , udsServerID: ' +
                 hex(udsServerID) + ' and cab500IpID: ' + hex(cab500IpID))


    bus.close_bus()
    print_hi('Stop program')
