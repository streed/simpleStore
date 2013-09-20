import json
import random
import requests
import time
import uuid
from flask import Flask, request, jsonify, url_for, g
from functools import wraps
from threading import Thread

app = Flask( __name__ )
app.hosts = []

def decoder( js ):
	d = json.loads( js )
	return d["value"]

def encoder( v ):
	return json.dumps( { "value": v } )

app.encoder = encoder
app.decoder = decoder

app.master = None
app.parent = None
app.left = None
app.right = None

packets = {}
data = {}

@app.before_first_request
def insert_into_network():
	if app.master:
		host = app.master
		result = None
		while  result != "":
			result = make_request( host, "add", "", request.host, request.host, request.host, args={ "them": request.host } )

			txt = result.text

			app.logger.debug( txt )

			if txt != "":
				result = result.json()

				host = result["value"][0].decode( "utf-8" )
			else:
				result = txt
				app.parent = host


def async( f ):
	@wraps( f )
	def wrapper( *args, **kwargs ):
		thread = Thread( target=f, args=args, kwargs=kwargs )
		thread.start()
	
	return wrapper

def get( h, host_str, headers={} ):

	try:
		return requests.get( host_str, headers=headers, timeout=5 )
	except requests.exceptions.ConnectionError:
		app.logger.debug( "Host %s is down." % h )
		pass

def make_request( h, action, key, origin, host, last, args={} ):
	args_str = "&".join( [ "%s=%s" % ( k, v ) for k, v in args.iteritems() ] )

	headers = { "Propagate": True, "OriginHost": origin, "LastHost": host }

	if origin == host:
		headers["Packet"] = str( uuid.uuid4() )
		packets[headers["Packet"]] = ( True, int( time.time() ), last )

		headers["Timestamp"] = packets[headers["Packet"]][1]

	host_str = "http://%s/" % h
	host_str += action
	if key != "":
		host_str += "/%s" % key
	if args_str != "":
		host_str += "?%s" % args_str

	if h != host:
		return get( h, host_str, headers=headers )

@async
def distribute_set( args, origin, host, packet, last ):
	if packet in packets:
		return
	for h in [ app.left, app.right, app.parent ]:
		if h != None:
			make_request( h, "set", "", origin, host, last, args=args )

@async
def distribute_del( key, origin, host, packet, last ):
	if packet in packets:
		return
	for h in [ app.left, app.right, app.parent ]:
		if h != None:
			make_request( h, "del", key )

@async
def distribute_get( key, origin, host, packet, last ):
	for h in [ app.left, app.right, app.parent ]:
		if h != None:
			result = make_request( h, "get", key, origin, host, last )
			if result and result.text != "":
				data[key] = app.decoder( result.text )
				make_request( last, "fwd", "", origin, host, last, args={ "key": key, "value": data[key], "packet": packet } )
				break

@app.route( "/dump" )
def dump():
	return app.encoder( [ data, packets, { "left": app.left, "right": app.right, "parent": app.parent } ] )

@app.route( "/set" )
def set_key():

	changes = {}

	for k, v in request.args.iteritems():
		if k not in data:
			changes[k] = v
			data[k] = v
		else:
			if v != data[k]:
				changes[k] = v
				data[k] = v

	if changes != {}:
		if not "Propagate" in request.headers: 
			distribute_set( changes, request.host, request.host, "", "" )
		else:
			origin = request.headers.get( "OriginHost" )
			packet = request.headers.get( "Packet" )
			last = request.headers.get( "LastHost" )
			timestamp = request.headers.get( "Timestamp" )

			distribute_set( changes, origin, request.host, packet, last )

	return ""


@app.route( "/get/<key>" )
def get_key( key ):

	if key in data:
		return app.encoder( data[key] )
	else:
		if not "Propagate" in request.headers: 
			distribute_get( key, request.host, request.host, "", "" )
		else:
			origin = request.headers.get( "OriginHost" )
			packet = request.headers.get( "Packet" )
			last = request.headers.get( "LastHost" )
			timestamp = request.headers.get( "Timestamp" )

			if not packet in packets:
				packets[packet] = ( True, timestamp, last )
				distribute_get( key, origin, request.host, packet, last )
		return "TryAgain"

	return ""

@app.route( "/del/<key>" )
def del_key( key ):
	if key in data:
		del data[key]

		if not "Propagate" in request.headers: 
			distribute_del( key, request.host, request.host, "", "" )
		else:
			origin = request.headers.get( "OriginHost" )
			packet = request.headers.get( "Packet" )
			last = request.headers.get( "LastHost" )
			timestamp = request.headers.get( "Timestamp" )

			distribute_del( key, origin, request.host, packet, last )

	return ""

@app.route( "/fwd" )
def fwd_key():
	packet = request.args.get( "packet" )
	key = request.args.get( "key" )
	value = request.args.get( "value" )

	if packet in packets:
		last = packets[packet][2]

		del packets[packet]

		data[key] = value
		if last != "":
			make_request( last, "fwd", "", request.host, "", { "key": key, "value": value, "packet": packet } )

	return ""

@app.route( "/add" )
def add_node():
	them = request.args.get( "them" )

	if app.left == None and app.right != them:
		app.left = them
	elif app.right == None and app.left != them:
		app.right = them
	else:
		if all( [ them != i for i in [ app.left, app.right ] ] ):
			recurse = random.choice( [ app.left, app.right ] )
			return app.encoder( [ recurse ] )
	return ""
