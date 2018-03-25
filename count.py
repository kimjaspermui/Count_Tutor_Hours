
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
import pickle
import os.path
from collections import defaultdict
from enum import Enum
import json

class TaskInfo(Enum):
    TIMESTAMP = 0
    EMAIL = 1
    TASK = 2
    DATE = 3
    TIME = 4
    SPECIAL = 5

# constants
MAX_HOURS = 3

# need an index to store from which request to process
masterReport = defaultdict(list)
masterTasks = list()

# data
tutorHourCount = defaultdict(int) # {name: count}
names = defaultdict() # {email: name}

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

# calendar details
CAL_ID = 'eng.ucsd.edu_cprroni4e75jsicjt9bv26nm74@group.calendar.google.com'
TIME_FROM = '2018-03-25T00:00:00-07:00'
TIME_TO = '2018-03-31T23:59:59-07:00'

# constant strings
ADD_DECLINE = 'Decline to add hour to calendar'
# Weeks
WEEK1FROM = '2018-03-25T00:00:00-07:00'
WEEK1TO = '2018-03-31T23:59:59-07:00'

def myPrint(data):
    for line in data:
        print(line)

def printError(message, name, time):
    print(message + ": " + name + " (" + str(time) + ")")

def convertToDatetime(date, time):
    '''Function to convert the date and time into datetime'''
    '''date: month/day/year, time: hr:min:sec'''
    
    # parse out the date and time
    month, day, year = [int(s) for s in date.split('/')]
    startTime = time.split('-')[0]
    hour, minute, second = [int(s) for s in startTime.split(':')]

    # create datetime object
    myDatetime = datetime.datetime(year, month, day, hour, minute, second)

    return myDatetime

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
    '''function to read in names for processing'''

    # global structures
    global names

    print("Reading tutor names...")
    names = json.load(open('names.json'))
    print("done")

def countTutors(service):

    # get all of the events in this week
    events = service.events().list(calendarId=CAL_ID, timeMin=TIME_FROM,
        timeMax=TIME_TO, singleEvents=True, orderBy='startTime').execute()
    
    # iterate through all of the events in this week
    for event in events['items']:

        # get only those with title: Tutor hour with no TBD
        if event['status'] != 'cancelled' and 'Tutor Hour' in event['summary']:

            # parse the list of tutors in this event
            summary = event['summary']
            summary = summary[summary.find("(")+1:len(summary)-1]
            listOfTutors = [t.strip() for t in re.split(',', summary)]
            startTime = str(event['start']['dateTime'])[5:-6]
            endTime = str(event['end']['dateTime'])[11:-6]
            currDate = startTime[:5]
            startTime = startTime[6:]

            # increment count for this tutor
            for tutor in listOfTutors:
                tutorHourCount[tutor] += 1

    # print tutor hours count
    for tutor, count in tutorHourCount.items():
        print("%s\t%d" % (tutor, count))

    # probably save to file instead of printing it

def updateTitle(service):
    '''This function will update the title into correct format:'''
    '''Tutor Hours (Names)'''

    # get all of the events in this week
    events = service.events().list(calendarId=CAL_ID, timeMin=TIME_FROM,
        timeMax=TIME_TO, singleEvents=True, orderBy='startTime').execute()        

    # iterate through all of the events in this week
    for i, event in enumerate(events['items']):

        # get only those with title: Tutor hour with no TBD
        if event['status'] != 'cancelled' and 'tutor hour' in event['summary'].lower():

            # reformat the title
            openIndex = event['summary'].find('(')
            closeIndex = event['summary'].find(')')
            event['summary'] = 'Tutor Hour (' + event['summary'][openIndex+1:closeIndex] + ')'
            updated_event = service.events().update(calendarId=CAL_ID, eventId=event['id'], body=event).execute()

def readMasterReport():
    '''function to readin master report map from file'''
    global masterReport
    if os.path.isfile("masterReport.txt") :
        with open("masterReport.txt", "rb") as myFile:
            masterReport = pickle.load(myFile)

def writeMasterReport():
    '''function to print out report & write out master report map to file'''
    global masterReport
    for k, v in sorted(masterReport.items()):
        print(k)
        for t in v:
            print("\t%s\t%s\t%s" % (t[0], t[1], t[2]))

    with open("masterReport.txt", "wb") as myFile:
        pickle.dump(masterReport, myFile)

def addRequest(myTask):
    '''function to add hour to calendar if it passes the condition'''
    print(myTask[TaskInfo.EMAIL.value])
    myName = names[myTask[TaskInfo.EMAIL.value]]

    # get the datetime format of the current and future time
    myTimestamp = myTask[TaskInfo.TIMESTAMP.value].split()
    timestamp = convertToDatetime(myTimestamp[0], myTimestamp[1])
    futureTime = convertToDatetime(myTask[TaskInfo.DATE.value], myTask[TaskInfo.TIME.value])

    # 1st condition: a future time and at least 24 hours
    deltaDay = (futureTime - timestamp).days
    if deltaDay < 1:
        printError(ADD_DECLINE, myName, futureTime)

def removeRequest(myTask):
    '''function to remove hour to calendar if it passes the condition'''

def readRequests():
    ''' function to read in the requests from google forms'''
    global masterTasks
    if os.path.isfile("requests.txt"):
        with open ("requests.txt") as myFile:
            masterTasks = myFile.readlines()

    # list of tuples: (timestamp, email, task, date, times, special)
    masterTasks = [tuple(s.replace('\n', '').split('\t')) for s in masterTasks]

    myPrint(masterTasks)

def processRequests():
    '''function to distribute task processing in the tasks read in'''
    # need an index to jump to the new process
    for task in masterTasks:
        if task[2] == 'Add':
            addRequest(task)
        elif task[2] == 'Remove':
            addRequest(task)

def main():
    """Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    10 events on the user's calendar.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    # read names to be input to calendar
    readData()

    # read requests and process them
    readRequests()
    processRequests()

    #updateTitle(service)
    countTutors(service)

if __name__ == '__main__':
    main()