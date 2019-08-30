"""
usage: python test_post.py
run test_post.py after you have started the webhook listener
will test it out using this example call
This is the simplest way to try out webhooks, does not require ssl or port-forwarding
"""
import requests

requests.post('http://localhost:8080/webhook',
              json='{"userName": "Job van Schipstal", '
                   '"alarmRateLimitTill": null, '
                   '"extraInfo": {"Device ID": "********", '
                   '"Device name": "Project #D4 Alarming machine", '
                   '"Counter1000Max30": "30"}, '
                   '"shortContent": "Alarm every 30s of Project #D4'
                   ' - Alarming machine was triggered at 8/29/19, 12:26 PM UTC", '
                   '"companyId": "1111-2222-3333-4444-5555", '
                   '"systemLabel": "alarm-medium", '
                   '"createdOn": "2019-08-29T12:26:24", '
                   '"companyName": "IXON Product Demo", '
                   '"userId": "*******", '
                   '"longContent": "Instructions: Your machine entered an alarm state. '
                   'Please turn the machine off, open valve D5, '
                   'and clear any dirt. Reset the alarm afterwards to resume production."}')
