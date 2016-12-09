omni-multicast-monitor
======================
A script to monitor multicast joins and port traffic on the Alcatel Lucent Omniswitch platform.

** Requirements **
- SNMPv2c read access configured on Omniswitch
- JSON dump of multicast IPTV channel data in current directory (see: iptv_channels.json)

**Usage:**
```
usage: omni-multicast-traffic.py [-h] -i IP -s SLOT -p PORT [-v VLAN] [-l] -c
                                 COMMUNITY

Check current multicast viewership on Alcatel Omniswitch

optional arguments:
  -h, --help            show this help message and exit
  -i IP, --ip IP        Device IP (loopback)
  -s SLOT, --slot SLOT  Device Slot
  -p PORT, --port PORT  Device Port
  -v VLAN, --vlan VLAN  Multicast VLAN
  -l, --loopback        Derive multicast VLAN from loopback IP
  -c COMMUNITY, --community COMMUNITY
                        SNMPv2 community read string
```



Example usage:
```
./omni-multicast-traffic.py -i 10.40.30.19 -s 2 -p 2 -v 319 -c public
```

Example Output:
![Sample Screenshot](omni-multicast-traffic.png?raw=true "Sample Screenshot")
