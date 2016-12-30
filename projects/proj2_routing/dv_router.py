"""Your awesome Distance Vector router for CS 168."""

import sim.api as api
import sim.basics as basics

# We define infinity as a distance of 16.
INFINITY = 16


class DVRouter(basics.DVRouterBase):
    # NO_LOG = True # Set to True on an instance to disable its logging
    # POISON_MODE = True # Can override POISON_MODE here
    # DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

    def __init__(self):
        """
        Called when the instance is initialized.

        You probably want to do some additional initialization here.

        """
        self.table = {} #maps dest -> (first_port, total_cost, expiration_time)
        self.links = {} #maps port -> (host, latency)
        self.neighbors = {} #maps neighbor -> port
        self.start_timer()  # Starts calling handle_timer() at correct rate

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this Entity goes up.

        The port attached to the link and the link latency are passed
        in.

        """
        self.links[port] = [None, latency]
        self.advertise(port)
        

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this Entity does down.

        The port number used by the link is passed in.

        """
        if self.links[port][0]:
            self.neighbors.pop(self.links[port][0])
        self.links.pop(port)

        for dest, info in dict(self.table).items():
            fport = info[0]
            if fport == port:
                self.table.pop(dest)
                if dest in self.neighbors:
                    self.table[dest] = [self.neighbors[dest], self.links[self.neighbors[dest]][1], api.current_time()+self.ROUTE_TIMEOUT+10000]
                    x = basics.RoutePacket(dest, self.table[dest][1])
                    self.send(x, self.table[dest][0], flood=True)
                    if self.POISON_MODE:
                        x = basics.RoutePacket(dest, INFINITY)
                        self.send(x, self.table[dest][0])
                elif self.POISON_MODE:
                    x = basics.RoutePacket(dest, INFINITY)
                    self.send(x, port, flood=True)


    def advertise(self, p):
        # p = self.neighbors[neighbor]
        for dest, info in self.table.items():
            if info[0] == p:
                if self.POISON_MODE:
                    x = basics.RoutePacket(dest, INFINITY)
                    self.send(x, p)
            else:
                if self.POISON_MODE or info[1] < INFINITY:
                    x = basics.RoutePacket(dest, info[1])
                    self.send(x, p)


    def handle_rx(self, packet, port):
        """
        Called by the framework when this Entity receives a packet.

        packet is a Packet (or subclass).
        port is the port number it arrived on.

        You definitely want to fill this in.

        """
        #self.log("RX %s on %s (%s)", packet, port, api.current_time())

        # print(api.get_name(self), packet.src, packet.dst, self.table)

        if isinstance(packet, basics.RoutePacket):
            curr = min(INFINITY, self.table[packet.destination][1]) if packet.destination in self.table else INFINITY+1
            rcost = min(INFINITY, packet.latency+self.links[port][1])
            ncost = self.links[self.neighbors[packet.destination]][1] if packet.destination in self.neighbors else INFINITY

            if curr == rcost:
                if not packet.destination in self.table or self.table[packet.destination][2] < api.current_time()+self.ROUTE_TIMEOUT:
                    self.table[packet.destination] = [port, packet.latency+self.links[port][1], api.current_time()+self.ROUTE_TIMEOUT]
            elif rcost < curr or self.table[packet.destination][0] == port:
                if ncost < rcost:
                    self.table[packet.destination] = [self.neighbors[packet.destination], ncost, api.current_time()+self.ROUTE_TIMEOUT+10000]
                    x = basics.RoutePacket(packet.destination, self.table[packet.destination][1])
                    self.send(x, self.table[packet.destination][0], flood=True)
                    if self.POISON_MODE:
                        x = basics.RoutePacket(packet.destination, INFINITY)
                        self.send(x, self.table[packet.destination][0])
                else:
                    self.table[packet.destination] = [port, rcost, api.current_time()+self.ROUTE_TIMEOUT]
                    if self.POISON_MODE or self.table[packet.destination][1] < INFINITY:
                        x = basics.RoutePacket(packet.destination, self.table[packet.destination][1])
                        self.send(x, port, flood=True)
                    if self.POISON_MODE:
                        x = basics.RoutePacket(packet.destination, INFINITY)
                        self.send(x, port)
            # print("routing",api.get_name(self), packet.src, packet.destination, packet.latency, self.table, self.links)


            # if not packet.destination in self.table or self.table[packet.destination][1] > packet.latency+self.links[port][1] or self.table[packet.destination][0] == port:
            #     self.table[packet.destination] = [port, packet.latency+self.links[port][1], api.current_time()+self.ROUTE_TIMEOUT]
            #     x = basics.RoutePacket(packet.destination, self.table[packet.destination][1])
            #     self.send(x, port, flood=True)
            #     if self.POISON_MODE:
            #         x = basics.RoutePacket(packet.destination, INFINITY)
            #         self.send(x, port)
            # elif self.table[packet.destination][1] == packet.latency+self.links[port][1] and self.table[packet.destination][2] < api.current_time()+self.ROUTE_TIMEOUT:
            #     self.table[packet.destination] = [port, packet.latency+self.links[port][1], api.current_time()+self.ROUTE_TIMEOUT]
            
        elif isinstance(packet, basics.HostDiscoveryPacket):
            self.links[port][0] = packet.src
            self.neighbors[packet.src] = port;
            # print(api.get_name(self), self.links[port], self.neighbors[packet.src])
            if not packet.src in self.table or self.links[port][1] <= self.table[packet.src][1]:
                self.table[packet.src] = [port, self.links[port][1], api.current_time()+self.ROUTE_TIMEOUT+10000]
            
            x = basics.RoutePacket(packet.src, self.table[packet.src][1])
            self.send(x, port, flood=True)
            if self.POISON_MODE:
                x = basics.RoutePacket(packet.src, INFINITY)
                self.send(x, port)
            #Todo: advertise routes to neighbor
            # print(self.table)
            self.advertise(port)

        else:
            # print(api.get_name(self), packet.src, packet.dst, self.table, self.links)
            if packet.dst in self.table and self.table[packet.dst][0] != port and self.table[packet.dst][1] < INFINITY:
                # print(api.get_name(self), packet.src, packet.dst, self.table)
                self.send(packet, self.table[packet.dst][0])

    def handle_timer(self):
        """
        Called periodically.

        When called, your router should send tables to neighbors.  It
        also might not be a bad place to check for whether any entries
        have expired.

        """
        ct = api.current_time()
        for dest, info in dict(self.table).items():
            if info[2] <= ct:
                self.table.pop(dest)
                if dest in self.neighbors:
                    self.table[dest] = [self.neighbors[dest], self.links[self.neighbors[dest]][1], api.current_time()+self.ROUTE_TIMEOUT+10000]
                    # x = basics.RoutePacket(dest, self.table[dest][1])
                    # self.send(x, self.table[dest][0], flood=True)
                    # if self.POISON_MODE:
                    #     x = basics.RoutePacket(dest, INFINITY)
                    #     self.send(x, self.table[dest][0])
                elif self.POISON_MODE:
                    x = basics.RoutePacket(dest, INFINITY)
                    self.send(x, None, flood=True)

            if dest in self.table:
                if self.POISON_MODE or self.table[dest][1] < INFINITY:
                    x = basics.RoutePacket(dest, self.table[dest][1])
                    self.send(x, self.table[dest][0], flood=True)
                if self.POISON_MODE:
                    x = basics.RoutePacket(dest, INFINITY)
                    self.send(x, self.table[dest][0])
