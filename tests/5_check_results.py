import os
import sys
import ConfigParser

from syncserver.tests import dbmodel

test_name = sys.argv[1]


# Test databases
for role in ['client', 'server']:
    parser = ConfigParser.SafeConfigParser()
    parser.read(role + '/database.cfg')
    db_uri = parser.get('databases', 'nosetests')
    dbmodel.load_from_uri(db_uri)

    with open(os.path.join(test_name, '5_' + role + '_database.py'), 'rt') as fp:
        data = eval(fp.read())

    expected_records = [tuple(row.items()) for row in data.get('records', [])]
    expected_records.sort()

    select = dbmodel.sqlalchemy.sql.select([dbmodel.tables['records']])
    actual_records = [tuple(dict(row).items()) for row in dbmodel.db.execute(select)]
    actual_records.sort()

    if expected_records != actual_records:
        for i in xrange(min(len(expected_records), len(actual_records))):
            e = expected_records[i]
            a = actual_records[i]
            if e != a:
                break
        else:
            if len(expected_records) < len(actual_records):
                e = None
                a = actual_records[len(expected_records)]
            else:
                e = expected_records[len(actual_records)]
                a = None

        assert expected_records == actual_records, '{}: expected = {}, actual = {}'.format(
            role, repr(e), repr(a))

    # {'sync_name': '__test__', 'section_name': 'records', 'record_id': '1,',
    #  'record_hash': 'a3b48eba3d1b7a709f6d47a9de10c523'},
    expected_record_hashes = [tuple(row.items()) for row in data.get('record_hashes', [])]
    expected_record_hashes.sort()

    select = dbmodel.sqlalchemy.sql.select(
        [dbmodel.tables['record_hashes'].c[column]
         for column in ['sync_name', 'section_name', 'record_id', 'record_hash']])
    actual_record_hashes = [tuple(dict(row).items()) for row in dbmodel.db.execute(select)]
    actual_record_hashes.sort()

    if expected_record_hashes != actual_record_hashes:
        for i in xrange(min(len(expected_record_hashes), len(actual_record_hashes))):
            e = expected_record_hashes[i]
            a = actual_record_hashes[i]
            if e != a:
                break
        else:
            if len(expected_record_hashes) < len(actual_record_hashes):
                e = None
                a = actual_record_hashes[len(expected_record_hashes)]
            else:
                e = expected_record_hashes[len(actual_record_hashes)]
                a = None

        assert expected_record_hashes == actual_record_hashes, (
            '{}: expected = {}, actual = {}'.format(role, repr(e), repr(a)))

# Test log files
for phase in ['compute', 'apply']:
    for log in ['err', 'out']:
        expected_log = open(
            os.path.join(test_name, '5_client_' + phase + '_actions.' + log), 'rt').read()
        actual_log = open(
            os.path.join('client', 'client_' + phase + '_actions.' + log), 'rt').read()
        if log == 'out':
            # Strip sync time
            expected_log = expected_log[expected_log.find('\n') + 1:]
            actual_log = actual_log[actual_log.find('\n') + 1:]
        assert expected_log == actual_log, 'Log mismatch for ({}, {})'.format(phase, log)
