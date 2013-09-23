simpleStore
===========

Simple key-value store using gossiping to ensure eventual-consistency.

The system is incredibly simplistic and was insipired by a node.js talk. I wanted to implement something similar and here 
is what came of that.
 
The system involves many different nodes in a cluster. This cluster will keep a key-value database consistent between all
such that when a key-value pair is set on one node and subsuquently gotten from another node the key-value will exist
there as well.

To give an small overview of the system a small cluster needs to be made.

    A: run.py 8000
    B: run.py 8001 127.0.0.1:8000
    C: run.py 8002 127.0.0.1:8000
    
The above will build a three node cluster that will look like the following tree.

        A
       / \
      B   C
      
This tree structure is used to remove any chance of a cycle. New nodes are always added to the root and then they propagate
down to their specific location. This makes the business logic of getting and setting values very trivial. 

The following is used to set a specific value in the cluster.

    curl http://127.0.0.1:8000/set?testing=hello_world
    
After the above is executed the following query to node B will give the value back.

    curl http://127.0.0.1:8001/get/testing
    { "value": "hello_wolrd" }
    
Now, another node is added.

    D: run.py 8003 127.0.0.1:8000
    
The tree will look like something below:

        A
       / \
      B   C
     /
    D
    
Now, the following query is done.

    curl http://127.0.0.1:8003/get/testing

This will return nothing back, but if the same request is repeated it will return the value.

TODO:
* [ ] Write a futures class
* [ ] Make the method of getting/setting more efficient and try to take advantage of the tree strucutre.
