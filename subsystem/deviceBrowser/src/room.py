from mod_python import apache
from nav import db
from nav.db import manage 
from nav.errors import *
import forgetHTML as html
from nav.web import urlbuilder
from nav.web.tableview import TableView

def process(request):
    args = request['args']
    if not args:
        # We need a trailing /
        raise RedirectError, urlbuilder.createUrl(division="room")

    if args[0] == "":
        return showIndex()
    return getAllInRoom(args[0])
def showIndex():
    result = html.Division()
    result.append(html.Header("All rooms", level=1))
    rooms = manage.Room.getAll()
    table = TableView("Roomid", "Description", "Location")
    for room in rooms:
        row = []
        link = html.Anchor(room.roomid, href=room.roomid)
        row.append(link)
        row.append(room.descr or "")
        row.append(urlbuilder.createLink(room.location))
        table.add(*row)
    table.sort()    
    return table

def getAllInRoom(roomid):
    room = manage.Room(roomid)
    netboxes = room.getChildren(manage.Netbox, orderBy="sysname")
    result = html.Division()
    result.append(html.Header("Room %s (%s)" % (room, room.roomid)))
    for netbox in netboxes:
        link = html.Anchor(netbox.sysname, href="../%s" % netbox.sysname)
        line = html.Division(link)
        result.append(line)
    return result
