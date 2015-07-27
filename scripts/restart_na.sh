#!/bin/sh
. venv/bin/activate

echo "Stopping daemon"
pserve --status northern-academy.ini
pserve --stop-daemon

echo "\n\nStarting daemon"
pserve northern-academy.ini --daemon
pserve --status northern-academy.ini
