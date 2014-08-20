#!/usr/bin/env python

import time
import datetime
import gdata.calendar
import gdata.calendar.service
import argparse
import json

from opensprinklerlib import OpenSprinkler


def active_events(cid):
    """"Takes a google calendar ID and returns an array of active events
    """
    calendar_service = gdata.calendar.service.CalendarService()
    query = gdata.calendar.service.CalendarEventQuery(cid, 'public', 'full')
    query.orderby = 'starttime'
    query.singleevents = 'true'
    query.sortorder = 'a'
    now = datetime.datetime.utcnow()

    nextminute = now + datetime.timedelta(minutes=1)

    query.start_min = now.isoformat()
    query.start_max = nextminute.isoformat()

    events = list()

    try:
        feed = calendar_service.CalendarQuery(query)
    except:
        return False, "Error getting calendar data"

    for event in enumerate(feed.entry):
        events.append(event[1].title.text)
    return True, events


def station_lookup(event, station):
    '''
    Determines if the event includes the sid or matches the station name
    returns bool
    '''
    if str(station.sid) == event.strip():
        return True
    elif station.name.lower() == event.strip().lower():
        return True
    else:
        return False


def calendar_run(controller, CALENDAR_ID):
    '''
    Checks for active calendar events
    and makes sure that the current state matches the active events
    '''
    status, events = active_events(CALENDAR_ID)
    if status:
        desired_state = set()
        current_state = set(controller.enabled_stations())
        # loop through stations and add to set if active
        for station in controller.get_stations():
            for event in events:
                if station_lookup(event, station):
                    desired_state.add(station)
        # Is there any changes that need to be made
        if desired_state != current_state:
            print "Run Time: %s" % (datetime.datetime.now())
            # disable any stations that are no longer active
            disable_list = current_state - desired_state
            if len(disable_list) > 0:
                print "\tDisabled:"
                for station in disable_list:
                    station.disable()
                    print "\t\t %d: %s" % (station.sid, station.name)
            # Enable any stations that became active
            enable_list = desired_state - current_state
            if len(enable_list) > 0:
                print "\tEnabled:"
                for station in enable_list:
                    station.enable()
                    print "\t\t %d: %s" % (station.sid, station.name)


def main():
    controller = OpenSprinkler()

    # Compute config
    parser = argparse.ArgumentParser(description='Control OpenSprinkler schedule with a Google Calendar.')
    parser.add_argument('config', nargs='?', type=str, help='Config file', default='config.json')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-i', '--id', type=str, help='Google Calendar ID')

    args = parser.parse_args()

    # Verify and load config file
    config = None
    try:
        config_file = open(args.config)
        try:
            config = json.loads(config_file.read())
            count = controller.load_config(json.dumps(config))
            if count == 0:
                raise ValueError("Config must contain atleast one station.")

        finally:
            config_file.close()

    except IOError:
        raise IOError("Must have a configuration file defining the stations.")

    # Verify that we have a calendar id
    if args.id is None:
        # No option passed try to get it out of the config file.
        try:
            if config["calendar_id"]:
                args.id = config["calendar_id"]
        except KeyError:
            pass

    if args.id is None:
        raise ValueError("Calendar ID must be set.")

    # Now we have a valid configuration lets run the loop.
    print('OpenSprinkler Calendar Run has started...')
    while True:
        try:
            calendar_run(controller, args.id)
        except:
            pass
        time.sleep(60)  # check every 60 seconds


if __name__ == '__main__':
    main()
