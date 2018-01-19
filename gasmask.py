#!/usr/bin/env python
# encoding: UTF-8

"""
    GasMasK - All in one Information gathering tool - OSINT
    This file is part of GasMasK Project

    Written by: @maldevel
    Website: https://www.twelvesec.com/
    GIT: https://github.com/twelvesec/gasmask

    TwelveSec (@Twelvesec)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    For more see the file 'LICENSE' for copying permission.
"""

__author__ = "maldevel"
__license__ = "GPLv3"
__version__ = "1.0"

#######################################################

import argparse
from argparse import RawTextHelpFormatter
import validators
import sys
import socket
import whois
import dns.resolver
import collections
import re
from dns import reversename, resolver
import requests
import time

#######################################################

from requests.packages.urllib3.exceptions import InsecureRequestWarning #remove insecure https warning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning) #remove insecure https warning

#######################################################

message = """
   ______           __  ___           __ __
  / ____/___ ______/  |/  /___ ______/ //_/
 / / __/ __ `/ ___/ /|_/ / __ `/ ___/ ,<
/ /_/ / /_/ (__  ) /  / / /_/ (__  ) /| |
\____/\__,_/____/_/  /_/\__,_/____/_/ |_|

GasMasK - All in one Information gathering tool - OSINT
Ver. {}
Written by: @maldevel
https://www.twelvesec.com/
""".format(__version__)

#######################################################

## Validate Domain name ##

def CheckDomain(value):
    if not validators.domain(value):
        raise argparse.ArgumentTypeError('Invalid {} domain.'.format(value))
    return value

#######################################################

## Verify domain/ip ##

def CheckDomainOrIP(value):

	if not validators.domain(value) and not validators.ip_address.ipv4(value):
		raise argparse.ArgumentTypeError('Invalid domain or ip address ({}).'.format(value))
	return value

#######################################################

## Get Domain ip address ##

def VerifyHostname(value):

    try:
        ip = socket.gethostbyname(value)
        return ip
    except Exception as e:
        return False

#######################################################

## Perform whois query ##

def WhoisQuery(value):

    whoisData = collections.OrderedDict()
    whoisData["name"] = ["-", "Name:"]
    whoisData["org"] = ["-", "Organization:"]
    whoisData["address"] = ["-", "Address:"]
    whoisData["city"] = ["-", "City:"]
    whoisData["zipcode"] = ["-", "Zip code:"]
    whoisData["country"] = ["-", "Country:"]
    whoisData["emails"] = ["-", "Emails:"]
    whoisData["registrar"] = ["-", "Registrar:"]
    whoisData["whois_server"] = ["-", "Whois Server:"]
    whoisData["updated_date"] = ["-", "Updated Date:"]
    whoisData["expiration_date"] = ["-", "Expiration Date:"]
    whoisData["creation_date"] = ["-", "Creation Date:"]
    whoisData["name_servers"] = ["-", "Name Servers:"]

    domain = whois.whois(value)

    for rec in whoisData:
        if domain[rec]:
            if isinstance(domain[rec], list):
                if rec is 'name_servers':
                    whoisData[rec][0] = []
                    for val in domain[rec]:
                        whoisData[rec][0].append(val + ":" + VerifyHostname(val))
                else:
                    whoisData[rec][0] = []
                    for val in domain[rec]:
                        whoisData[rec][0].append(val)
            else:
                whoisData[rec][0] = str(domain[rec])

    return whoisData

#######################################################

## Perform DNS queries ##

def DnsQuery(value, dnsserver):

	dnsData = {
        "A":[],
        "CNAME":[],
        "HINFO":[],
        "MX":[],
        "NS":[],
        "PTR":[],
        "SOA":[],
        "TXT":[],
        "SPF":[],
        "SRV":[],
        "RP":[]
    }

	myresolver = dns.resolver.Resolver()
	myresolver.nameservers = [dnsserver]

	for rec in dnsData:
		try:
			answers = myresolver.query(value, rec)
			for answer in answers:
				if rec is 'NS':
					dnsData[rec].append(answer.to_text() + ":" + VerifyHostname(answer.to_text()))
				elif rec is 'MX':
					domain_name = re.search(' (.*)\.', answer.to_text(), re.IGNORECASE).group(1)
					dnsData[rec].append(answer.to_text() + ":" + VerifyHostname(domain_name))
				else:
					dnsData[rec].append(answer.to_text())
		except Exception as e:
			dnsData[rec].append('-')

	return dnsData

#######################################################

## IP DNS Reverse lookup ##

def ReverseIPQuery(value, dnsserver):

	try:
		revname = reversename.from_address(value)
		myresolver = dns.resolver.Resolver()
		myresolver.nameservers = [dnsserver]
		return str(myresolver.query(revname, 'PTR')[0]).rstrip('.')
	except Exception as e:
		print e
		return ''

#######################################################

## GET HTTP response status code and HTML title ##

def HttpStatusQuery(value):

	r = requests.get('http://{}'.format(value), verify=False)
	title = ''

	if r.status_code == 200:
		title = re.search('(?<=<title>).+?(?=</title>)', r.text, re.DOTALL)
		if title:
			title = title.group().strip()
		else:
			title = ''

	return r.status_code, title

#######################################################

## Clean HTML tags ##

def CleanHTML(results):

	res = results
	res = re.sub('<em>', '', res)
	res = re.sub('<b>', '', res)
	res = re.sub('</b>', '', res)
	res = re.sub('</em>', '', res)
	res = re.sub('%2f', ' ', res)
	res = re.sub('%3a', ' ', res)
	res = re.sub('<strong>', '', res)
	res = re.sub('</strong>', '', res)
	res = re.sub('<wbr>', '', res)
	res = re.sub('</wbr>', '', res)

	return res

#######################################################

## Extract Emails ##

def GetEmails(results, value):

	res = results
	res = CleanHTML(res)

	temp = re.compile(
	    '[a-zA-Z0-9.\-_+#~!$&\',;=:]+' +
	    '@' +
	    '[a-zA-Z0-9.-]*' +
	    value)

	emails = temp.findall(res)
	final = []
	for email in emails:
		final.append(email.lower())

	return sorted(set(final))

#######################################################

## Extract Hostnames ##

def GetHostnames(results, value):

	res = results
	res = CleanHTML(res)

	temp = re.compile('[a-zA-Z0-9.-]*\.' + value)
	hostnames = temp.findall(res)
	final = []
	for host in hostnames:
		final.append(host.lower())

	return sorted(set(final))

#######################################################

## Get All Hostnames ##

def GetHostnamesAll(results):

	res = results
	temp = re.compile('<cite>(.*?)</cite>')
	hostname = temp.findall(res)
	vhosts = []

	for x in hostname:
		r = ''
		if x.count(':'):
			r = x.split(':')[1].split('/')[2]
		else:
			r = x.split("/")[0]
		vhosts.append(r)

	return sorted(set(vhosts))

#######################################################

## Google search ##

def GoogleSearch(value, useragent, limit):

	server = "www.google.com"
	quantity = 100
	counter = 0
	step = 100
	results = ""

	while counter <= limit:
		try:
			url = "https://" + server + "/search?num=" + str(quantity) + "&start=" + str(counter) + "&hl=en&meta=&q=%40%22" + value + "%22"
		 	r = requests.get(url, headers={'User-Agent': useragent})
		 	results += r.content
		except Exception,e:
			print e

		time.sleep(1)
		counter += step

	return GetEmails(results, value), GetHostnames(results, value)

#######################################################

## Bing search ##

def BingSearch(value, useragent, limit):

	server = "www.bing.com"
	quantity = 50
	counter = 0
	step = 50
	results = ""

	while counter <= limit:
		try:
			url = "https://" + server + "/search?q=%40" + value + "&count=" + str(quantity) + "&first=" + str(counter)
		 	r = requests.get(url, headers={'User-Agent': useragent})
		 	results += r.content
		except Exception,e:
			print e

		time.sleep(1)
		counter += step

	return GetEmails(results, value), GetHostnames(results, value)

#######################################################

## ASK search ##

def AskSearch(value, useragent):

	server = "www.ask.com"
	limit = 5
	step = 1
	page = 1
	results = ""

	while page <= limit:
		try:
			url = "https://" + server + "/web?q=%40%22" + value + "%22&page=" + str(page)
		 	r = requests.get(url, headers={'User-Agent': useragent})
		 	results += r.content
		except Exception,e:
			print e

		time.sleep(1)
		page += step

	return GetEmails(results, value), GetHostnames(results, value)

#######################################################

## Dogpile search ##

def DogpileSearch(value, useragent, limit):

	server = "www.dogpile.com"
	step = 15
	counter = 1
	results = ""

	while counter <= limit:
		try:
			url = "https://" + server + "/search/web?qsi=" + str(counter) + "&q=%40" + value
		 	r = requests.get(url, verify=False, headers={'User-Agent': useragent})
		 	results += r.content
		except Exception,e:
			print e

		time.sleep(1)
		counter += step

	return GetEmails(results, value), GetHostnames(results, value)

#######################################################

## Yahoo search ##

def YahooSearch(value, useragent, limit):

	server = "search.yahoo.com"
	step = 10
	counter = 1
	results = ""

	while counter <= limit:
		try:
			url = "https://" + server + "/search?p=%40" + value + "&b=" + str(counter) + "&pz=10"
		 	r = requests.get(url, headers={'User-Agent': useragent})
		 	results += r.content
		except Exception,e:
			print e

		time.sleep(1)
		counter += step

	return GetEmails(results, value), GetHostnames(results, value)

#######################################################

## Bing search ##

def YandexSearch(value, useragent, limit):

	server = "yandex.com"
	quantity = 50
	step = 50
	results = ""
	page = 0
	counter = 0

	while counter <= limit:
		try:
			url = "https://" + server + "/search/?text=%22%40" + value + "%22&numdoc=" + str(quantity) + "&p=" + str(page) + "&lr=10418"
		 	r = requests.get(url, headers={'User-Agent': useragent})
		 	results += r.content
		except Exception,e:
			print e

		time.sleep(1)
		counter += step
		page += 1

	return GetEmails(results, value), GetHostnames(results, value)

#######################################################

## Bing Virtual Hosts ##

def BingVHostsSearch(value, useragent, limit):

	server = "www.bing.com"
	step = 50
	counter = 0
	results = ""
	vhosts = []

	while counter <= limit:
		try:
			url = "https://" + server + "/search?q=ip%3A" + value + "&go=&count=" + str(step) + "&FORM=QBHL&qs=n&first=" + str(counter)
		 	r = requests.get(url, headers={'User-Agent': useragent})
		 	results += r.content
		except Exception,e:
			print e

		time.sleep(1)
		counter += step

	all_hostnames = GetHostnamesAll(results)

	for x in all_hostnames:
		x = re.sub(r'[[\<\/?]*[\w]*>]*','',x)
		x = re.sub('<','',x)
		x = re.sub('>','',x)
		vhosts.append(x)

	return sorted(set(vhosts))

#######################################################

## Main Function ##

def MainFunc():
	print message
	info = {}
	all_emails = []
	all_hosts = []
	limit = 500

	parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
	parser.add_argument("-d", '--domain', action="store", metavar='DOMAIN', dest='domain',
                        default=None, type=CheckDomain, help="Domain to search.", required=True)
	parser.add_argument("-s", '--server', action="store", metavar='NAMESERVER', dest='dnsserver',
                        default='8.8.8.8', type=CheckDomainOrIP, help="DNS server to use.")
	parser.add_argument('-u', '--user-agent', action="store", metavar='USER-AGENT', dest='uagent',
                        default='GasMasK {}'.format(__version__), type=str, help="User Agent string to use.")
    #parser.add_argument('-o', '--output', action='store', metavar='BASENAME', dest='basename',
    #                    type=str, default=None, help='Output in the four major formats at once.')

	if len(sys.argv) is 1:
		parser.print_help()
		sys.exit()

	args = parser.parse_args()
	info['domain'] = args.domain

#######################################################

## information ##

	dnsserver = args.dnsserver
	print "[+] Using DNS server: " + dnsserver

	uagent = args.uagent
	print "[+] Using User Agent string: " + uagent
	print

#######################################################

## target ##

	print "[+] Target:"
	print "-----------"
	info['ip'] = VerifyHostname(info['domain'])
	print info['domain'] + ":" + info['ip'] + "\n"

#######################################################

## Whois query ##

	print "[+] Whois lookup:"
	print "-----------------"
	info['whois'] = WhoisQuery(info['domain'])
	for key,value in info['whois'].iteritems():
		if isinstance(value[0], list):
			print
			print value[1]
			for val in value[0]:
				print val
			print
		else:
			print value[1] + " " + value[0]
	print

#######################################################

## DNS records ##

	print "[+] DNS queries:"
	print "----------------"
	info['dns'] = DnsQuery(info['domain'], dnsserver)
	for key,value in info['dns'].iteritems():
		if(len(value) == 1):
			print key + " DNS record: " + value[0]
		else:
			print
			print key + " DNS record: "
			for val in value:
				print val
			print
	print

#######################################################

## IP Reverse DNS lookup ##

	print "[+] Reverse DNS Lookup:"
	print "-----------------------"
	info['revdns'] = ReverseIPQuery(info['ip'], dnsserver)
	if info['revdns']:
		print info['ip'] + ":" + info['revdns']
	print

#######################################################

## Bing Virtual Hosts search results ##

	print "[+] Bing Virtual Hosts:"
	print "-----------------------"
	info['bingvhosts'] = BingVHostsSearch(info['ip'], uagent, limit)
	print
	for host in info['bingvhosts']:
		print host
	print

#######################################################

## Google search results ##

	print "[+] Searching in Google.."
	info['googleemails'], info['googlehostnames'] = GoogleSearch(info['domain'], uagent, limit)
	all_emails.extend(info['googleemails'])
	all_hosts.extend(info['googlehostnames'])

#######################################################

## Bing search results ##

	print "[+] Searching in Bing.."
	info['bingemails'], info['binghostnames'] = BingSearch(info['domain'], uagent, limit)
	all_emails.extend(info['bingemails'])
	all_hosts.extend(info['binghostnames'])

#######################################################

## Yahoo search results ##

	print "[+] Searching in Yahoo.."
	info['yahooemails'], info['yahoohostnames'] = YahooSearch(info['domain'], uagent, limit)
	all_emails.extend(info['yahooemails'])
	all_hosts.extend(info['yahoohostnames'])

#######################################################

## ASK search results ##

	print "[+] Searching in ASK.."
	info['askemails'], info['askhostnames'] = AskSearch(info['domain'], uagent)
	all_emails.extend(info['askemails'])
	all_hosts.extend(info['askhostnames'])

#######################################################

## Dogpile search results ##

	print "[+] Searching in Dogpile.."
	info['dogpileemails'], info['dogpilehostnames'] = DogpileSearch(info['domain'], uagent, limit)
	all_emails.extend(info['dogpileemails'])
	all_hosts.extend(info['dogpilehostnames'])

#######################################################

## Yandex search results ##

	print "[+] Searching in Yandex.."
	info['yandexemails'], info['yandexhostnames'] = YandexSearch(info['domain'], uagent, limit)
	all_emails.extend(info['yandexemails'])
	all_hosts.extend(info['yandexhostnames'])

#######################################################

## Search Results Final Report ##

	print
	print "[+] Search engines Results - Final Report:"
	print "------------------------------------------"
	all_emails = sorted(set(all_emails))
	all_hosts = sorted(set(all_hosts))
	print
	print "Emails:"
	for email in all_emails:
		print email
	print
	print "Hostnames:"
	for host in all_hosts:
		print host
	print

#######################################################

if __name__ == '__main__':

	try:
		MainFunc()
	except KeyboardInterrupt:
		print "Search interrupted by user.."
	except:
		sys.exit()

#######################################################
