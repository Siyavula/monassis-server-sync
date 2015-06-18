#!/bin/sh
. venv/bin/activate

echo "Stopping daemon"
pserve --status config/northern-academy-1.ini
pserve --stop-daemon

echo "\n\nStarting daemon"
pserve config/northern-academy-1.ini --daemon
pserve --status config/northern-academy-1.ini
