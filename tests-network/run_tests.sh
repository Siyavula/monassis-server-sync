#!/bin/sh

PYTHON_PATH=../env/bin/python
PASTER_PATH=../env/bin/pserve
CONFIG_PATH=../config
ALL_TESTS="test_master_slave_sync test_slave_master_sync test_parent_child_sync test_child_parent_sync"

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

executetest() {
    local status=1
    while [ $status -ne 0 ]; do
	"$@"
	status=$?
    done
    return 0
}

# Run client
ln -s `pwd`/${TEST_NAME}/config.ini ${CONFIG_PATH}/__test__.ini
cd client
(executetest ../${PYTHON_PATH} ../../client/client.py ../${CONFIG_PATH}/__test__.ini > client_compute_actions.out 2> client_compute_actions.err) || { echo 'ERROR on running client.py'; exit 1; }
cd ..

# Clean up
cd server
../${PASTER_PATH} --stop-daemon
cd ..
rm ${CONFIG_PATH}/__test__.ini

# Report
${PYTHON_PATH} 5_check_results.py ${TEST_NAME} || { echo 'ERROR on running 5_check_results.py'; exit 1; }

done
