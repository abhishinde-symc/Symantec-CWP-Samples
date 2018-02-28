#!/usr/bin/env python
#
# Copyright 2017 Symantec Corporation. All rights reserved.
#
#Script to automate deployment of Symantec Cloud Workload Protection Agent on a Virtual Machine. This script also applies a CWP Policy Group.
#This script can be used in AWS user data field during instance launch
#Refer to CWP REST API at: https://apidocs.symantec.com/home/scwp#_symantec_cloud_workload_protection
#Customer has to pass Customer ID, Domain ID, Client ID and Client Secret Key as arguments. The keys are available in CWP portal's Settings->API Key tab
#Script no longer reboots the server. This script can be used in AWS & Azure launch configs.
#Usage: python cwpagentinstall.py <Customer ID> <Domain ID> <Client Id> <Client Secret Key>"
#######################################################################################################################################################################

import platform
import os
import requests
import string
import json
import time
import sys

#Customer has to pass Customer ID, Domain ID, Client ID and Client Secret Key as arguments. The keys are available in CWP portal's Settings->API Key tab
clientsecret=''
clientID=''
customerID=''
domainID=''

#Function to call CWP REST API and download Agent package
def download_agentpkg_from_scwp_server(osdistribution):
  token = {}
  mydict = {}

  #CWP REST API endpoint URL for auth function
  url = 'https://scwp.securitycloud.symantec.com/dcs-service/dcscloud/v1/oauth/tokens'

  #Add to payload and header your CWP tenant & API keys - client_id, client_secret, x-epmp-customer-id and x-epmp-domain-id
  payload = {'client_id' : clientID, 'client_secret' : clientsecret}
  header = {"Content-type": "application/json" ,'x-epmp-customer-id' : customerID , 'x-epmp-domain-id' : domainID}
  response = requests.post(url, data=json.dumps(payload), headers=header) 
  authresult=response.status_code
  token=response.json()
  if (authresult!=200) :
    print ("\nAuthentication Failed. Did you replace the API keys in the code with your CWP API Keys? Check clientsecret, clientID, customerID, and domainID\n")
    exit()

  #Extracting auth token
  accesstoken= token['access_token']
  accesstoken = "Bearer " + accesstoken

#Additional checks to make sure the agent is installed on supported Kernel versions
  kernel = platform.release()
  kernelversion = kernel.strip()
  print ("Detected OS: " + osdistribution + ", Kernel: " +  kernelversion)

  #CWP REST API function endpoint URL for checking if platform and kernel is supported
  urlplatformcheck = 'https://scwp.securitycloud.symantec.com/dcs-service/dcscloud/v1/agents/packages/supported-platforms'
  payload={}
  payload['osDistribution'] = osdistribution
  payload['kernelVersion'] = kernelversion

  #print 'Payload: ' + str(payload)
  headerplatformcheck = {"Authorization": accesstoken ,'x-epmp-customer-id' : customerID , 'x-epmp-domain-id' : domainID , "Content-Type": "application/json"}
  #print 'Headers: ' + str(headerplatformcheck)

  response = requests.put(urlplatformcheck, data= json.dumps(payload), headers=headerplatformcheck)
  if response.status_code != 200:
        print ("supported-platforms API call failed \n")
        exit()
  outputplatformcheck = {}
  outputplatformcheck = response.json()
  #print outputplatformcheck

  if (outputplatformcheck['supported']) :
        print ("Supported OS: " + osdistribution + ", Kernel: " +  kernelversion);
        print ("\n" + outputplatformcheck['description'])
  else :
        print ("Non Supported OS: " + osdistribution + ", Kernel: " +  kernelversion)
        print (outputplatformcheck['description'] + "\n")
        exit()

  #Output agent platform package type passed as a parameter for debugging
  myosdistribution = osdistribution
  print ("\nDownloading Agent package :-> " +  osdistribution + "  to current directory \n")

  #CWP REST API endpoint URL download package function
  urldonwnload = 'https://scwp.securitycloud.symantec.com/dcs-service/dcscloud/v1/agents/packages/download/platform/'
  urldonwnload = urldonwnload + osdistribution

  #Add to payload and header your CWP tenant & API keys - client_id, client_secret, x-epmp-customer-id and x-epmp-domain-id
  headerdownload = {"Authorization": accesstoken ,'x-epmp-customer-id' : customerID , 'x-epmp-domain-id' : domainID}
  response = requests.get(urldonwnload, headers=headerdownload)

  #On Windows save file as a .zip and as a .tar.gz on linux
  if (osdistribution =='windows') :
      nameofpkg='scwp_agent_' + osdistribution + '_package.zip'
  else :
      nameofpkg='scwp_agent_' + osdistribution + '_package.tar.gz'
  with open(nameofpkg, "wb") as code:
     #Save downloaded package to local file
     code.write(response.content)
     result=response.status_code
  if (result==200) :
     #Agent download API was successfull
     mydict=response.headers
     filename = mydict['content-disposition']
     #Check if file was doenloaded successfully
     if filename.find(nameofpkg) :
        print ("\nAgent package :-> " +  nameofpkg + " downloaded successfully to current directory \n")
  else :
     print ("\nDownload agent API failed. Specify correct platform name.\n")
     exit()

if __name__=="__main__":

   if (len(sys.argv) < 5):
      print ("Insufficient number of arguments passed. Pass all 4 CWP API key parameters from 'Setting Page->API Keys' tab. Usage: python cwpagentinstall.py <Customer ID> <Domain ID> <Client Id> <Client Secret Key>")
      exit()

   customerID=sys.argv[1]
   domainID=sys.argv[2]
   clientID=sys.argv[3]
   clientsecret=sys.argv[4]

   #First dump Instance metadata to use as reference
   #os.system('curl -s http://169.254.169.254/latest/dynamic/instance-identity/document')
   #Determine OS platform name that is needed as input to CWP download agent REST API function

   #print Current working director for referenxe
   curentdir = os.getcwd()
   print ("\nCurrent Working Path = " + os.getcwd())

   #some sample code to detect type of OS platform. CWP API needs platform to be specified in the REST endpoint URL
   osversion = 'undefined'
   osversion = platform.platform()
   print (osversion)

   osdistribution = 'undefined'
   if '.amzn1.' in osversion:
     osdistribution = 'amazonlinux'
   elif '-redhat-7' in osversion:
     osdistribution = 'rhel7'
   elif '-redhat-6' in osversion:
     osdistribution = 'rhel6'
   elif '-centos-7' in osversion:
     osdistribution = 'centos7'
   elif '-centos-6' in osversion:
     osdistribution = 'centos6'
   elif 'Ubuntu-16' in osversion:
    osdistribution = 'ubuntu16'
   elif 'Ubuntu-14' in osversion:
    osdistribution = 'ubuntu14'
   elif 'windows' in osversion:
     osdistribution = 'windows'
   elif '-oracle-7' in osversion:
     osdistribution = 'oel7'
   elif '-oracle-6' in osversion:
     osdistribution = 'oel6'


   #Make sure the selected Platform is one of the supported list
   #print osdistribution
   oslist = ['centos6', 'centos7', 'rhel6', 'rhel7', 'ubuntu14', 'ubuntu16', 'amazonlinux', 'windows', 'oel7', 'oel6']
   if osdistribution not in  oslist:
    print ("\n Invalid OS Platform\n")
    exit()

   download_agentpkg_from_scwp_server(osdistribution)

   #Install for Windows. You can add custom code to expand .zip file and run installagent.bat
   if osdistribution == 'windows':
    exit()

   #Install for Linux Platforms
   else:
     pkgtocopy="scwp_agent_" + osdistribution + "_package.tar.gz"
     package_local = pkgtocopy
     tarcommand = "tar -xvzf " + package_local
     os.system(tarcommand)
     os.system('chmod 700 ./installagent.sh')
     os.system('./installagent.sh')
