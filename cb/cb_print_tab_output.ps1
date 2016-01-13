#Get command-line parameters
Param(
	[parameter(Mandatory=$true, HelpMessage="API token for authenticaton.")][alias("t")][string]$apiToken,
	[parameter(Mandatory=$true, HelpMessage="Name of Carbon Black server.")][alias("s")][string]$serverName,
	[parameter(Mandatory=$false, HelpMessage="Set to true or false to verify SSL.")][alias("z")][switch]$sslVerify,
	[parameter(Mandatory=$true, HelpMessage="Supported query syntax for specified node.")][alias("q")][string]$query,
	[parameter(Mandatory=$true, ParameterSetName="some_fields", HelpMessage="Fields to print from 'results' objects.")][alias("f")][string]$fields,
	[parameter(Mandatory=$true, HelpMessage="Node to query, namely /binary, /alert, /sensor, or /process")][alias("n")][ValidateSet("binary","alert","sensor","process")][string]$node,
	[parameter(Mandatory=$false, HelpMessage="How many rows to process in each loop (paging).")][alias("p")][int]$pagerows=25000,
	[parameter(Mandatory=$false, HelpMessage="Maximum number of output rows to return.")][alias("r")][int]$maxrows=2000000,
	[parameter(Mandatory=$false, HelpMessage="Whether to sort ascending or descending.")][alias("o")][ValidateSet("asc","desc")][string]$sortorder="desc",
	[parameter(Mandatory=$false, HelpMessage="What field on which to sort results.")][alias("u")][string]$sortfield="desc",
	[parameter(Mandatory=$true, ParameterSetName="all_fields", HelpMessage="Print all possible fields instead of specified")][alias("a")][switch]$allfields
)

# Set up some useful constants constants
$t = $apiToken
$s = $serverName
$h = "X-Auth-Token"
$u = "https://$s/api/v1/"

if ( $sortfield.IsPresent ) {
	$sortkey = @{ $node = $sortfield }
} else {
	$sortkey = @{ process="last_update"; binary="md5"; sensor="id"; alert="created_time" }
}

$myfields = $fields.Split("{,}")

#Some crazy stuff to ignore SSL certificate validation.
add-type @"
    using System.Net;
    using System.Security.Cryptography.X509Certificates;
    public class TrustAllCertsPolicy : ICertificatePolicy {
        public bool CheckValidationResult(
            ServicePoint srvPoint, X509Certificate certificate,
            WebRequest request, int certificateProblem) {
            return true;
        }
    }
"@
if ( $sslVerify ) {
	[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
}


# Set some counters.

$nextrow = 0
$totrows = 1


# While we are at less rows than total in result...
while ( $nextrow -lt $totrows -and $nextrow -lt $maxrows ) {
	# Get the next set of results.
	$url = $u `
      + $node `
      + "?q=" + $query `
      + "&rows=" + $pagerows `
      + "&sort=" + $sortkey[$node] + "+" + $sortorder `
      + "&start=" + $nextrow
	$json = Invoke-RestMethod -Headers @{$h=$t} -Method Get -Uri $url
	# Print header row if necessary.
	if ( $nextrow -lt 1 -and $allfields ) {
		$objects = $json.results[0] | Get-Member -MemberType Properties
		$myfields = $objects.Name
	}
	if ( $nextrow -lt 1 ) {
		Write-Output ( $myfields -join "`t" )
	}
	# Increase the counters.
	$totrows = $json.total_results
    $nextrow = $nextrow + $pagerows
    # Print the rows
    if ( $json.total_results -gt 0 ) {
		foreach ( $result in $json.results ) {
			Write-Output ((($myfields) | % { $result."$_" }) -join "`t")	
		}
	}
}