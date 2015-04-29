import ConfigParser
import os
import sys

from syncserver.tests import dbmodel


test_name = sys.argv[1]


try:
    with open(os.path.join(test_name, '3_modify_client_database.py'), 'rt') as fp:
        data = eval(fp.read())
except IOError:
    print 'Not applicable for {}'.format(test_name)
    sys.exit()

parser = ConfigParser.SafeConfigParser()
parser.read('client/database.cfg')
db_uri = parser.get('databases', 'nosetests')

dbmodel.load_from_uri(db_uri)

for table in 'records', 'record_hashes':
    dbmodel.tables[table].delete().execute()

for table, rows in data.iteritems():
    for row in rows:
        dbmodel.tables[table].insert().values(**row).execute()
