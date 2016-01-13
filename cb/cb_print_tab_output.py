#!/usr/bin/python

# We need HTTP, JSON, CSV files, plus common utility functions.
import requests, json, csv, argparse, sys


# Python requires definition of main.
def main(argv):


  #Get command-line arguments.
  parser = argparse.ArgumentParser(description='Print tab-delimited output from certain Carbon Black REST nodes, based on a specified query and specified field set.')
  arggroup = parser.add_mutually_exclusive_group(required=True)
  parser.add_argument( "-s", "--servername", help="Hostname of Carbon Black server.", required=True )
  parser.add_argument( "-t", "--apitoken", help="API token for authentication.", required=True )
  parser.add_argument( "-q", "--query", help="Supported query syntax for specified node.", required=True )
  arggroup.add_argument( "-f", "--fields", help="Fields to print from 'results' objects." )
  parser.add_argument( "-n", "--node", help="Node to query, namely /binary, /alert, /sensor, or /process", required=True, choices=["binary","alert","sensor","process"])
  parser.add_argument( "-p", "--pagerows", help="How many rows to process in each loop (paging).", default=25000)
  parser.add_argument( "-r", "--maxrows", help="Maximum number of output rows to return.", default=2000000)
  parser.add_argument( "-o", "--sortorder", help="Whether to sort ascending or descending.", default="desc", choices=["asc","desc"])
  parser.add_argument( "-u", "--sortfield", help="What field on which to sort results.")
  parser.add_argument( "-z", "--sslverify", help="Whether or not to verify SSL connection.", action="store_true")
  arggroup.add_argument( "-a", "--allfields", help="Print all fields instead of selected list.", action="store_true") 

  myargs = parser.parse_args()

  # Set up some useful constants. 
  pagerows = myargs.pagerows
  if myargs.fields is not None: fields = myargs.fields.split(",")
  if myargs.sortfield is not None:
    sortkey = { myargs.node:myargs.sortfield }
  else:
    sortkey = { "process":"last_update", "binary":"md5", "sensor":"id", "alert":"created_time" }
  gh = {'X-Auth-Token': myargs.apitoken } # header for GET
  du = 'https://' + myargs.servername + '/api/v1/' # supported API URL
  if myargs.sslverify: ssl = True 
  else: ssl = False


  # Grab a session and set some counters.
  s = requests.Session()
  nextrow = 0
  totrows = 1
 
  # Print the header row.

  # While we are at less rows than total in result...
  while nextrow < totrows and nextrow < myargs.maxrows:
    # Get the results
    url = du \
      + myargs.node \
      + "?q=" + myargs.query \
      + "&rows=" + str(pagerows) \
      + "&sort=" + sortkey[myargs.node] + "+" + myargs.sortorder \
      + "&start=" + str(nextrow)
    r = s.get( url, headers=gh, verify=ssl, timeout=30 )
    j = r.json()
    # Print a header row if necessary.
    if nextrow == 0 and myargs.allfields:
      print '\t'.join( "%s" % (k) for k in j['results'][0].keys() )
    elif nextrow == 0:
      print '\t'.join( "%s" % (k) for k in fields )
    # Increase the counters
    totrows = j["total_results"]
    nextrow = nextrow + pagerows
    # Print the rows
    if j["total_results"] > 0:
      for result in j["results"]:
        if myargs.allfields:
          print '\t'.join( "%s" % (result[k]) for k in result.keys() ).encode("utf-8")
        else:
          print '\t'.join( "%s" % (result[k]) for k in fields ).encode("utf-8")

# How to make a python script actually run.
if __name__ == "__main__":
   main(sys.argv[1:])

