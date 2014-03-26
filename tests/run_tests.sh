#!/bin/sh

PYTHON_PATH=../env/bin/python
PASTER_PATH=../env/bin/pserve
CONFIG_PATH=../config
ALL_TESTS="test_master_slave_sync test_parent_child_sync test_volatile_master_slave_sync test_volatile_parent_child_sync"

# Clean up
cd server
../${PASTER_PATH} --stop-daemon > /dev/null 2> /dev/null
cd ..
rm -f ${CONFIG_PATH}/__test__.ini

for TEST_NAME in ${ALL_TESTS} ; do

echo ${TEST_NAME}

# Create database
${PYTHON_PATH} 1_create_server_database.py ${TEST_NAME}
${PYTHON_PATH} 1_create_client_database.py ${TEST_NAME}

# Start sync server
cd server
rm -f test_server.log pyramid.log pyramid.pid
../${PASTER_PATH} --daemon test_server.ini > /dev/null
cd ..
sleep 1

# Run client phase 1: compute hash actions
ln -s `pwd`/${TEST_NAME}/config.ini ${CONFIG_PATH}/__test__.ini
cd client
../${PYTHON_PATH} ../2_client_compute_actions.py ../${CONFIG_PATH}/__test__.ini > client_compute_actions.out 2> client_compute_actions.err || { echo 'ERROR'; exit 1; }
cd ..

# Optionally modify the database for volatile tests
${PYTHON_PATH} 3_modify_client_database.py ${TEST_NAME}

# Run client phase 2: apply hash actions
cd client
../${PYTHON_PATH} ../4_client_apply_actions.py ../${CONFIG_PATH}/__test__.ini > client_apply_actions.out 2> client_apply_actions.err || { echo 'ERROR'; exit 1; }
cd ..

# Clean up
cd server
../${PASTER_PATH} --stop-daemon
cd ..
rm ${CONFIG_PATH}/__test__.ini

# Report
${PYTHON_PATH} 5_check_results.py ${TEST_NAME} || { echo 'ERROR'; exit 1; }

done
