"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        ##### Begin Stage 10A #####
        self.history = {}
        ##### End Stage 10A #####

    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        ##### Begin Stage 1 #####
        latency = self.ports.get_latency(port)
        new_entry = TableEntry(
            dst = host,
            port = port,
            latency = latency,
            expire_time = FOREVER
        )
        self.table[host] = new_entry
        ##### End Stage 1 #####

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        
        ##### Begin Stage 2 #####
        dst = packet.dst
        
        if dst not in self.table:
            return
        
        route = self.table[dst]
        
        if route.latency >= INFINITY:
            return
        
        self.send(packet, port=route.port)
        ##### End Stage 2 #####

    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        
        ##### Begin Stages 3, 6, 7, 8, 10 #####
        ports_dict = self.ports.get_underlying_dict()
        ports_list = list(ports_dict.keys())
        
        for port in ports_list:
            for dst, route in self.table.items():
                port_from = route.port
                no_entry = (dst, port) not in self.history.keys()
                
                if no_entry:
                    old_ad = None
                else:
                    old_ad = self.history[(dst, port)]
                
                if self.SPLIT_HORIZON:
                    if port != port_from:
                        self.send_route(port, dst, route.latency)
                elif self.POISON_REVERSE:
                    if port == port_from:
                        if not force:
                            if no_entry or old_ad.destination != dst or old_ad.latency != INFINITY:
                                self.send_route(port, dst, INFINITY)
                                self.history[(dst, port)] = RoutePacket(dst, INFINITY)
                        else:
                            self.send_route(port, dst, INFINITY)
                            self.history[(dst, port)] = RoutePacket(dst, INFINITY)
                    else:
                        if not force:
                            if no_entry or old_ad.destination != dst or old_ad.latency != route.latency:
                                self.send_route(port, dst, route.latency)
                                self.history[(dst, port)] = RoutePacket(dst, route.latency)
                        else:
                            self.send_route(port, dst, route.latency)
                            self.history[(dst, port)] = RoutePacket(dst, route.latency)
                else:
                    self.send_route(port, dst, route.latency)
        ##### End Stages 3, 6, 7, 8, 10 #####

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        
        ##### Begin Stages 5, 9 #####
        dsts = list(self.table.keys())
        for dst in dsts:
            table_entry = self.table[dst]
            if table_entry.expire_time == FOREVER:
                return
            
            if self.POISON_EXPIRED and api.current_time() > table_entry.expire_time:
                current_route = self.table[dst]
                poison_route = TableEntry(dst, current_route.port, latency=INFINITY, expire_time=self.ROUTE_TTL)
                self.table[dst] = poison_route   
                         
            if api.current_time() > table_entry.expire_time:
                self.table.pop(dst)
        ##### End Stages 5, 9 #####

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        
        ##### Begin Stages 4, 10 #####
        expire_time = api.current_time()+self.ROUTE_TTL
        port_latency = self.ports.get_latency(port)
        new_latency = port_latency + route_latency
        current_route = self.table.get(route_dst)
        new_route = TableEntry(dst=route_dst, port=port, latency=new_latency, expire_time=expire_time)
        
        if route_latency >= INFINITY and current_route.port == port:
            current_expire_time = current_route.expire_time
            poison_route = TableEntry(dst=route_dst, port=port, latency=INFINITY, expire_time=current_expire_time)
            self.table[route_dst] = poison_route
            self.send_routes(force=False)
            return
        
        if not current_route:
            self.table[route_dst] = new_route
            self.send_routes(force=False)
            return
        
        #Rule1&2
        if new_latency < current_route or current_route.port == port:
            self.table[route_dst] = new_route
            self.send_routes(force=False)
            return
        ##### End Stages 4, 10 #####

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        ##### Begin Stage 10B #####
        for dst in self.table.keys():
            if self.SEND_ON_LINK_UP:
                self.send(port, dst, self.table[dst].latency)
        ##### End Stage 10B #####

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)

        ##### Begin Stage 10B #####
        for dst in list(self.table.keys()):
            if self.table[dst].port == port:
                if self.POISON_ON_LINK_DOWN:
                    poison_route = TableEntry(dst, port, latency=INFINITY, expire_time=self.table[dst].expire_time)
                    self.table[dst] = poison_route
                    self.send_routes(force=False)
                    
                self.table.pop(dst)       
        ##### End Stage 10B #####

    # Feel free to add any helper methods!
