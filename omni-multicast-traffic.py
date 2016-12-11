#!/usr/bin/env python
from pysnmp.entity.rfc3413.oneliner import cmdgen
from time import sleep
import json
import argparse
import sys
import re

def load_json(fname):
    with open(fname) as json_file:
        dict = json.loads(json_file.read())
    return dict

def snmp_walk_oid(host,community,oid):
    try:
        cg = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData(community)
        transport = cmdgen.UdpTransportTarget((host, 161),timeout=3,retries=3)
        errorIndication, errorStatus, errorIndex, varBindTable = cg.nextCmd(comm_data, transport, oid)

        if errorIndication:
            raise Exception(errorIndication)
            
    except Exception as ex:
        return ex
    else:
        return varBindTable

def snmp_get_single_oid(host,community,oid):
    try:
        cg = cmdgen.CommandGenerator()
        comm_data = cmdgen.CommunityData(community)
        transport = cmdgen.UdpTransportTarget((host, 161),timeout=3,retries=3)
        errorIndication, errorStatus, errorIndex, varBindTable = cg.getCmd(comm_data, transport, oid)

        if errorIndication:
            print errorIndication

    except Exception as ex:
        return ex
    else:
        return varBindTable

def snmp_key_val_split(var_bind_table):
    var_table = {}
    for x in var_bind_table:
        key = str(x[0][0]).split(".")[-1]
        val = x[0][1]
        var_table[key] = val
    return var_table

def snmp_key_to_mcast(key):
    p = key.split('.')
    mcast = "%s.%s.%s.%s" % (p[20],p[21],p[22],p[23])
    return mcast

def colorize(text,color):
    # Colors
    colors = {}
    colors['PINK'] = '\033[95m'
    colors['BLUE'] = '\033[94m'
    colors['GREEN'] = '\033[92m'
    colors['YELLOW'] = '\033[93m'
    colors['RED'] = '\033[91m'
    # Remove coloring
    ENDC = '\033[0m'
    text = colors[color] + text + ENDC
    return text

def loopback_vlan(ip):
    octets = ip.split('.')
    base = int(octets[2]) * 10
    vlan = str(base + int(octets[3]))
    return vlan

def format_slot_port(slot,port):
    formatted_port = '%02d' % int(port)
    formatted = "%d0%s" % (int(slot),formatted_port)
    return formatted

def calc_iptv_traffic(hd,sd,music):
    pps_min = 0
    mbps_min = 0
    pps_min = (hd * 570) + (sd * 100) + (music * 15)
    mbps_min = (hd * 6) + (sd * 1) + (music * .2)
    return pps_min,mbps_min


if __name__ == "__main__":
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description='Check current multicast viewership on Alcatel Omniswitch')
    parser.add_argument('-i','--ip', help='Device IP (loopback)', required=True)
    parser.add_argument('-s','--slot', help='Device Slot', required=True)
    parser.add_argument('-p','--port', help='Device Port', required=True)
    parser.add_argument('-v','--vlan', help='Multicast VLAN', required=False)
    parser.add_argument('-l','--loopback', help='Derive multicast VLAN from loopback IP', required=False, action='store_true')
    parser.add_argument('-c','--community', help='SNMPv2 community read string', required=True)
    args = vars(parser.parse_args())
    ip = args['ip']
    slot = args['slot']
    port = args['port']
    vlan = args['vlan']
    use_loopback = args['loopback']
    community = args['community']

    # Load JSON data
    iptv_channels = load_json('iptv_channels.json')

    # SNMP OIDs
    # ifOutOctets
    octets_out_oid = ".1.3.6.1.2.1.2.2.1.16"
    #ifOutMulticastPkts
    mcast_out_oid = ".1.3.6.1.2.1.31.1.1.1.4"
    #alaIgmpMemberTimeout
    igmp_oid = ".1.3.6.1.4.1.6486.800.1.2.1.34.1.1.3.1.1.7"

    # Get VLAN
    if use_loopback:
        vlan = loopback_vlan(ip)

    # Format slot port to match SNMP iface index standard used on Omniswitch
    aluport = format_slot_port(slot,port)

    # Append index and vlan to OIDs as required
    mcast_full_oid = mcast_out_oid  + "." + aluport
    octets_full_oid = octets_out_oid + "." + aluport
    igmp_full_oid = igmp_oid + "." + vlan + "." + aluport

    # Initialize counters and dictionaries
    count = 0;

while True:
    try:
        mcast_r = snmp_get_single_oid(ip,community,mcast_full_oid)
        octets_r = snmp_get_single_oid(ip,community,octets_full_oid)
        igmp_r = snmp_walk_oid(ip,community,igmp_full_oid)

        mcast_count = 0
        mcast_hd = 0
        mcast_sd = 0
        mcast_music = 0

        mc_cur = mcast_r[0][1]
        octet_cur = octets_r[0][1]
  
        if count == 0:
            diff = 0
            diff2 = 0
        else:
            diff = mc_cur - mc_prev
            diff2 = octet_cur - octet_prev

        pps = diff / 5
        mbps = (((diff2 * 8) / 1024) / 1024) / 5


        # Clear the screen
        print "\033[2J"
        # Jump to 0,0
        print "\033[0;0H" + colorize("Omniswitch Port: %s - %s/%s" % (ip,slot,port),"GREEN")

        for i in igmp_r:
            i_key = str(i[0][0])
            i_val = i[0][1]
            mcast = snmp_key_to_mcast(i_key)
            if re.search(r"^239\.192\.", mcast) is not None and re.match(r"239.192.0.1",mcast) is None:
                if i_key > 100:
                    lifetime = colorize(str(i_val),"GREEN")
                else: 
                    lifetime = colorize(str(i_val),"RED")
                
                channel_num = iptv_channels[mcast]['channel']
                channel_name = iptv_channels[mcast]['name']

                if iptv_channels[mcast]['type'] == "HD":
                    mcast_hd += 1
                elif iptv_channels[mcast]['type'] == "SD":
                    mcast_sd += 1
                elif iptv_channels[mcast]['type'] == "MUSIC":
                    mcast_music += 1
                mcast_count += 1
                
                print colorize("Multicast Group: ","BLUE") + mcast + colorize(" Life: ","BLUE") + lifetime + " seconds\t" + colorize("%s - %s" % (channel_num,channel_name),"YELLOW")
        print "%s %s %s %s %s %s %s %s %s" % (colorize("Total IPTV Channels:","PINK"),colorize(str(mcast_count),"GREEN"),"(HD:",colorize(str(mcast_hd),"GREEN"),"SD:",colorize(str(mcast_sd),"GREEN"),"MUSIC:",colorize(str(mcast_music),"GREEN"),")")
        print "================================================";
        (pps_min, mbps_min) = calc_iptv_traffic(mcast_hd,mcast_sd,mcast_music)
        if pps_min > pps:
            pps_txt = colorize("%01d" % pps,"RED")
        else:
            pps_txt = colorize("%01d" % pps,"GREEN")

        if mbps_min > mbps:
            mbps_txt = colorize("%.3f" % mbps,"RED")
        else:
            mbps_txt = colorize("%.3f" % mbps,"GREEN")

        print "%s %s %s %s" % (colorize("Multicast Traffic Out: ","PINK"),pps_txt,"pps",colorize("(Min Expecting: %d)" % pps_min,"BLUE"))
        print "%s %s %s %s" % (colorize("Port Traffic Out: ","PINK"),mbps_txt,"Mbps",colorize("(Min Expecting: %d)" % int(mbps_min),"BLUE"))     
  
        mc_prev = mc_cur
        octet_prev = octet_cur
        count += 1
        sleep(5)
    except KeyboardInterrupt:
        sys.exit()


