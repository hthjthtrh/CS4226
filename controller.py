'''
Please add your name: Liu Renxing
Please add your matric number: A0149943R
'''

import sys
import os
import csv
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
        self.flooded = {}
        self.FIREWALL_POLICIES = []
        self.user_queue = {}
        self.import_policies()
        
        self.reset_timer = Timer(5, self.reset_stuff, recurring=True)

        self.PREMIUM_QUEUE = 1
        self.REGULAR_QUEUE = 0
        self.FREE_QUEUE = 2       

    def import_policies(self):
        
        # read policy.in
        with open('policy.in') as polifile:
            content = csv.reader(polifile, delimiter = ' ')
            lineNum = 0
            firewall_rules = -1
            QoS_rules = -1
            for row in content:
                if firewall_rules == -1:
                    print("Number of firewall rules: {}\nNumber of QOS rules: {}".format(row[0], row[1]))
                    firewall_rules = int(row[0])
                    QoS_rules = int(row[1])
                    if firewall_rules <= 0:
                        log.debug("no firewall rule")
                        if QoS_rules <= 0:
                            log.debug("no QoS rule")
                            break
                elif lineNum <= firewall_rules:
                    self.FIREWALL_POLICIES.append(row[0].strip().split(','))
                    print(self.FIREWALL_POLICIES[-1])
                elif (lineNum - firewall_rules) <= QoS_rules:
                    # line is QoS policy
                    content = row[0].strip().split(',')
                    host = IPAddr(content[0])
                    host_type = int(content[1])
                    self.user_queue[host] = host_type
                    print(host, host_type)
                lineNum += 1
        
        log.debug("Policy import complete")                    
                

    def reset_stuff(self):
        for switch in self.macMap:
            self.macMap[switch].clear()
        for switch in self.flooded:
            self.flooded[switch] = []
        
    # You can write other functions as you need.
        
    def _handle_PacketIn (self, event):    
        # install entries to the route table
        #print(self.macMap)
        def src_dst_flooded(dpid, srcIP, dstIP):
            temp = (srcIP, dstIP)
            return temp in self.flooded[dpid]

        def mac_port_known(dpid, mac):
            return self.macMap[dpid].get(mac) != None

        
        def install_enqueue():            
            q_id = 2 #default free user
            if self.user_queue.get(src_ip) != None and self.user_queue.get(dst_ip) != None:
                q_id = max(self.user_queue[src_ip], self.user_queue[dst_ip])
            elif self.user_queue.get(dst_ip) != None:
                q_id = self.user_queue[dst_ip]
            elif self.user_queue.get(src_ip) != None:
                q_id = self.user_queue[src_ip]

            log.debug("\nPutting packet of source {} destination {} into queue {}".format(src_ip, dst_ip, q_id))

            msg = of.ofp_flow_mod()
            msg.priority = 50 # lower than firewall
            msg.data = ofMsg
            msg.hard_timeout = 5
            msg.match = of.ofp_match.from_packet(packet, in_port)
            msg.actions.append(of.ofp_action_enqueue(port = self.macMap[dpid][dst_mac], queue_id = q_id))
            event.connection.send(msg)
          

        # Check the packet and decide how to route the packet
        '''
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
        '''


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
        in_port = event.port
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
            self.macMap[dpid][src_mac] = in_port

        if dst_mac.is_multicast or (not mac_port_known(dpid, dst_mac)):
            if not src_dst_flooded(dpid, src_ip, dst_ip):
                self.flooded[dpid].append((src_ip, dst_ip))
                flood()
        else:
            #installFlowEntries()
            install_enqueue()
            #forward()


    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)
        self.macMap[dpid] = {}
        self.flooded[dpid] = []
        # Send the firewall policies to the switch
       
        def sendFirewallPolicy(connection, policy):
            type = len(policy)
            msg = of.ofp_flow_mod()
            msg.priority = 100
            msg.match.dl_type = 0x800   #IPv4
            msg.match.nw_proto = 6  #TCP
            
            if type == 1:
                msg.match.nw_src = IPAddr(policy[0])
                log.debug("Blocking source {}".format(policy[0]))
            elif type == 2:
                msg.match.nw_dst = IPAddr(policy[0])
                msg.match.tp_dst = int(policy[1])
                log.debug("Blocking destination {} on port {}".format(policy[0],policy[1]))
            else:
                msg.match.nw_src = IPAddr(policy[0])
                msg.match.nw_dst = IPAddr(policy[1])
                msg.match.tp_dst = int(policy[2])
                log.debug("Blocking source {}, destination {} on port {}".format(policy[0], policy[1], policy[2]))
            msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))
            connection.send(msg)
            log.debug("Firewall entry sent")
                         
        log.debug("Setting up firewall for Switch {}".format(dpid))
        for i in self.FIREWALL_POLICIES:
            
            sendFirewallPolicy(event.connection, i)
        
    
    def _handle_ConnectionDown(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has gone down.", dpid)
        self.macMap.pop(dpid, None)
        self.flooded.pop(dpid, None)

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_tree.launch()

    # Starting the controller module
    core.registerNew(Controller)
