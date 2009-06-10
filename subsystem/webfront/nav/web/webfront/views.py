# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 UNINETT AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License version 2 as published by the Free
# Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.  You should have received a copy of the GNU General Public License
# along with NAV. If not, see <http://www.gnu.org/licenses/>.
#

import os
from ConfigParser import ConfigParser

from django.template import RequestContext

from nav.path import sysconfdir
from nav.django.shortcuts import render_to_response
from nav.models.profiles import Account

from nav.web.templates.DjangoCheetah import DjangoCheetah
from nav.web.webfront.utils import quick_read, current_messages, boxes_down

WEBCONF_DIR_PATH = os.path.join(sysconfdir, "webfront")
WELCOME_ANONYMOUS_PATH = os.path.join(WEBCONF_DIR_PATH, "welcome-anonymous.txt")
WELCOME_REGISTERED_PATH = os.path.join(WEBCONF_DIR_PATH, "welcome-registered.txt")
CONTACT_INFORMATION_PATH = os.path.join(WEBCONF_DIR_PATH, "contact-information.txt")
EXTERNAL_LINKS_PATH = os.path.join(WEBCONF_DIR_PATH, "external-links.txt")
NAV_LINKS_PATH = os.path.join(WEBCONF_DIR_PATH, "nav-links.conf")

def index(request):
    # Read files that will be displayed on front page
    external_links = quick_read(EXTERNAL_LINKS_PATH)
    contact_information = quick_read(CONTACT_INFORMATION_PATH)
    if request._req.session['user']['id'] == Account.DEFAULT_ACCOUNT:
        welcome = quick_read(WELCOME_ANONYMOUS_PATH)
    else:
        welcome = quick_read(WELCOME_REGISTERED_PATH)

    # Read nav-links
    config = ConfigParser()
    config.read(NAV_LINKS_PATH)
    links = config.items('Links')

    return render_to_response(
        DjangoCheetah,
        'webfront/index.html',
        {
            'external_links': external_links,
            'contact_information': contact_information,
            'welcome': welcome,
            'current_messages': current_messages(),
            'boxes_down': boxes_down(),
        },
        RequestContext(request)
    )
