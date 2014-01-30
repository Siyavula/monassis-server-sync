#!/bin/bash

APP_HOME=$HOME/monassis-server-sync

cd $APP_HOME
source env/bin/activate

exec pserve production.ini 2>&1
