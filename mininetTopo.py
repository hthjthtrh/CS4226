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
from mininet.link import Link
from mininet.node import RemoteController

net = None

class CustomTopo(Topo):

    def addANode(node):
        type = node[0]
        num = int(node[1:])
        if type == 'h':
            if node in hostSet:
                return node
            else:
                n = self.addHost('h%d' % num)
                hostSet.add(n)
                return n
        else:
            if node in switchSet:
                return node
            else:
                sconfig = {'dpid': "%016x" % num}
                n = self.addSwitch('s%d' % num, **sconfig)
                switchSet.add(n)
                return n
			
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

        hostSet = set()
        switchSet = set()
        linkSet = set()

        # read topology.in
        with open('topology.in', newline = '') as topofile:
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
                    node1 = addANode(splitRow[1])
                    self.addLink(node1, node2, bw=int(splitRow[2]))                
                lineNum += 1

	
	# You can write other functions as you need.

	# Add hosts
    # > self.addHost('h%d' % [HOST NUMBER])

	# Add switches
    # > sconfig = {'dpid': "%016x" % [SWITCH NUMBER]}
    # > self.addSwitch('s%d' % [SWITCH NUMBER], **sconfig)

	# Add links
	# > self.addLink([HOST1], [HOST2])


def startNetwork():
    info('** Creating the tree network\n')
    topo = CustomTopo()

    global net
    net = Mininet(topo=topo, link = Link,
                  controller=lambda name: RemoteController(name, ip='127.0.0.1'),
                  listenPort=6633, autoSetMacs=True)

    info('** Starting the network\n')
    net.start()

    # Create QoS Queues
    # > os.system('sudo ovs-vsctl -- set Port [INTERFACE] qos=@newqos \
    #            -- --id=@newqos create QoS type=linux-htb other-config:max-rate=[LINK SPEED] queues=0=@q0,1=@q1,2=@q2 \
    #            -- --id=@q0 create queue other-config:max-rate=[LINK SPEED] other-config:min-rate=[LINK SPEED] \
    #            -- --id=@q1 create queue other-config:min-rate=[X] \
    #            -- --id=@q2 create queue other-config:max-rate=[Y]')

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
