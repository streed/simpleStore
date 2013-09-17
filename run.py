import sys
from simpleStore import app

if __name__ == "__main__": 
	port = 5000
	if len( sys.argv ) >= 2:
		port = int( sys.argv[1] )

		app.hosts = sys.argv[2:]

	app.run( debug=True, port=port )
