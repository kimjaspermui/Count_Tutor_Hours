
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
    RECUR = 5

# constants
MAX_HOURS = 3
MAX_TUTORS = 4

# need an index to store from which request to process
masterReport = defaultdict(list)
masterTasks = list()

# data
names = defaultdict() # {email: name}
tutorHours = defaultdict(list) # {name: list of datetime ("month-day time")} <- TODO: need to change to list of defaultdict
restrictedHours = defaultdict(list) # {date: list of times}
hourCount = defaultdict(int) # {datetime: count}

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
# 8A Spring 2018 Calendar ID
CAL_ID = 'eng.ucsd.edu_vtobr6j7jckkr4j9qmrqc11t6k@group.calendar.google.com'
TIME_FROM = '2018-04-02T00:00:00-07:00'
TIME_TO = '2018-06-08T23:59:59-07:00'
LAST_DATE = '6/8/2018'
LAST_HOUR = '21:00:00'

# constant strings
ADD_DECLINE = 'Decline to add hour to calendar'
REMOVE_DECLINE = 'Decline to remove hour to calendar'
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
    hour, minute, second = [int(s) for s in time.split(':')]

    # create datetime object
    myDatetime = datetime.datetime(year, month, day, hour, minute, second)

    return myDatetime

def convertTo24(time):
    '''Function to convert the am/pm time to 24 system time'''
    colonIndex = time.find(':')
    myHour = int(time[:colonIndex])
    if myHour == 12 and "pm" in time:
        return "12:00:00"
    elif "am" in  time:
        return str(myHour) + ":00:00"
    elif "pm" in time:
        return str(myHour+12) + ":00:00"
    else:
        print("Erorr in converting to 24 hour system!")

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
    global restrictedHours

    print("Reading tutor names...")
    names = json.load(open('8A_Names.json'))
    print("done")

    print("Reading restricted hours...")
    restrictedHours = json.load(open('8A_restricted_hours.json'))
    print("done")

def countTutors(service):

    global tutorHours
    global hourCount

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
                tutorHours[tutor].append(currDate + " " + startTime)
                hourCount[currDate + " " + startTime] += 1

    # print tutor hours count
    # TODO: need to fix this
    for tutor, listOfHours in tutorHours.items():
        print("%s\t%s" % (tutor, listOfHours))

    # probably save to file instead of printing it

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

def getEvent(timeslot, service):
    '''function that will return an event with the time slot if exists'''

    # get the events on that day
    startTime = "%sT00:00:00-07:00" % (timeslot.date())
    endTime = "%sT23:59:59-07:00" % (timeslot.date())

    # get all of the events in this time frame
    events = service.events().list(calendarId=CAL_ID, timeMin=startTime,
        timeMax=endTime, singleEvents=True, orderBy='startTime').execute()

    for event in events['items']:

        # get only those with title: Tutor hour with no TBD
        if event['status'] != 'cancelled' and 'Tutor Hour' in event['summary']:
            currTime = str(event['start']['dateTime'])[11:-6]
            if str(timeslot.time()) == currTime:
                # get the list of names
                return event

def addRequest(myTask, service):
    '''function to add hour to calendar if it passes the condition'''
    myName = names[myTask[TaskInfo.EMAIL.value]]
    myDate = myTask[TaskInfo.DATE.value]
    allTime = myTask[TaskInfo.TIME.value].split(', ')
    repeatNum = int(myTask[TaskInfo.RECUR.value])
    lastHour = convertToDatetime(LAST_DATE, LAST_HOUR)

    for time in allTime:

      # split start and end time
      myTime = time.split('-')

      # convert the time to 24 hr system
      myTime[0] = convertTo24(myTime[0])
      myTime[1] = convertTo24(myTime[1])

      # get the datetime format of the current and future time
      myTimestamp = myTask[TaskInfo.TIMESTAMP.value].split()
      timestamp = convertToDatetime(myTimestamp[0], myTimestamp[1])
      startTime = convertToDatetime(myDate, myTime[0])
      endTime = convertToDatetime(myDate, myTime[1])
      deltaDay = (startTime - timestamp).total_seconds()

      repeatIndex = 0
      while (lastHour - startTime).total_seconds() >= 0 and repeatIndex < repeatNum:

        # 1st condition: a future time and at least 24 hours NOTE: not doing 24 hrs check
        # 2nd condition: less than maximum hour
        # 3rd condition: not a restricted hour
        # 4th condition: not repeated
        # 5th condition: current time slot has less than max tutors
        if deltaDay < 0:
            printError("It is not a future time-" + ADD_DECLINE, myName, startTime)
            return
        # disable this for now, hard to keep track
        # elif len(tutorHours[myName]) >= MAX_HOURS:
        #     printError("Has max hours-" + ADD_DECLINE, myName, startTime)
        #    return
        elif (myDate in restrictedHours and myTime in restrictedHours[myDate]):
            printError("Restricted hours-" + ADD_DECLINE, myName, startTime)
            return
        elif str(startTime)[5:] in tutorHours[myName]:
            printError("Already in timeslot-" + ADD_DECLINE, myName, startTime)
            return
        elif hourCount[str(startTime)[5:]] >= MAX_TUTORS:
            printError("Has max tutors-" + ADD_DECLINE, myName, startTime)
            return

        # check if event exists, if not, create one, if yes, update the title
        myEvent = getEvent(startTime, service)
        if myEvent is None: 

            # passed the conditions, add the event
            event = {'summary': 'Tutor Hour (%s)' % (myName),
            'start': {'dateTime': '%sT%s-07:00' % (startTime.date(), startTime.time())},
            'end': {'dateTime': '%sT%s-07:00' % (endTime.date(), endTime.time())}
            }

            event = service.events().insert(calendarId=CAL_ID, body=event).execute()
            print("created an event")

        else:

            # update the current entry
            openIndex = myEvent['summary'].find('(')
            closeIndex = myEvent['summary'].find(')')
            myEvent['summary'] = 'Tutor Hour (' + myEvent['summary'][openIndex+1:closeIndex] + ", " + myName + ')'
            updated_event = service.events().update(calendarId=CAL_ID, eventId=myEvent['id'], body=myEvent).execute()
            print("updated an event")

        # update the recorded hours for this tutor
        tutorHours[myName].append(str(startTime.date())[5:] + " " + str(startTime.time()))

        # increment the time by a week
        startTime += datetime.timedelta(days = 7)
        endTime += datetime.timedelta(days = 7)
        repeatIndex += 1

def removeRequest(myTask, service):
    '''function to remove hour to calendar if it passes the condition'''
    myName = names[myTask[TaskInfo.EMAIL.value]]
    myDate = myTask[TaskInfo.DATE.value]
    allTime = myTask[TaskInfo.TIME.value].split(', ')
    repeatNum = int(myTask[TaskInfo.RECUR.value])
    lastHour = convertToDatetime(LAST_DATE, LAST_HOUR)

    for time in allTime:

        # split start and end time
        myTime = time.split('-')

        # convert the time to 24 hr system
        myTime[0] = convertTo24(myTime[0])
        myTime[1] = convertTo24(myTime[1])

        # get the datetime format of the current and future time
        myTimestamp = myTask[TaskInfo.TIMESTAMP.value].split()
        timestamp = convertToDatetime(myTimestamp[0], myTimestamp[1])
        startTime = convertToDatetime(myDate, myTime[0])

        repeatIndex = 0
        while (lastHour - startTime).total_seconds() >= 0 and repeatIndex < repeatNum:

          # check if it is a future time
          deltaDay = (startTime - timestamp).total_seconds()
          if deltaDay < 0:
              printError("It is not a future time-" + REMOVE_DECLINE, myName, startTime)
              return

          # get the event with this start time
          myEvent = getEvent(startTime, service)

          # check if hour exists, if not, no hours to remove
          if myEvent is None:
              printError("Hour doesn't exist-", REMOVE_DECLINE, myName, startTime)
              return

          else:
              # update the current entry
              openIndex = myEvent['summary'].find('(')
              closeIndex = myEvent['summary'].find(')')
              listOfNames = myEvent['summary'][openIndex+1:closeIndex].split(', ')
              listOfNames.remove(myName)

              # case for no tutors in this slot
              if len(listOfNames) == 0:
                  service.events().delete(calendarId=CAL_ID, eventId=myEvent['id']).execute()

              # case for removing this one tutor from this slot by updating the title
              else:
                  strNames = listOfNames[0]
                  for i in range(1, len(listOfNames)):
                      strNames += ", " + listOfNames[i]
                  myEvent['summary'] = 'Tutor Hour (' + strNames + ')'
                  updated_event = service.events().update(calendarId=CAL_ID, eventId=myEvent['id'], body=myEvent).execute()

          # increment the time by a week
          startTime += datetime.timedelta(days = 7)
          repeatIndex += 1

def readRequests():
    ''' function to read in the requests from google forms'''
    global masterTasks
    if os.path.isfile("8A_requests.txt"):
        with open ("8A_requests.txt") as myFile:
            masterTasks = myFile.readlines()

    # list of tuples: (timestamp, email, task, date, times, special)
    masterTasks = [tuple(s.replace('\n', '').split('\t')) for s in masterTasks]

    #myPrint(masterTasks)

def processRequests(service):
    '''function to distribute task processing in the tasks read in'''
    # need an index to jump to the new process
    for task in masterTasks:
        if task[2] == 'Add':
            addRequest(task, service)
        elif task[2] == 'Remove':
            removeRequest(task, service)

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

    # populate the tutor hours count for each tutors
    countTutors(service)

    # read requests and process them
    readRequests()
    processRequests(service)

if __name__ == '__main__':
    main()
