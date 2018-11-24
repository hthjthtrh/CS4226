'''
Please add your name:
Please add your matric number: 
'''

import os
import sys
import atexit
import csv
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import RemoteController

net = None

class CustomTopo(Topo):
			
    def __init__(self):

        def addANode(node):
            type = node[0]
            num = int(node[1:])
            if type == 'h':
                if node in self.hostSet:
                    return node
                else:
                    n = self.addHost('h%d' % num)
                    self.hostSet.add(n)
                    return n
            else:
                if node in self.switchSet:
                    return node
                else:
                    sconfig = {'dpid': "%016x" % num}
                    n = self.addSwitch('s%d' % num, **sconfig)
                    self.switchSet.add(n)
                    return n

        # Initialize topology
        Topo.__init__(self)

        self.hostSet = set()
        self.switchSet = set()
        self.bwMap = list()

        # read topology.in
        with open('topology.in') as topofile:
            content = csv.reader(topofile, delimiter = ' ')
            lineNum = 0
            numLinks = 0
            for row in content:
                if numLinks == 0:
                    print("Number of hosts ", row[0])
                    print("Number of switches ", row[1])
                    print("Number of links ", row[2])
                    numLinks = int(row[2])                    
                elif lineNum <= numLinks:
                    splitRow = row[0].strip().split(',')
                    node1 = addANode(splitRow[0])
                    node2 = addANode(splitRow[1])
                    self.addLink(node1, node2)
                    self.bwMap.append(splitRow)
                lineNum += 1

def startNetwork():
    info('** Creating the tree network\n')
    topo = CustomTopo()

    global net
    net = Mininet(topo=topo, link = TCLink,
                  controller=lambda name: RemoteController(name, ip='192.168.56.101'),
                  listenPort=6633, autoSetMacs=True)

    info('** Starting the network\n')
    net.start()

    info('** QoS configurations\n')

    def getBW(node1, node2):
        for link in topo.bwMap:
            if node1 == link[0] and node2 == link[1]:
                return int(link[2]) * 1000000

    n = 0
    for link in topo.links(True, False, True):
        for switch in topo.switches():
            linkInfo = link[2]
            for i in [1, 2]:
                if linkInfo["node%i" % (i)] == switch:
                    n += 1
                    port = linkInfo["port%i" % (i)]
                    node1 = linkInfo["node1"]
                    node2 = linkInfo["node2"]
                    bw = getBW(node1, node2)
                    wSpd = 0.8 * bw
                    xSpd = 0.6 * bw
                    ySpd = 0.3 * bw
                    zSpd = 0.2 * bw
                    interface = "%s-eth%s" % (switch, port)
                    # OS system call
                    os.system("sudo ovs-vsctl -- set Port %s qos=@newqos \
                        -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%i queues=0=@q0,1=@q1,2=@q2 \
                        -- --id=@q0 create queue other-config:max-rate=%i other-config:min-rate=%i \
                        -- --id=@q1 create queue other-config:min-rate=%i \
                        -- --id=@q2 create queue other-config:max-rate=%i" % (interface, bw, xSpd, ySpd, wSpd, zSpd))

    print("Total QoS: %i" % (n))

    info('** Running CLI\n')
    CLI(net)

def stopNetwork():
    if net is not None:
        net.stop()
        # Remove QoS and Queues
        os.system('sudo ovs-vsctl --all destroy Qos')
        os.system('sudo ovs-vsctl --all destroy Queue')


if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)

    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
