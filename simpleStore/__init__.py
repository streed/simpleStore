import json
import requests
from flask import Flask, request, jsonify, url_for, g
from functools import wraps
from threading import Thread

app = Flask( __name__ )
app.hosts = []

def decoder( js ):
	d = json.loads( js )
	return d["value"]

def encoder( v ):
	print v
	return json.dumps( { "value": v } )

app.encoder = encoder
app.decoder = decoder


data = {}

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
		app.logger.debug( "Removing %s from the hosts list, because it appears to be down." % ( h ) )
		index = app.hosts.index( h )
		del app.hosts[index]
		raise

@async
def distribute_set( args, origin, host ):
	set_str = "&".join( [ "%s=%s" % ( k, v ) for k, v in args.iteritems() ] )
	headers = { "Propagate": True, "OriginHost": origin, "LastHost": host }
	hosts = app.hosts[:]
	for h in hosts:

		if h != origin and h != host:
			host_str = "http://%s/set?%s" % ( h, set_str )

			app.logger.debug( "Propagating set to %s" % host_str )

			get( h, host_str, headers=headers )

@async
def distribute_del( key, origin, host ):
	headers = { "Propagate": True, "OriginHost": origin, "LastHost": host }
	hosts = app.hosts[:]
	for h in hosts:
		if h != origin and h != host:
			host_str = "http://%s/del/%s" % ( h, key )

			app.logger.debug( "Propagating delete to %s" % host_str )

			get( h, host_str, headers=headers )

@async
def distribute_get( key, origin, host ):

	headers = { "Propagate": True, "OriginHost": origin, "LastHost": host }
	
	hosts = app.hosts[:]
	for h in hosts:
		app.logger.debug( "origin %s" % origin )
		if h != origin and h != host:
			host_str = "http://%s/get/%s" % ( h, key )

			result = get( h, host_str, headers=headers )

			if not result.text == "":
				data[key] = app.decoder( result.text )
				break

@async
def send_pings( me ):
	hosts = app.hosts[:]
	for h in hosts:
		host_str = "http://%s/ping?me=%s" % ( h, me )
		result = get( h, host_str )
		
		if not result.text in app.hosts:
			app.logger.debug( "New host: %s" % result.text )
			app.hosts.append( result.text )

#@app.before_first_request
def send_the_pings():
	send_pings( request.host )

@app.route( "/ping" )
def ping():
	host = request.args["me"]

	if not host in app.hosts:
		app.hosts.append( host )

	return request.host

@app.route( "/dump" )
def dump():
	return app.encoder( data )

@app.route( "/set" )
def set_key():

	changes = {}

	for k, v in request.args.iteritems():
		app.logger.debug( "Setting %s => %s" % ( k, v ) )
		if k not in data:
			changes[k] = v
			data[k] = v
		else:
			if v != data[k]:
				changes[k] = v
				data[k] = v


	if changes != {}:
		app.logger.debug( "Should we propagate the set value?" )
		if not "Propagate" in request.headers: 
			app.logger.debug( "No `Propagate` in headers so let's start the propagation." )
			distribute_set( changes, request.host, request.host )
		else:
			app.logger.debug( "There was a `Propagate` in the headers so there must be a `OriginHost` as well so lets grab it and then start propagating." )
			origin = request.headers.get( "OriginHost" )
			distribute_set( changes, origin, request.host )

	return ""


@app.route( "/get/<key>" )
def get_key( key ):

	app.logger.debug( "Trying to get the value for %s" % key )
	if key in data:
		return app.encoder( data[key] )
	else:
		app.logger.debug( "The key did not exist so lets try and grab it from the other nodes." )
		app.logger.debug( "Shold we propagate the set value?" )
		if not "Propagate" in request.headers: 
			app.logger.debug( "No `Propagate` in headers so let's start the propagation." )
			distribute_get( key, request.host, request.host )
		else:
			app.logger.debug( "There was a `Propagate` in the headers so there must be a `OriginHost` as well so lets grab it and then start propagating." )
			origin = request.headers.get( "OriginHost" )
			distribute_get( key, origin, request.host )

	return ""

@app.route( "/del/<key>" )
def del_key( key ):
	if key in data:
		del data[key]

		app.logger.debug( "Should we propagate the del value?" )
		if not "Propagate" in request.headers: 
			app.logger.debug( "No `Propagate` in headers so let's start the propagation." )
			distribute_del( key, request.host, request.host )
		else:
			app.logger.debug( "There was a `Propagate` in the headers so there must be a `OriginHost` as well so lets grab it and then start propagating." )
			origin = request.headers.get( "OriginHost" )

			app.logger.debug( "OriginHost: %s" % origin )
			distribute_del( key, origin, request.host )

	return ""

