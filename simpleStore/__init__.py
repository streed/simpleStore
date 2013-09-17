import requests
from flask import Flask, request, jsonify, url_for, g
from functools import wraps
from threading import Thread

app = Flask( __name__ )
app.hosts = []

data = {}

def async( f ):
	@wraps( f )
	def wrapper( *args, **kwargs ):
		thread = Thread( target=f, args=args, kwargs=kwargs )
		thread.start()
	
	return wrapper

@async
def distribute_set( args, origin, host ):
	set_str = "&".join( [ "%s=%s" % ( k, v ) for k, v in args.iteritems() ] )
	headers = { "Propagate": True, "OriginHost": host }
	for h in app.hosts:
		if h != origin:
			host_str = "http://%s/set?%s" % ( h, set_str )

			app.logger.debug( "Propagating to %s" % host_str )

			requests.get( host_str, headers=headers )

@async
def send_pings( me ):
	for h in app.hosts:
		host_str = "http://%s/ping?me=%s" % ( h, me )
		result = requests.get( host_str )
		
		if not result.text in app.hosts:
			app.logger.debug( "New host: %s" % result.text )
			app.hosts.append( result.text )

@app.before_first_request
def send_the_pings():
	send_pings( request.host )

@app.route( "/ping" )
def ping():
	host = request.args["me"]

	if not host in app.hosts:
		app.hosts.append( host )

	return request.host

@app.route( "/set" )
def set_value():

	for k, v in request.args.iteritems():
		app.logger.debug( "Setting %s => %s" % ( k, v ) )
		data[k] = v

	app.logger.debug( "Should we propagate the set value?" )
	if not "Propagate" in request.headers: 
		app.logger.debug( "No `Propagate` in headers so let's start the propagation." )
		distribute_set( request.args, "", request.host )
	else:
		app.logger.debug( "There was a `Propagate` in the headers so there must be a `OriginHost` as well so lets grab it and then start propagating." )
		origin = request.headers.get( "OriginHost" )
		distribute_set( request.args, origin, request.host )


	return "OK"


@app.route( "/get/<value>" )
def get_value( value ):

	if value in data:
		return jsonify( **{ value: data[value] } )

	return ""

@app.route( "/delete/<value>" )
def delete_value( value ):
	del data[value]

	return "OK"
