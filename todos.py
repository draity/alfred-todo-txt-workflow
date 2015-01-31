
# encoding: utf-8

import sys
import subprocess
import re
import argparse
import os
from shutil import copyfile
from datetime import date, datetime
from workflow import Workflow, ICON_WARNING

def rewrite_files(linenumber, action, value):
    backupFileLocation = todotxt_location + u".bak"
    copyfile(todotxt_location, backupFileLocation)
    with open(backupFileLocation, "r") as backupFile:
        with open(todotxt_location, "w") as todoFile:
            n = 1 # line offset in comparison to backup
            for i, line in enumerate(backupFile):
                line = wf.decode(line)
                if line[:-1] == "":
                    n = n - 1 # hack for empty lines TODO: remove if not needed 
                    continue
                if str(i+n) == linenumber: #if desired line found
                    if action == u"done":
                        ####################################################################
                        # Done action
                        ####################################################################
                        dateStringToday = datetime.now().strftime("%Y-%m-%d")
                        # append todo to done file and don't write anything to todo file
                        with open(donetxt_location, "a") as doneFile:
                            doneFile.write("".join(["x ", dateStringToday, " ", line.encode('utf-8')]))
                    elif action == u"prio":
                        ####################################################################
                        # Prioritize action
                        ####################################################################
                        newLine = ""
                        if re.match(r"\([A-Z]\)", line):
                            newLine = "".join(["(", value, ")", line[3:]])
                        else:
                            newLine = "".join(["(", value, ") ", line])
                        todoFile.write(newLine.encode('utf-8'))
                    elif action == u"edit":
                        ####################################################################
                        # Edit action
                        ####################################################################
                        newLine = ""
                        # get prio and add date of exisitng todo as groups
                        match = re.match(r"(\([A-Z]\))\s(\d{4}-\d{2}-\d{2})", line)
                        # Append input according to keep existing values
                        if match.group(1) and match.group(2): 
                            newLine = "".join([line[:15], value, "\n"])
                        elif match.group(1):
                            newLine = "".join([line[:4], value, "\n"])
                        elif match.group(2):
                            newLine = "".join([line[:12], value, "\n"])
                        else:
                            newLine = value
                        todoFile.write(newLine.encode('utf-8'))
                else:
                    todoFile.write(line.encode('utf-8'))

def rewrite_selected(linenumber, action, todo):
    if action == u"done":
        ####################################################################
        # Done action
        ####################################################################
        del wf.settings['selected']
    elif action == u"delete":
        ####################################################################
        # Delete action
        ####################################################################
        del wf.settings['selected']
    elif action == u"edit":
        ####################################################################
        # Edit action
        ####################################################################
        wf.settings['selected'] = {'id': linenumber, 'todo': todo}

def perform_action(query):
    """Calls an action according to the action keyword.
    Current actions are: do (Key=done), delete (Key=delete) , prioritize (Key=prio) and edit (Key=edit) a todo.
    No matter which or if an action was called, the workflow is triggered again via applescript to list all todos.
    
    Arguments: query is a unicode string delimeted by delimiter
    """
    if len(query) > 1:
        ####################################################################
        # Do, delete, prioritize and edit action
        ####################################################################
        id = query[1][1:]
        if (len(query) > 2):
            rewrite_selected(id, action, query[2])
            rewrite_files(id, action, query[2])
        else:
            rewrite_selected(id, action, "")
            rewrite_files(id, action, "")

    subprocess.call(["osascript", "-e", 'tell application "Alfred 2" to search "todo "'])

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

def add_todo_item_actions(query):
    """Adds all todo item actions (like edit or delete) to the feedback items

    Arguments:  query should be a delimeted unicode string in the form: {id}{delimiter}{todo-description}
    """
    # if no selected item saved OR the id of this query is not same as the saved one
    if (not 'selected' in wf.settings.keys() or wf.settings['selected']['id'] != query[0]):
        # save the current selection in the settings dict
        wf.settings['selected'] = {'id': query[0], 'todo': query[1]}
    
    # At this point a selection with the same id as the current query is saved! 
    # If the todo description (as stored in the todo.txt file) for this id is the same as the current query text:
    # show all options, else hide them and only show the edit entry
    if (wf.settings['selected']['todo'] == query[1]):
        wf.add_item( title=u"Done"
                   , subtitle=u"Move todo to done.txt"
                   , arg=u"done{delimiter}{id}".format(id=query[0], delimiter=delimiter)
                   , valid=True
                   , icon=u"done.png"
                   )
        wf.add_item( title=u"Delete"
                   , subtitle=u"Todo will be removed completly!"
                   , arg=u"delete{delimiter}{id}".format(id=query[0], delimiter=delimiter)
                   , valid=True
                   , icon=u"remove.png"
                   )
        wf.add_item( title=u"Set priority"
                   , subtitle=u"Choose in next step"
                   , autocomplete=u"{id}{delimiter}prio{delimiter}A".format(id=query[0], delimiter=delimiter)
                   , valid=False
                   , icon=u"prio.png"
                   )

    wf.add_item( title=u"Edit directly..."
               , subtitle=u"...to: {todo}".format(todo=query[1])
               , arg=u"edit{delimiter}{id}{delimiter}{todo}".format(id=query[0], delimiter=delimiter, todo=query[1])
               , valid=True
               , icon=u"edit.png"
               )
    wf.add_item( title=u"Return to list"
               , arg=u"return"
               , valid=True
               , icon=u"return.png"
               )

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

    ####################################################################
    # Call desired mode: 
    # - action: do something, show nothing
    # - feedback: create and list feedback items
    ####################################################################

    ### Check for action flags: if given call desired method ###
    if args.action and args.query:
        ### Action mode ###
        perform_action(args.query.split(delimiter))
    else:

        ### List mode ###
        # split query on delimiter
        query = args.query.split(delimiter)
        
        # parts are used to select state
        numberOfQueryParts = len(query)
        
        if numberOfQueryParts == 2:
            ## State 2: show item actions ##
            ## Precondition at this point: Todo selected ##
            add_todo_item_actions(query)

        else:
            ## State 1: show list of todos ##
            ## Precondition at this point: none ##

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