#!/bin/sh
. venv/bin/activate

echo "Stopping daemon"
pserve --status config/northern-academy-2.ini
pserve --stop-daemon

echo "\n\nStarting daemon"
pserve config/northern-academy-2.ini --daemon
pserve --status config/northern-academy-2.ini
