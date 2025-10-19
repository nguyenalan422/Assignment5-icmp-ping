from socket import *
import os
import sys
import time
import select
import struct

ICMP_ECHO_REQUEST = 8


def checksum(source_string):
    checkS = 0
    ctTo = (len(source_string) // 2) * 2
    ct = 0

    while ct < ctTo:
        thisVal = source_string[ct + 1] * 256 + source_string[ct]
        checkS = checkS + thisVal
        checkS = checkS & 0xffffffff
        ct = ct + 2

    if ctTo < len(source_string):
        checkS = checkS + source_string[len(source_string) - 1]
        checkS = checkS & 0xffffffff

    checkS = (checkS >> 16) + (checkS & 0xffff)
    checkS = checkS + (checkS >> 16)

    ans = ~checkS
    ans = ans & 0xffff
    ans = ans >> 8 | (ans << 8 & 0xff00)

    return ans


def onePing(mySocket, ID, timeout, destAddr):
    remaining = timeout

    while True:
        begin = time.time()
        whatReady = select.select([mySocket], [], [], remaining)
        sDuration = (time.time() - begin)
        if whatReady[0] == []:
            return "Request timed out."

        recieved = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        icmpHeader = recPacket[20:28]
        type, code, checksum_recv, packetID, sequence = struct.unpack("bbHHh", icmpHeader)

        if packetID == ID:
            bytesInDouble = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
            rtt = (recieved - timeSent) * 1000
            
            return f"Reply from {addr[0]}: bytes={len(recPacket)} time={rtt:.2f}ms"

        remaining = remaining - sDuration
        if remaining <= 0:
            return "Request timed out."


def sendOnePing(mySocket, destAddr, ID):
    myCS = 0
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myCS, ID, 1)
    data = struct.pack("d", time.time())
    myCS = checksum(header + data)

    if sys.platform == 'darwin':
        myCS = htons(myChecksum) & 0xffff
    else:
        myCS = htons(myCS)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myCS, ID, 1)
    packet = header + data
    mySocket.sendto(packet, (destAddr, 1))


def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")
    try:
        mySocket = socket(AF_INET, SOCK_RAW, icmp)
    except PermissionError:
        sys.exit("This script is used as administrator and root to use raw sockets.")

    myID = os.getpid() & 0xFFFF
    sendOnePing(mySocket, destAddr, myID)
    delay = onePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return delay


def ping(host, timeout=1, count=4):
    dest = gethostbyname(host)
    print(f"\nPinging {host} [{dest}] with Python:\n")

    delays = []
    pSent = 0
    pReceived = 0

    for i in range(count):
        pSent += 1
        delay = doOnePing(dest, timeout)
        print(delay)
        if isinstance(delay, str) and "Request timed out" in delay:
            pass
        else:
            pReceived += 1
            try:
                time_ms = float(delay.split("time=")[-1].replace("ms", ""))
                delays.append(time_ms)
            except:
                pass
        time.sleep(1)

    print("\n--- Ping statistics ---")
    print(f"{pSent} packets transmitted, {pReceived} received, "
          f"{(pSent - pReceived) / pSent * 100:.0f}% packet loss")

    if delays:
        print(f"rtt min/avg/max = {min(delays):.2f}/{sum(delays)/len(delays):.2f}/{max(delays):.2f} ms")


targets = {
    "North America (Google)": "google.com",
    "Europe (BBC UK)": "bbc.co.uk",
    "Australia (Univ. of Sydney)": "sydney.edu.au",
    "Asia (Jeju Nat. Univ, Korea)": "jnu.ac.kr"
}

for location, host in targets.items():
    print(f"\n==================== {location} ====================")
    ping(host, count=4)
