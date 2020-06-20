import teslajson
import json
import sys
usern = str(sys.argv[1])
passw = str(sys.argv[2])
carnumb = int(sys.argv[3])

debug = True
cachefile='../../ramdisk/soc-tesla-chargestate.json'
soc = 0

c = teslajson.Connection(usern, passw)
v = c.vehicles[carnumb]
cs = ""
state = v.state()
if (debug):
   print("DEBUG %s" % state)

if(state=="online"):
   cs = json.dumps(v.data_request('charge_state'))

print(cs)





