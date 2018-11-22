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
from pox.lib.recoco import Timer

log = core.getLogger()

class Controller(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)
        self.macMap = {}
        self.reset_timer = Timer(5, self.reset_mac_map, recurring=True)

    def reset_mac_map(self):
        for switch in self.macMap:
            self.macMap[switch].clear()
        
        
    # You can write other functions as you need.
        
    def _handle_PacketIn (self, event):    
        # install entries to the route table
        #print(self.macMap)

        def mac_port_known(dpid, mac):
            return self.macMap[dpid].get(mac) != None

        
        def install_enqueue(event, packet, outport, q_id):
            a = 1
          

        # Check the packet and decide how to route the packet
        def forward(message = None):
            log.debug("\nForwarding for packet of source h{}, destination h{}".format(src_mac, dst_mac))
            msg = of.ofp_packet_out()
            msg.data = ofMsg
            msg.actions.append(of.ofp_action_output(port = self.macMap[dpid][dst_mac]))
            event.connection.send(msg)

        # install the flow entry
        def installFlowEntries(message = None):
            log.debug("\nInstalling flow entries for hosts h{}, h{}".format(src_mac, dst_mac))
            msg = of.ofp_flow_mod()
            msg.match.dl_src = src_mac
            msg.match.dl_dst = dst_mac
            msg.hard_timeout = 5
            msg.actions.append(of.ofp_action_output(port = self.macMap[dpid][dst_mac]))
            event.connection.send(msg)

            nxt_msg = of.ofp_flow_mod()
            nxt_msg.match.dl_src = dst_mac
            nxt_msg.match.dl_dst = src_mac
            nxt_msg.hard_timeout = 5
            nxt_msg.actions.append(of.ofp_action_output(port = self.macMap[dpid][src_mac]))            
            event.connection.send(nxt_msg)


        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            log.debug("\nFlooding for packet of source h{}".format(src_mac))
            msg = of.ofp_packet_out()
            msg.data = ofMsg
            msg.actions.append(of.ofp_action_output(port = of.OFPP_ALL))
            event.connection.send(msg)


        packet = event.parsed
        dpid = dpid_to_str(event.dpid)
        ofMsg = event.ofp
        inPort = event.port
        src_mac = packet.src
        dst_mac = packet.dst
        payload = packet.payload
        src_ip = None
        dst_ip = None
        if packet.type == ethernet.IP_TYPE:
            src_ip = payload.srcip
            dst_ip = payload.dstip
        elif packet.type == ethernet.ARP_TYPE:
            src_ip = payload.protosrc
            dst_ip = payload.protodst
        '''
        print("switch: {}".format(dpid))
        print("src mac: {}, dest mac : {}".format(src_mac, dst_mac))
        print("src ip: {}, dest ip : {}".format(src_ip, dst_ip))
        '''
        # map the src_mac to the port number, but keep the earliest mapping
        if not mac_port_known(dpid, src_mac):
            self.macMap[dpid][src_mac] = inPort

        if dst_mac.is_multicast or (not mac_port_known(dpid, dst_mac)):
            flood()
        else:
            installFlowEntries()
            forward()  

        #print("\n")



    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)
        self.macMap[dpid] = {}
        
        # Send the firewall policies to the switch
        '''
        def sendFirewallPolicy(connection, policy):
            

        for i in [FIREWALL POLICIES]:
            sendFirewallPolicy(event.connection, i)
        '''
    
    def _handle_ConnectionDown(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has gone down.", dpid)

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_tree.launch()

    # Starting the controller module
    core.registerNew(Controller)
