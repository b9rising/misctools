#!/usr/bin/python

import requests, json, argparse, sys, csv, random, hashlib, time

def main(argv):

  # Get command-line arguments.
  parser = argparse.ArgumentParser(description='Simple template on which to build API scripts.')
  parser.add_argument( "-s", "--servername", help="DNS hostname of Carbon Black server.", required=True )
  parser.add_argument( "-t", "--apitoken", help="Token for authentication to API.", required=True )
  parser.add_argument( "-z", "--sslverify", help="Verify SSL connection to server.", action="store_true" )
  parser.add_argument( "-y", "--timeout", help="Timeout on getting stuff back from CB Server.", default=90 )
  parser.add_argument( "-v", "--verbose", help="Print some logging/debugging to STDOUT.", action="store_true" )
  # Add more custom args here.
  nothis = parser.add_mutually_exclusive_group()
  nothat = parser.add_mutually_exclusive_group()
  parser.add_argument( "-f", "--fields", help="Fields to include in the output.", \
                         default="sensor_id process_name path cmdline os_type hostname parent_name group" )
  parser.add_argument( "-d", "--dayshist", help="How may days back in time to gather records.", default=10 )
  parser.add_argument( "-w", "--watchlists", help="File of proposed watchlists, one per line.", required=True )
  parser.add_argument( "--maxpagerows", help="How many results rows to process in each loop (paging).", default=25000)
  parser.add_argument( "--maxoutrows", help="Maximum number of output rows to return.", default=2000000)
  parser.add_argument( "--maxlistrows", help="Maximum number of rows to collect per list.", default=100000)
  parser.add_argument( "--maxaggrows", help="How many rows to hold in aggregtor before flushing.", default=200000)
  parser.add_argument( "--dialect", help="What file format to use for the input file.", default="excel-tab")
  nothis.add_argument( "--nohosts", help="Never include hostnames in the output.", action="store_true" )
  nothis.add_argument( "--nosids", help="Never include sensor ID's in the output.", action="store_true" )
  nothat.add_argument( "--nosensors", help="Remove sensor refs, get only summary counts.", action="store_true" )
  parser.add_argument( "--anonhosts", help="Anonymize hostnames with cryptorand plus MD5.", action="store_true" )
  parser.add_argument( "--anonsids", help="Anonymize sensor ID's with cryptorand plus MD5.", action="store_true" )
  parser.add_argument( "--timeclick", help="How much of time fields to preserve.", default="day", \
                         choices=["day","month","hour","minute"] )

  myargs = parser.parse_args()
  
  # Start a CB API client session.  Class def is down toward bottom.
  cb = cbclient( myargs.servername, myargs.apitoken, myargs.sslverify, int(myargs.timeout) )

  # === BEGIN CODE ===
  
  # Set up all our working defaults, counters, containers, etc.
  timeclicks = { "day":10, "month":7, "hour":13, "minute":16 } # help truncate/round timestamps
  timepads = { "day":" 00:00:00", "month":"01 00:00:00", "hour":":00:00", "minute":":00" } # help truncate/round timestamps
  aggregate = {}
  total_printed = 0
  myhours = myargs.dayshist * 24 # convert hours to days for query format
  myfields = myargs.fields.split(" ")
  if myargs.nohosts and "hostname" in myfields: myfields.remove('hostname')
  if myargs.nosids and "sensor_id" in myfields: myfields.remove('sensor_id')
  if myargs.nosensors:
    if "hostname" in myfields: myfields.remove('hostname')
    if "sendor_id" in myfields: myfields.remove('sensor_id')
  if myargs.anonhosts: anonhosts = anonimizer() # class is at the bottom, uses crypto rand plus hash
  if myargs.anonsids: anonsids = anonimizer() # class is at the bottom, uses crypto rand plus hash

  # Print a header row.
  print "watchlist\t" + '\t'.join( "%s" % (k) for k in myfields ) + "\tcount"  

  # Get queries from file.
  with open(myargs.watchlists) as csvfile:
    reader = csv.DictReader(csvfile, dialect=myargs.dialect)
    # Get some processes for each query.
    for row in reader:
      if total_printed < myargs.maxoutrows: # whack math to chunk results processing
        nextrow = 0 # whack math to chunk results processing  
        totrows = 1 # whack math to chunk 
        while nextrow < totrows and nextrow < myargs.maxlistrows: # whack math to chunk
          # add dayshist to query plus whack math to chunk results processing
          query ="/process" + \
                    "?q=" + row["watchlist"] + ")+AND+(start:-" + str(myhours) + "h)" + \
                    "&start=" + str(nextrow) + \
                    "&rows=" + str(myargs.maxpagerows)
          processes, success, errcode, errmsg = cb.get( query, chatty=True )
          if success:
            for process in processes["results"]:
              if myargs.anonhosts: process["hostname"] = anonhosts.giveme(process["hostname"]) # anonimize hostnames if...
              if myargs.anonsids: process["sensor_id"] = anonhosts.giveme(str(process["sensor_id"]))  # anonimize sensor id's if...
              # truncate/round time for aggregation but pad to std format.
              for timestamp in [ "start", "last_update" ]:
                mystr = str(process[timestamp])
                process[timestamp] = mystr.replace("T"," ")[:timeclicks[myargs.timeclick]] + timepads[myargs.timeclick]
              # Building and printing rows...
              mystr = row["watchlist"] + "\t" +  '\t'.join( "%s" % (process[k]) for k in myfields )
              if total_printed < myargs.maxoutrows:
                total_printed += 1
                aggregate[mystr.encode("utf-8")] = +1
                if len(aggregate) >= myargs.maxaggrows: # whack math
                  for row in aggregate.keys():
                    print row + "\t" + str(aggregate[row])
                  aggregate.clear()
            totrows = processes["total_results"] # whack math
            nextrow = nextrow + myargs.maxpagerows # whack math
          # And if the request chokes...
          else:
            totrows = 0
            print >> sys.stderr, "ERROR: Code=" + str(errcode) + \
                "||Message: " + errmsg + \
                "||Watchlist: " + row["watchlist"] + \
                "||URI: " + query
  for row in aggregate.keys():
    print row + "\t" + str(aggregate[row])


  # === END CODE ===


# Do not change below this line.
# === BEGIN CB CLIENT ===
# Defining the "CB Client" itself.
class cbclient(object):

  # Initialize the object.
  def __init__( self, server, token, ssl, timeout ):
  # Set up some useful constants constants, to save us time later.
    self.gh = {'X-Auth-Token': token } # header for GET
    self.ph = {'X-Auth-Token': token, 'Content-Type': 'application/json' } # header for PUT or POST, need content type added
    self.du = 'https://' + server + '/api/v1' # supported API URL
    self.hu = 'https://' + server + '/api' # hidden API URL
    self.ssl = ssl
    self.ko = timeout
    self.s = requests.Session()

  # GET data from the API
  def get( self, url, **kwargs ):
    if kwargs.pop("hidden", None): uri = self.hu + url
    else: uri = self.du + url
    try:
      r = self.s.get( uri, headers=self.gh, verify=self.ssl, timeout=self.ko )
      r.raise_for_status()
      j = r.json()
      code = r.status_code
      msg = str(r)
      success = True
    except requests.HTTPError as e:
      j = json.dumps([])
      code = r.status_code
      msg = "HTTPERR" + str(e)
      success = False
    except Exception as e:
      j = json.dumps([])
      code = 0
      msg = "UNKERR" + str(e)
      success = False
    if kwargs.pop("chatty", None): return j, success, code, msg
    else: return j

  # PUT some changes up to the API
  def put( self, url, js, **kwargs ):
    if kwargs.pop("hidden", None): uri = self.hu + url
    else: uri = self.du + url
    try:
      r = self.s.put( uri, data=json.dumps(js), headers=self.gh, verify=self.ssl, timeout=self.ko )
      r.raise_for_status()
      code = r.status_code
      msg = str(r)
      success = True
    except requests.HTTPError as e:
      code = r.status_code
      msg = str(e)
      success = False
    except Exception as e:
      code = 0
      msg = str(e)
      success = False
    if kwargs.pop("chatty", None): return success, code, msg
    else: return success

  # POST some changes up to the API
  def post( self, url, js, **kwargs ):
    if kwargs.pop("hidden", None): uri = self.hu + url
    else: uri = self.du + url
    try:
      r = self.s.post( uri, data=json.dumps(js), headers=self.gh, verify=self.ssl, timeout=self.ko )
      r.raise_for_status()
      code = r.status_code
      msg = str(r)
      success = True
    except requests.HTTPError as e:
      code = r.status_code
      msg = str(e)
      success = False
    except Exception as e:
      code = 0
      msg = str(e)
      success = False
    if kwargs.pop("chatty", None): return success, code, msg
    else: return success


# === END CB CLIENT ===

class anonimizer(object):

  def __init__( self ):
    self.rng = random.SystemRandom()
    self.items = {}

  def giveme( self, item ):
    if item in self.items:
      return self.items[item]
    else:
      m = hashlib.md5()
      m.update(item)
      m.update(str(self.rng.random()))
      self.items[item] = m.hexdigest()
      return self.items[item]

# How to make a python script actually run.
if __name__ == "__main__":
   main(sys.argv[1:])


