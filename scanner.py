#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# scanner.py - part of the FDroid server tools
# Copyright (C) 2010-12, Ciaran Gultnieks, ciaran@ciarang.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import shutil
import re
import urllib
import time
import subprocess
import traceback
from optparse import OptionParser
import HTMLParser
import common
from common import BuildException
from common import VCSException

#Read configuration...
execfile('config.py')


# Parse command line...
parser = OptionParser()
parser.add_option("-v", "--verbose", action="store_true", default=False,
                  help="Spew out even more information than normal")
parser.add_option("-p", "--package", default=None,
                  help="Scan only the specified package")
(options, args) = parser.parse_args()

# Get all apps...
apps = common.read_metadata(options.verbose)

html_parser = HTMLParser.HTMLParser()

problems = []

extlib_dir = os.path.join('build', 'extlib')

for app in apps:

    skip = False
    if options.package and app['id'] != options.package:
        skip = True
    elif app['Disabled']:
        print "Skipping %s: disabled" % app['id']
        skip = True
    elif not app['builds']:
        print "Skipping %s: no builds specified" % app['id']
        skip = True

    if not skip:

        print "Processing " + app['id']

        try:

            build_dir = 'build/' + app['id']

            # Set up vcs interface and make sure we have the latest code...
            vcs = common.getvcs(app['Repo Type'], app['Repo'], build_dir)

            refreshed_source = False


            for thisbuild in app['builds']:

                if thisbuild['commit'].startswith('!'):
                    print ("..skipping version " + thisbuild['version'] + " - " +
                            thisbuild['commit'][1:])
                else:
                    print "..scanning version " + thisbuild['version']

                    # Prepare the source code...
                    root_dir = common.prepare_source(vcs, app, thisbuild,
                            build_dir, extlib_dir, sdk_path, ndk_path, javacc_path,
                            not refreshed_source)
                    refreshed_source = True

                    # Scan for common known non-free blobs:
                    usual_suspects = ['flurryagent.jar',
                                      'paypal_mpl.jar',
                                      'libgoogleanalytics.jar',
                                      'admob-sdk-android.jar',
                                      'googleadview.jar']
                    for r,d,f in os.walk(build_dir):
                        for curfile in f:
                            if curfile.lower() in usual_suspects:
                                msg = 'Found probable non-free blob ' + os.path.join(r, curfile)
                                msg += ' in ' + app['id'] + ' ' + thisbuild['version']
                                problems.append(msg)

                    # Presence of a jni directory without buildjni=yes might
                    # indicate a problem...
                    if (os.path.exists(os.path.join(root_dir, 'jni')) and 
                            thisbuild.get('buildjni', 'no') != 'yes'):
                        msg = 'Found jni directory, but buildjni is not enabled'
                        msg += ' in ' + app['id'] + ' ' + thisbuild['version']
                        problems.append(msg)

        except BuildException as be:
            msg = "Could not scan app %s due to BuildException: %s" % (app['id'], be)
            problems.append(msg)
        except VCSException as vcse:
            msg = "VCS error while scanning app %s: %s" % (app['id'], vcse)
            problems.append(msg)
        except Exception:
            msg = "Could not scan app %s due to unknown error: %s" % (app['id'], traceback.format_exc())
            problems.append(msg)

print "Finished:"
for problem in problems:
    print problem
print str(len(problems)) + ' problems.'

