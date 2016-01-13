#!/usr/bin/python

# We need HTTP, JSON, CSV files, plus common utility functions.
import requests, json, csv, argparse, sys


# Python requires definition of main.
def main(argv):

  #Get command-line arguments.
  parser = argparse.ArgumentParser(description='Move sensors to different groups based on input from CSV file.')
  parser.add_argument( "-s", "--servername", help="DNS hostname of Carbon Black server.", required=True )
  parser.add_argument( "-t", "--apitoken", help="Token for authentication to API", required=True )
  parser.add_argument( "-f", "--filename", help="Name and path of CSV input file.", required=True )
  parser.add_argument( "-v", "--verbose", help="Print some logging/debugging to STDOUT.", action="store_true" )
  parser.add_argument( "-z", "--sslverify", help="Whether or not to verify SSL connection.", action="store_true")


  myargs = parser.parse_args()
  server = myargs.servername
  token = myargs.apitoken
  filename = myargs.filename
  if myargs.verbose: log = True
  if myargs.sslverify: ssl = True



  # Set up some useful constants constants
  gh = {'X-Auth-Token': token } # header for GET
  ph = {'X-Auth-Token': token, 'Content-Type': 'application/json' } # header for PUT or POST, need content type
  du = 'https://' + server + '/api/v1' # supported API URL
  hu = 'https://' + server + '/api' # hidden API URL

  # Grab a session.
  s = requests.Session()

  # Get the groups, so you can map name to ID
  url = hu + "/group"
  r = s.get( url, headers=gh, verify=ssl, timeout=30 )
  if log: print "Get groups result: " + str(r)
  if log: print "===BEGIN GROUPS==="
  j = r.json()
  groups = dict()
  for group in j:
    if log: print group["name"] + "," + str(group["id"])
    groups[group["name"]] = group["id"]
  if log: print "===END GROUPS==="

  # Open the CSV file
  with open(filename) as csvfile:
    reader = csv.DictReader(csvfile)
    # Read it one row at a time.
    for row in reader:
      # Get the sensors that match the name in the "Computer" column.
      url = du + '/sensor?hostname=' + row['Computer']
      r = s.get( url, headers=gh, verify=ssl, timeout=30 )
      if log:  print "Get sensor " + row['Computer'] + " result: " + str(r)
      sensors = r.json()
      # Go through each sensor matched by that row.
      for sensor in sensors:
        # Set the new group ID
        sensor["group_id"] = groups[row['Group']]
        # Post the change
        url = du + '/sensor/' + str( sensor['id'] )
        r = s.put( url, headers=ph, verify=False, timeout=30, data=json.dumps(sensor) )
        if log: print "Set sensor " + sensor["computer_name"] + ":" + str(sensor["id"]) + " to " + row["Group"] + ": " + str(r)

# How to make a python script actually run.
if __name__ == "__main__":
   main(sys.argv[1:])
