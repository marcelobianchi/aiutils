#
# Copyright (C) 2012 Marcelo Belentani de Bianchi
#
# This file is part of aiUtils.
#
# aiUtils is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aiUtils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
#

import os

def name(ncode = None, scode = None, lcode = None, ccode = None):
    if lcode == "":
        lcode = "--"
    if ccode:
        s = "%s.%s.%s.%s" % (ncode, scode, lcode, ccode)
    elif lcode:
        s = "%s.%s.%s" % (ncode, scode, lcode)
    elif scode:
        s = "%s.%s" % (ncode, scode)
    elif ncode:
        s = "%s" % (ncode)
    
    return s

def load_xml(arg, inv):
    if os.path.isfile(arg):
        inv.load_xml(arg)
        return inv

    if arg.find("~") != -1:
        ## webdc.eu:18002~GE.APE,
        raise NotImplementedError("Not Yet Implemented")

    raise Exception("Invalid source supplied %s" % arg)

def unWrapNSLC(objs, archive = None, onlyShared = False):
    # unwrap lists of lists into arrays of tuples
    clist = []
    for (code, spam) in objs.items():
        for (start, obj) in spam.items():
            try:
                if archive and getattr(obj, "archive") != archive:
                    continue
                if onlyShared and getattr(obj, "shared") == False:
                    continue
            except:
                pass
            clist.append((code, start, obj))
    return clist

def overlaps(parent, child):
    if parent.code != child.code:
        return False
    
    if parent.end:
        if parent.end > child.start:
            if not child.end or parent.start < child.end:
                return True
    else:
        if not child.end or parent.start < child.end:
            return True
    return False

def isInside(parent, child):
    if child.end and child.start > child.end:
        raise Exception("Invalid supplied interval for checking")
    if parent.end and parent.start > parent.end:
        raise Exception("Invalid supplied interval")
    if not child.start:
        raise Exception("Invalid interval parent_start")
    if not parent.start:
        raise Exception("Invalid parent_start")
    
    if child.start < parent.start:
        return False
    
    if parent.end:
        if child.start >= parent.end: return False
        if not child.end: return False
        if child.end > parent.end: return False
    
    return True

def isReversed(obj):
    if obj.end and obj.start > obj.end:
        return True
    return False
