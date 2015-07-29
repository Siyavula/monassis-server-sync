import os
import sys

test_name = sys.argv[1]
try:
    with open(os.path.join(test_name, '1_create_server_database.py'), 'rt') as fp:
        data = eval(fp.read())
except IOError:
    data = {}

import ConfigParser
parser = ConfigParser.SafeConfigParser()
parser.read('server/database.cfg')
db_uri = parser.get('databases', 'nosetests')

from syncserver.tests import dbmodel
dbmodel.load_from_uri(db_uri)
for table in 'records', 'record_hashes':
    dbmodel.tables[table].delete().execute()
for table, rows in data.iteritems():
    for row in rows:
        dbmodel.tables[table].insert().values(**row).execute()
