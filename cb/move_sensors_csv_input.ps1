#Get command-line parameters
Param(
	[parameter(Mandatory=$true, HelpMessage="API token for authenticaton.")][alias("t")][string]$apiToken,
	[parameter(Mandatory=$true, HelpMessage="Name of Carbon Black server.")][alias("s")][string]$serverName,
	[parameter(Mandatory=$true, HelpMessage="Path and name to CSV file.")][alias("f")][string]$csvFile,
	[parameter(Mandatory=$false, HelpMessage="Set to true or false to verify SSL.")][alias("z")][switch]$sslVerify,
	[parameter(Mandatory=$false, HelpMessage="Print verbose logging to STDOUT.")][alias("l")][switch]$logging
)

# Set up some useful constants constants
$t = $apiToken
$s = $serverName
$h = "X-Auth-Token"
$u = "https://$s/api/v1"
$v = "https://$s/api"

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

# Get the list of groups first.
$groups = @{}

try {
	$groupreqs = Invoke-RestMethod -Headers @{$h=$t} -Method Get -Uri "$v/group"
	If ( $logging ) { Write-Output "Get groups result: 200" }
} catch {
	If ( $logging ) { Write-Output ( "Get groups result: " + $_.Exception.Response.StatusCode ) }
}

If ( $logging ) { Write-Output "Get groups result: 200" }
If ( $logging ) { Write-Output "===BEGIN GROUPS===" }
foreach ( $groupreq in $groupreqs ) {
	$groups.Add( $groupreq.name, $groupreq.id )
}
If ( $logging ) { Write-Output "===END GROUPS===" }

#Import the CSV file.
$records = Import-Csv $csvFile

foreach ( $record in $records) {

	$groupid = $groups.Get_Item($record.group)
	$hostname = $record.computer

	# Get the computer(s) with matching name.
	try {
		$computers = Invoke-RestMethod -Headers @{$h=$t} -Method Get -Uri "$u/sensor?hostname=$hostname"
		If ( $logging ) { Write-Output ( "Get sensor " + $hostname + " result: 200" ) }
	} catch {
		If ( $logging ) { Write-Output ( "Get sensor " + $hostname + " result: " + $_.Exception.Response.StatusCode ) }
	}

	foreach ( $computer in $computers ) {

		$sensor_id = $computer.id
		$computer.group_id = $groupid

		$json = $computer | ConvertTo-Json

		# Move to the new group.
		try {
			Invoke-RestMethod -Headers @{$h=$t} -Method Put -ContentType "application/json" -Uri "$u/sensor/$sensor_id" -Body $json
			If ( $logging ) { Write-Output ( "Set sensor " + $computer.computer_name + ":" + $computer.id + " to " + $record.group + " result: 200" ) }
		} catch {
			If ( $logging ) { Write-Output ( "Set sensor " + $computer.computer_name + ":" + $computer.id + " to " + $record.group + " result: " + $_.Exception.Response.StatusCode ) }
		}
		
	}

}