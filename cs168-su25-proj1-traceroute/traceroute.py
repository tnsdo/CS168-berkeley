import util
import time

SELECT_TIMEOUT = 0.3  #timeout value for select


# Your program should send TTLs in the range [1, TRACEROUTE_MAX_TTL] inclusive.
# Technically IPv4 supports TTLs up to 255, but in practice this is excessive.
# Most traceroute implementations cap at approximately 30.  The unit tests
# assume you don't change this number.
TRACEROUTE_MAX_TTL = 30

# Cisco seems to have standardized on UDP ports [33434, 33464] for traceroute.
# While not a formal standard, it appears that some routers on the internet
# will only respond with time exceeeded ICMP messages to UDP packets send to
# those ports.  Ultimately, you can choose whatever port you like, but that
# range seems to give more interesting results.
TRACEROUTE_PORT_NUMBER = 33434  # Cisco traceroute port number.

# Sometimes packets on the internet get dropped.  PROBE_ATTEMPT_COUNT is the
# maximum number of times your traceroute function should attempt to probe a
# single router before giving up and moving on.
PROBE_ATTEMPT_COUNT = 3

class IPv4:
    # Each member below is a field from the IPv4 packet header.  They are
    # listed below in the order they appear in the packet.  All fields should
    # be stored in host byte order.
    #
    # You should only modify the __init__() method of this class.
    version: int
    header_len: int  # Note length in bytes, not the value in the packet.
    tos: int         # Also called DSCP and ECN bits (i.e. on wikipedia).
    length: int      # Total length of the packet.
    id: int
    flags: int
    frag_offset: int
    ttl: int
    proto: int
    cksum: int
    src: str
    dst: str

    def __init__(self, buffer: bytes):
        
        b = ''.join(format(byte, '08b') for byte in [*buffer])
        
        self.version = int (b[:4], 2)
        self.header_len = int (b[4:8], 2) * 4
        
        self.tos = buffer[1]
        self.length = int (b[16:32], 2)
        self.id = int (b[32:48], 2)
        
        self.flags = int (b[48:51], 2)
        self.frag_offset = int (b[51:64], 2)
        
        self.ttl = buffer[8]
        self.proto = buffer[9]
        self.cksum = int (b[80:96], 2)
        
        self.src = self.convert_ip(buffer[12:16])
        self.dst = self.convert_ip(buffer[16:20])

    #convert 4byte address to decimal format
    def convert_ip(self, ip_bytes: bytes) -> str:
        return '.'.join(str(byte) for byte in ip_bytes)

    def __str__(self) -> str:
        return f"IPv{self.version} (tos 0x{self.tos:x}, ttl {self.ttl}, " + \
            f"id {self.id}, flags 0x{self.flags:x}, " + \
            f"ofsset {self.frag_offset}, " + \
            f"proto {self.proto}, header_len {self.header_len}, " + \
            f"len {self.length}, cksum 0x{self.cksum:x}) " + \
            f"{self.src} > {self.dst}"


class ICMP:
    # Each member below is a field from the ICMP header.  They are listed below
    # in the order they appear in the packet.  All fields should be stored in
    # host byte order.
    #
    # You should only modify the __init__() function of this class.
    type: int
    code: int
    cksum: int

    def __init__(self, buffer: bytes):
        
        b = ''.join(format(byte, '08b') for byte in [*buffer])
        
        self.type = buffer[0]
        self.code = buffer[1]
        self.cksum = int (b[16:32], 2)

    def __str__(self) -> str:
        return f"ICMP (type {self.type}, code {self.code}, " + \
            f"cksum 0x{self.cksum:x})"


class UDP:
    # Each member below is a field from the UDP header.  They are listed below
    # in the order they appear in the packet.  All fields should be stored in
    # host byte order.
    #
    # You should only modify the __init__() function of this class.
    src_port: int
    dst_port: int
    len: int
    cksum: int

    def __init__(self, buffer: bytes):
        
        b = ''.join(format(byte, '08b') for byte in [*buffer])
        
        self.src_port = int (b[:16], 2)
        self.dst_port = int (b[16:32], 2)
        self.len = int (b[32:48], 2)
        self.cksum = int (b[48:64], 2)

    def __str__(self) -> str:
        return f"UDP (src_port {self.src_port}, dst_port {self.dst_port}, " + \
            f"len {self.len}, cksum 0x{self.cksum:x})"

# TODO feel free to add helper functions if you'd like


def traceroute(sendsock: util.Socket, recvsock: util.Socket, ip: str) -> list[list[str]]:
    """ Run traceroute and returns the discovered path. """
    result = []
    
    for ttl in range(1, TRACEROUTE_MAX_TTL + 1):
        sendsock.set_ttl(ttl) 
        #save routers
        routers = set()
        
        #send packets to each ttl
        for _ in range(PROBE_ATTEMPT_COUNT):
            sendsock.sendto("Potato".encode(), (ip, TRACEROUTE_PORT_NUMBER))
            
            start_time = time.time()  #track time to avoid timeout error
            
            while time.time() - start_time < SELECT_TIMEOUT:
                if recvsock.recv_select():
                    buf, address = recvsock.recvfrom()
                    
                    if not buf:
                        break
                    
                    routers.add(address[0])
                    
                    #if response from ip, break the loop
                    if address[0] == ip:
                        result.append(list(routers))
                        util.print_result(result[-1], ttl)
                        return result
                    else:
                        break

        #save results
        result.append(list(routers))
        util.print_result(result[- 1], ttl)
        
        
        if ip in routers:
            return result
        
    return result


if __name__ == '__main__':
    args = util.parse_args()
    ip_addr = util.gethostbyname(args.host)
    print(f"traceroute to {args.host} ({ip_addr})")
    traceroute(util.Socket.make_udp(), util.Socket.make_icmp(), ip_addr)
