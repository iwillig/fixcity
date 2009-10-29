#!/bin/bash

# Wrapper script that runs our handle_mailin command
# in a fairly location-independent manner.


date >> /tmp/mail-sh-runs.log

HERE="$(cd "${0%/*}" 2>/dev/null; echo "$PWD"/)"
BASEDIR=$HERE/..

cd $BASEDIR


# Find a virtualenv in the nearest parent directory and activate it.
function activator {
    ACTIVATOR_STARTDIR=$PWD
    unset ACTIVATOR_SCRIPT
    while [ true ]; do
	if [ "$PWD" == '/' ]; then
	    break
	elif [ -f ./bin/activate ]; then
	    ACTIVATOR_SCRIPT=$PWD/bin/activate
	    break
	elif [ -f activate ]; then
	    ACTIVATOR_SCRIPT=$PWD/activate
	    break
	else
	    cd ..
	fi
    done
    if [ -f "$ACTIVATOR_SCRIPT" ]; then
	source $ACTIVATOR_SCRIPT
	cd $ACTIVATOR_STARTDIR
        unset ACTIVATOR_SCRIPT ACTIVATOR_STARTDIR
	return 0
    else
	echo No activate script found.
	cd $ACTIVATOR_STARTDIR
        unset ACTIVATOR_SCRIPT ACTIVATOR_STARTDIR
	return 1
    fi
}

activator

echo Who the heck am I? $USER >> /tmp/mail-sh-runs.log
whoami >> /tmp/mail-sh-runs.log

#./manage.py handle_mailin /home/pw/tmp/test_mailin.txt
# Read one message from stdin.

PYTHON_EGG_CACHE=/tmp/$USER-fixcity_mailin_egg_cache ./manage.py handle_mailin \
 $@ #>> /tmp/mail-sh-runs.log 2>&1
