'''
Please add your name:
Please add your matric number: 
'''

import sys
import os
from sets import Set

from pox.core import core

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_tree

from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.packet import ethernet

log = core.getLogger()

class Controller(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)
        self.macMap = {}
        self.flooded = {}
        
        
    # You can write other functions as you need.
        
    def _handle_PacketIn (self, event):    
        # install entries to the route table

        packet = event.parsed
        dpid = event.dpid
        ofMsg = event.ofp
        inPort = event.port
        src_mac = packet.src
        dst_mac = packet.dst

        # map the src_mac to the port number, but keep the earliest mapping
        if not mac_port_known(dpid, src_mac):
            self.macMap[dpid][src_mac] = inPort
        
        if mac_port_known(dpid, dst_mac):
            dest_port = self.macMap[dpid][dst_mac]
            forward()
            installFlowEntries()
        else:
            if not switch_flooded(dpid, mac):
                flood()
                self.flooded[dpid][mac] = True

        def mac_port_known(dpid, mac):
            switch_macs = self.macMap.get(dpid)
            return switch_macs.get(mac) != None

        def switch_flooded(dpid, mac):
            return self.flooded[dpid].get(mac) != None
        
        def install_enqueue(event, packet, outport, q_id):
          

        # Check the packet and decide how to route the packet
        def forward(message = None):
            log.debug("Forwarding for packet of source {}, destination {}".format(src_mac, dst_mac))
            msg = of.ofp_packet_out()
            msg.data = ofMsg
            msg.actions.append(of.ofp_action_output(port = dest_port))
            event.connection.send(msg)

        # install the flow entry
        def installFlowEntries(message = None):
            log.debug("Installing flow entries for hosts {}, {}".format(src_mac, dst_mac))
            msg = of.ofp_flow_mod()
            msg.match.dl_dst = dst_mac
            msg.actions.append(of.ofp_action_output(port = dest_port))

            nxt_msg = of.ofp_flow_mod()
            nxt_msg.match.dl_dst = src_mac
            nxt_msg.actions.append(of.ofp_action_output(port = inPort))

            event.connection.send(msg)
            event.connection.send(nxt_msg)


        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            log.debug("Flooding for packet of source {}".format(src_mac))
            msg = of.ofp_packet_out()
            msg.data = ofMsg
            msg.actions.append(of.ofp_action_output(port = of.OFPP_ALL)
            event.connection.send(msg)
    


    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)
        self.macMap[dpid] = {}
        self.flooded[dpid] = {}
        
        # Send the firewall policies to the switch
        def sendFirewallPolicy(connection, policy):
            

        for i in [FIREWALL POLICIES]:
            sendFirewallPolicy(event.connection, i)
            

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_tree.launch()

    # Starting the controller module
    core.registerNew(Controller)
