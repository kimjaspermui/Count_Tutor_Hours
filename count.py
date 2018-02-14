
from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import urllib.request
import re

import datetime

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def parseData(fname):
    for l in open(fname):
        yield eval(l)

def readData():
    # this will read all tutors and initialize its count
    print("Reading tutors...")
    tutors = {t: 0 for t in list(parseData("tutors 8B"))}
    print("done")
    
    # this will read all tutors' names in google calendar mapping to their name
    print("Reading tutors map...")
    tutorsMap = list(parseData("tutors map 8B.json"))[0]
    print("done")

    return tutors, tutorsMap

def countTutors(service):

    # boolean to see if we need to delete TBD
    delete = True
    eventToDelete = []

    # read tutor info
    tutors, tutorsMap = readData()

    # this is the calendar id with the time range of the week
    calId = 'eng.ucsd.edu_cprroni4e75jsicjt9bv26nm74@group.calendar.google.com'
    timeFrom = '2018-02-04T10:00:00-07:00'
    timeTo = '2018-02-10T23:59:59-07:00'

    # get all of the events in this week
    events = service.events().list(calendarId=calId, timeMin=timeFrom,
        timeMax=timeTo, singleEvents=True, orderBy='startTime').execute()
    
    # iterate through all of the events in this week
    for event in events['items']:

        # code to delete the tutor hours with TBD
        if delete and 'Tutor Hour' in event['summary'] and 'TBD' in event['summary']:
            eventToDelete.append(event['id'])

        # get only those with title: Tutor hour with no TBD
        if event['status'] != 'cancelled' and 'Tutor Hour' in event['summary'] and 'TBD' not in event['summary']:

            # parse the list of tutors in this event
            summary = event['summary']
            summary = summary[summary.find("(")+1:len(summary)-1]
            listOfTutors = [t.strip() for t in re.split(',|，', summary)]

            for tutor in listOfTutors:
                if tutor not in tutorsMap:
                    print("This tutor doesn't exist in map: %s" % (tutor))
                else:
                    name = tutorsMap[tutor]
                    tutors[name] += 1

    # print tutor hours count
    for tutor, count in tutors.items():
        print("%d" % (count))

    # print tutor names in excel order
    for tutor, count in tutors.items():
        print("%s" % (tutor))

    # delete TBD events
    for eventId in eventToDelete:
        service.events().delete(calendarId=calId, eventId=eventId).execute()

def updateTitle(service):
    '''This function will update the title into correct format:'''
    '''Tutor Hours (Names)'''
    
    # this is the calendar id with the time range of the week
    calId = 'eng.ucsd.edu_cprroni4e75jsicjt9bv26nm74@group.calendar.google.com'
    timeFrom = '2018-02-04T10:00:00-07:00'
    timeTo = '2018-02-10T23:59:59-07:00'

    # get all of the events in this week
    events = service.events().list(calendarId=calId, timeMin=timeFrom,
        timeMax=timeTo, singleEvents=True, orderBy='startTime').execute()        

    # iterate through all of the events in this week
    for i, event in enumerate(events['items']):

        # get only those with title: Tutor hour with no TBD
        if event['status'] != 'cancelled' and 'tutor hour' in event['summary'].lower():

            # reformat the title
            openIndex = event['summary'].find('(')
            closeIndex = event['summary'].find(')')
            event['summary'] = 'Tutor Hour (' + event['summary'][openIndex+1:closeIndex] + ')'
            updated_event = service.events().update(calendarId=calId, eventId=event['id'], body=event).execute()


def main():
    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    10 events on the user's calendar.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    updateTitle(service)
    countTutors(service)

if __name__ == '__main__':
    main()
