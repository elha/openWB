import teslajson
import json
import sys
usern = str(sys.argv[1])
passw = str(sys.argv[2])
carnumb = int(sys.argv[3])

debug = False

c = teslajson.Connection(usern, passw)
v = c.vehicles[carnumb]
state = v.state()
if (debug):
   print("DEBUG %s" % state)

if(state!="online"):
   v.wake_up()





