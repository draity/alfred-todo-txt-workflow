
# encoding: utf-8

import sys
import re
import argparse
from datetime import date, datetime
from workflow import Workflow, ICON_WARNING

def get_suggestions(query, symbol):
    """Adds suggestions items accoridng to input query and the found suggestions for the symbol.
    Filters suggestables with the current input following the symbol

    Arguments:  query should be the currently entered query as unicode string
                symbol is the symbol which starts suggestion for these suggestables
    """ 
    suggestables = set()
    for line in open(todotxt_location, "r"):
        description = wf.decode(line)
        regex = re.escape(symbol) + r"\S*(?=\s|$)"
        projectsOfThisLine = set(re.findall(regex, description))
        suggestables = suggestables | projectsOfThisLine # union of sets

    index = query.rfind(symbol)
    partialInput = query[index:]

    suggestables = wf.filter(partialInput, suggestables)

    for suggestion in suggestables:
        wf.add_item( title=suggestion
                   , autocomplete=u"{query}{suggestion} ".format(query=query[:index], suggestion=suggestion)
                   , valid=False
                   )

def add_suggestions(query):
    """Adds all possible suggestions to the feedback items
    Calls submethod for triggering symbols

    Arguments:  query should be the currently entered query as unicode string
    """
    # Get projects suggestions
    match = re.match(r".*(\s|^)\+\S*$", query)
    if match: 
        get_suggestions(query, "+")

    # Get context suggestions
    match = re.match(r".*(\s|^)@\S*$", query)
    if match:
        get_suggestions(query, "@")

def get_description(todoItem):
    """Returns the description field for filtering"""
    return todoItem["description"]

def add_todo_item_list(query):
    """Adds all todo items nicley formatted to the feedback items

    Arguments:  query should be the user input as unicode string which filter the list
    """
    # get current datetime
    today = datetime.now()

    # retrieve todo items as list
    todoList = []
    i = 1
    for line in open(todotxt_location, "r"):
        description = wf.decode(line)[:-1]
        if description != "":
            todoList.append(dict(id=i, description=description))
            i = i + 1
    
    # If script was passed a query, use it to filter posts
    if query[0]:
        todoList = wf.filter(query[0], todoList, key=get_description)

    # Loop through the returned posts and add an item for each to
    # the list of results for Alfred
    currentTodos = []
    for todoItem in todoList:
        # get priority: second element (after line number) and remove braces
        match = re.match(r"\([A-Z]\)", todoItem['description'])
        if match:
            todoItem['priority'] = todoItem['description'][1:2]
            todoItem['description'] = todoItem['description'][4:]
        else: 
            todoItem['priority'] = "noPrio"

        todoItem['title'] = todoItem['description'] # will be the title to be displayed
        todoItem['subtitle'] = "" # subtitle

        # split todo description on threshold date 
        match = re.split(r"(t:\d{4}-\d{2}-\d{2})", todoItem['description'])
        # if todo description contains a threshold date the matched length is a minimum of 2
        if len(match) >= 2 :
            # concatenate the parts before and after the threshold date and use it as title
            todoItem['title'] = match[0].strip() + match[2].rstrip() #TODO: JOIN
            # get datetime object for the threshold date
            todoItem['thresholdDate'] = datetime.strptime(match[1][2:], "%Y-%m-%d")
            # calc the timedelta
            threshold = todoItem['thresholdDate'] - today
            # don't show todos with threshold dates in the future
            if threshold.days >= 0:
                continue

        # look for add date at the beginning of the current description
        match = re.match(r"(\d{4}-\d{2}-\d{2})", todoItem['description'])
        # if there is one:
        if match:
            # remove it from description and title
            todoItem['description'] = todoItem['description'][11:]
            todoItem['title'] = todoItem['title'][11:]

            # add the timedelta in days to the subtitle
            todoItem['addedDate'] = datetime.strptime(match.group(1), "%Y-%m-%d")
            since = today - todoItem['addedDate']
            todoItem['subtitle'] += u"since {days} days".format(days=since.days)

        # split todo description on due date 
        match = re.split(r"(due:\d{4}-\d{2}-\d{2})", todoItem['description'])
        # if todo description contains a duedate the matched length is a minimum of 2
        if len(match) >= 2 :
            # concatenate the parts before and after the duedate and use it as title
            todoItem['title'] = match[0].strip() + match[2].rstrip()
            # get datetime object for the duedate
            todoItem['dueDate'] = datetime.strptime(match[1][4:], "%Y-%m-%d")
            # add duedate to subtitle
            todoItem['subtitle'] += u" - due at {date}".format(date=todoItem['dueDate'].strftime("%d.%m.%Y"))

        currentTodos.append(todoItem)

    # sorting = wf.settings[sorting].split(';')
    # sortstring = ""
    # for sortkey in sorting:
    #     sortstring = "".join([sortstring, todoItem[sortkey]])
    # sort by specific key TODO special sort key function
    currentTodos.sort(key=lambda todoItem : todoItem['priority'].join(todoItem['addedDate'].isoformat()))

    for todoItem in currentTodos:
        # Add the item
        wf.add_item( title=todoItem['title']
                   , subtitle=todoItem['subtitle']
                   , autocomplete=u"#{id}{delimiter}{todo}".format(id=todoItem['id'], delimiter=delimiter, todo=todoItem['description'])
                   , valid=False
                   , icon=u"{prio}.png".format(prio=todoItem['priority'])
                   )

def main(wf):
    """Main method which is triggered for each query
    Calls the desired action or feedback functions
    
    Arguments:  wf is the workflow object
    """
    ####################################################################
    # Parse arguments
    ####################################################################
    
    parser = argparse.ArgumentParser()
    # add an optional query and save it to 'query'
    parser.add_argument('query', nargs='?', default=None)
    # parse the script's arguments
    args = parser.parse_args(wf.args)

    ####################################################################
    # Check for missing settings
    ####################################################################

    #log.debug(todotxt_location)
    if not todotxt_location:  
        wf.add_item( title=u"Where is your todo.txt located?"
                   , subtitle=u"Action this item to locate the file"
                   , arg=""
                   , valid=False
                   , icon=ICON_WARNING
                   )
    if not donetxt_location:  
        wf.add_item( title=u"Where is your done.txt located?"
                   , subtitle=u"Action this item to locate the file"
                   , arg=""
                   , valid=False
                   , icon=ICON_WARNING
                   )
    if not todotxt_location or not donetxt_location:
        wf.send_feedback()
        return 0

        ### List mode ###
        # split query on delimiter
        query = args.query.split(delimiter)
            
        # get and add suggestions
        add_suggestions(query[0])

        # add todo items
        add_todo_item_list(query)

        ### Send the results to Alfred as XML ###
        wf.send_feedback()


if __name__ == u"__main__":
    wf = Workflow()
    log = wf.logger
    # set delimiter for parsing of queries
    delimiter = u"⇒"
    # get file location as stored in the settings
    todotxt_location = wf.settings.get('todo-file-location', None)
    donetxt_location = wf.settings.get('done-file-location', None)
    sys.exit(wf.run(main))