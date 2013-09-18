simpleStore
===========

Simple key-value store using gossiping to ensure eventual-consistency.

The system is incredibly simplistic and was insipired by a node.js talk. I wanted to implement something similar and here is what came of that.

The store is run as such:

    run.py <port> [host:port host:port host:port]

The above will start the local server on the port specified. If there is a list of hosts it will use those when doing any operation that requires
propagation. 

Everything is a simple get request at the moment, but it's not hard to change to a post or put.

So, to set a value/s the following request will suffice.

    curl http://127.0.0.1:8000/set?test=lol&msg=this_is_a_message

This will store two keys into the system `test` and `msg`. If there is more than one node attached to this node then the entries are propagated,
so for example say there is another node running on port 8001, the following request can be performed.

    curl http://127.0.0.1:8001/get/test

    { "value": "lol" }

And the above output will be printed. As can be seen the data has propagated to the other nodes. Now, if the connection between them is bi-directional, or in
other words the second node also lists the first node as a connectable node (as done via the command line arguments) then the following will also work.

    curl http://127.0.0.1:8001/set?msg=new_message
    curl http://127.0.0.1:8000/get/msg

    { "value": "new_message" }

As can be seen the output from the port 8000 node will print out the changed data because the information has been propagated correctly between the news.

Now, let's say the following is run.

    A: run.py 8000 B:8001
    B: run.py 8001 C:8002 D:8003
    C: run.py 8002
    D: run.py 8003 A:8000

    curl http://A:8000/set?msg=hello world

What happens here is that the key `msg` is created on A then this is then propagated to the other nodes first going to B which then sends the propagation to
C and D. When it gets to D there is found to be a cycle in the node graph, but there is a `OriginHost` in the headers that will be used to prevent a 
infinite propagation through the node graph. But the following query will work perfectly fine.

    curl http://D:8003/get/msg

    { "value": "hello world" }


Now if a key is set on D it will follow the same pattern and eventually get to all of the nodes by the propagation method as long as there exists a path between the nodes.

Now, given the next setup with a single node.

    A: run.py 8000 B:8001
    
The above is simply a single node with the ability to eventually use another node running on port 8001 on host B. So, a key is added to the system.

    curl http://A:8000/set?msg=hello world
    
Now the descision that the cluster, the single node, just can't handle the current load so the descision is made to add two more
nodes to the cluster.

    B: run.py 8001 A:8000 C:8002
    C: run.py 8002 B:8001
    
So, there are the extra nodes. Now a request comes into node C.

    curl http://B:8002/get/msg
    
But, at this point the key `msg` does not exist on the node C so it sets out to discover the value. It goes to its neighbor B, but since this node was just added it must also discover the value so it goes to it's neighbor A. 
From this point the key exists and the value `hello world` is returned to B. B now fowards this value back to C as well as stores it locally. C receives the forward
and then inserts it into its store. Now the client can easily retreive the value again and get the new value.
