import wan_optimizer
import utils
import tcp_packet

class WanOptimizer(wan_optimizer.BaseWanOptimizer):
    """ WAN Optimizer that divides data into variable-sized
    blocks based on the contents of the file.

    This WAN optimizer should implement part 2 of project 4.
    """

    # The string of bits to compare the lower order 13 bits of hash to
    GLOBAL_MATCH_BITSTRING = '0111011001010'

    def __init__(self):
        wan_optimizer.BaseWanOptimizer.__init__(self)
        # Add any code that you like here (but do not add any constructor arguments).
        self.cache = {}
        # self.blocks = set()
        self.buffer = {}
        return


    def send_block(self, packet, dest):
        block = packet.payload
        while len(block) >= 1500:
            payload = block[:1500]
            remainder = block[1500:]
            block = remainder
            self.send(tcp_packet.Packet(packet.src, packet.dest, packet.is_raw_data, False, payload), dest)
        packet.payload = block
        self.send(packet, dest)

    def receive(self, packet):
        """ Handles receiving a packet.

        Right now, this function simply forwards packets to clients (if a packet
        is destined to one of the directly connected clients), or otherwise sends
        packets across the WAN. You should change this function to implement the
        functionality described in part 2.  You are welcome to implement private
        helper fuctions that you call here. You should *not* be calling any functions
        or directly accessing any variables in the other middlebox on the other side of 
        the WAN; this WAN optimizer should operate based only on its own local state
        and packets that have been received.
        """
        if packet.dest in self.address_to_port:
            # The packet is destined to one of the clients connected to this middlebox;
            # send the packet there.
            if packet.is_raw_data:
                if not (packet.src, packet.dest) in self.buffer:
                    self.buffer[packet.src, packet.dest] = ""
                start = len(self.buffer[(packet.src, packet.dest)])
                self.buffer[(packet.src, packet.dest)] = self.buffer[(packet.src, packet.dest)] + packet.payload
                i = max(start, 47)
                while i < len(self.buffer[(packet.src, packet.dest)]):
                    i += 1
                    h = utils.get_hash(self.buffer[(packet.src, packet.dest)][i-48:i])
                    if utils.get_last_n_bits(h, 13) == self.GLOBAL_MATCH_BITSTRING:
                        block = self.buffer[(packet.src, packet.dest)][:i]
                        self.cache[utils.get_hash(block)] = block
                        self.buffer[(packet.src, packet.dest)] = self.buffer[(packet.src, packet.dest)][i:]
                        i = 47
                        self.send_block(tcp_packet.Packet(packet.src, packet.dest, True, False, block), self.address_to_port[packet.dest])

                    # remainder = self.buffer[(packet.src, packet.dest)][self.BLOCK_SIZE:]
                    
                if packet.is_fin:
                    block = self.buffer[(packet.src, packet.dest)]
                    self.cache[utils.get_hash(block)] = block
                    self.send_block(tcp_packet.Packet(packet.src, packet.dest, True, True, block), self.address_to_port[packet.dest])
                    self.buffer[(packet.src, packet.dest)] = ""
            else:
                self.send_block(tcp_packet.Packet(packet.src, packet.dest, True, packet.is_fin, self.cache[packet.payload]), self.address_to_port[packet.dest])
        else:
            # The packet must be destined to a host connected to the other middlebox
            # so send it across the WAN.
            if packet.is_raw_data:
                if not (packet.src, packet.dest) in self.buffer:
                    self.buffer[packet.src, packet.dest] = ""
                start = len(self.buffer[(packet.src, packet.dest)])
                self.buffer[(packet.src, packet.dest)] = self.buffer[(packet.src, packet.dest)] + packet.payload
                i = max(start, 47)
                while i < len(self.buffer[(packet.src, packet.dest)]):
                    i += 1
                    h = utils.get_hash(self.buffer[(packet.src, packet.dest)][i-48:i])
                    if utils.get_last_n_bits(h, 13) == self.GLOBAL_MATCH_BITSTRING:
                        block = self.buffer[(packet.src, packet.dest)][:i]
                        if utils.get_hash(block) in self.cache:
                            self.send_block(tcp_packet.Packet(packet.src, packet.dest, False, False, utils.get_hash(block)), self.wan_port)
                        else:
                            self.cache[utils.get_hash(block)] = block
                            self.send_block(tcp_packet.Packet(packet.src, packet.dest, True, False, block), self.wan_port)
                        self.buffer[(packet.src, packet.dest)] = self.buffer[(packet.src, packet.dest)][i:]
                        i = 47

                if packet.is_fin:
                    block = self.buffer[(packet.src, packet.dest)]
                    if utils.get_hash(block) in self.cache:
                        self.send_block(tcp_packet.Packet(packet.src, packet.dest, False, True, utils.get_hash(block)), self.wan_port)
                    else:
                        self.cache[utils.get_hash(block)] = block
                        self.send_block(tcp_packet.Packet(packet.src, packet.dest, True, True, block), self.wan_port)
                    self.buffer[(packet.src, packet.dest)] = ""
            else:
                # 1/0
                self.send_block(packet, self.wan_port)
