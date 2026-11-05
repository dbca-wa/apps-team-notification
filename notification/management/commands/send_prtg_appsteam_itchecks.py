from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta, datetime
from notification import email_templates
import requests
import re
import sys

class Command(BaseCommand):
    help = 'Send IT Checks to PRTG for Apps Team'

    def handle(self, *args, **options):
        print ("Starting to send Apps Team IT Checks")

        username = settings.PRTG_USERNAME
        password = settings.PRTG_PASSWORD
        
        # get pass hash

        r = requests.get(
            settings.PRTG_HOST + "/api/getpasshash.htm",
            params={
                "username": username,
                "password": password
            },
            verify=False
        )

        # if r != 200:
        #     return "ERROR"

        passhash = r.text

        r = requests.get(
            settings.PRTG_HOST + "/api/table.json",
            params = {
                "content": "sensors",
                "columns": "objid,downtimesince,device,sensor,sensortype,lastvalue,status,message,priority,comments, tags, active, lastcheck,lastvalue",
                "filter_status": ["3","4", "5", "10", "13","14","7","8","9", "11", "12"],
                # "filter_status": ["5"],
                "id": "15142",
                "output": "json",
                "sortby": "-lastcheck",
                "count": 1,
                "username": username,
                "passhash": passhash 
            },
            verify=False
        )
        main_check = r.json()
        last_sensor_check = main_check['sensors'][0]['lastcheck_raw']
    
        print ("Last Sensor Check: ", main_check['sensors'][0]['lastcheck'])
        dt = datetime(1899, 12, 30) + timedelta(days=float(last_sensor_check), hours=8)
        formatted_last_sensor = dt.strftime("%m/%d/%Y %I:%M:%S %p")
        now = datetime.now() + timedelta(hours=8)
        formatted_now= now.strftime("%m/%d/%Y %I:%M:%S %p")
        difference = now - dt
        difference_minutes = difference.total_seconds() / 60        

        # sys.exit()
        # get sensor status

        r = requests.get(
            settings.PRTG_HOST + "/api/table.json",
            params = {
                "content": "sensors",
                "columns": "objid,downtimesince,device,sensor,sensortype,lastvalue,status,message,priority,comments, tags, active, lastcheck,lastvalue,url",
                "filter_status": ["3","4", "5", "10", "13","14","7","8","9", "11", "12"],
                # "filter_status": ["5"],
                "id": "15142",
                "output": "json",
                "username": username,
                "passhash": passhash 
            },
            verify=False
        )

        checks = {"monitors" :[], "monitor_status": {"last_job_run": formatted_last_sensor, "time_differnce_last_job": difference_minutes, "current_time" : formatted_now}}
        json_data = r.json()        
        for i in json_data['sensors']:
           
            url = None
            try:
                url_response = requests.get(
                    settings.PRTG_HOST + "/api/getobjectproperty.htm",
                    params={
                        "id": i['objid'],
                        "name": "httpurl",
                        "show": "text",
                        "username": username,
                        "passhash": passhash,
                        
                    },
                    verify=False
                )            
                match = re.search(r"<result>(.*?)</result>", url_response.text, re.DOTALL)
                url = match.group(1).strip() if match else None
                if "http:" in url or "https:" in url:
                    pass
                else:
                    url = None
            except Exception as e:
                print (e)

            
            itcheck = True
            #if i['status'] != "Up" and i['status'] != "Down" and i['status'] != "Paused" and i['status'] != "Paused  (paused by parent)" and i['status'] != "Paused  (paused)" and i['status'] != "Warning":
                # print (i)
                #print(i['device'], i['sensor'], i['status'], i['lastvalue'], i['message'], i['downtimesince'],i['lastcheck'])
            # print (i)
            row = {}
            row['objid'] = i['objid']
            row["name"] = i['sensor']
            if i['status'] == "Up":
                row["status"]  = 3
            elif i['status'] == "Warning" or i["status"] == "Unusual":
                row["status"]  = 2                
            elif i['status'] == "Down" or i['status'] == "Down (Acknowledged)":
                row["status"]  = 1
            elif i['status'] == "Paused" or i["status"] == "Paused  (paused by parent)" or i["status"] == "Paused  (paused by parent)" or i["status"] == "Paused  (paused)":
                row["status"]  = 4               
            else:
                row["status"]  = 0
            # row["lastcheck"] = i['lastcheck']
            dt = datetime(1899, 12, 30) + timedelta(days=float(i['lastcheck_raw']), hours=8)
            formatted = dt.strftime("%m/%d/%Y %I:%M:%S %p")
            
            row["lastcheck"] = str(formatted)
            row["downtimesince"] = i['downtimesince']
            row["mon_type"] = i['sensor']
            row["message"] = i['message_raw']
            row["helpdoc"] = False


            match = re.search(r'\bnoitcheck\b', i["tags"])            
            if match:
                #print (i)
                itcheck = False                

            # Reponse Type Start
            match = re.search(r'\bhelp-doc-\d+\b', i["tags"])            
            if match:
                row["helpdoc"] = True                
                help_doc_id = match.group(0)                
                row["helpdocid"] = help_doc_id.replace('help-doc-','')   
                                                                                             
            row["businesshours"] = False
            if "business-hours" in i["tags"]:
                row["businesshours"] = True
            # Response Type End

            row["responsible_group"] = "Application Team"
            match = re.search(r'\bteam-infra\d+\b', i["tags"])            
            if match:                          
                responsible_group = match.group(0)                
                row["responsible_group"] = "Infrastructure Team" 

            match = re.search(r'\bteam-security\d+\b', i["tags"])            
            if match:                          
                responsible_group = match.group(0)                
                row["responsible_group"] = "Security Team"                 

            if itcheck is True:
                checks["monitors"].append(row)  
            row["url"] = url
        # print (r.text)

        t = email_templates.AppCheckList()
    
        to_addresses = []
    
        for email in settings.APPSTEAM_ITCHECKS_EMAIL.split(','):
            print(email)
            to_addresses.append(email)
        t.send(to_addresses=to_addresses, context={"checks": checks,  "settings": settings}, headers={"Reply-To": settings.IT_CHECKS_REPLY_TO_EMAIL})        
        

