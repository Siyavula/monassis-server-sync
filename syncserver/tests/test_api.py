import unittest

from pyramid import testing

from json import loads

from syncserver.tests import init_testing_app, init_testing_db
from syncserver.models.support import DBSession
from syncserver import record_database

class APITests(unittest.TestCase):
    USER = 'rest'
    PAYLOAD = {'a': 'b', 'c': ['d', 'e']}

    def setUp(self):
        self.app = init_testing_app()
        self.session = init_testing_db()


    def tearDown(self):
        DBSession.remove()
        testing.tearDown()


    def test_read_bad_entry(self):
        self.app.get('/read/badness', status=404)


    def test_request_ids_on_error(self):
        res = self.app.get('/read/notthere', status=404)
        self.assertIsNotNone(res.headers.get('X-Request-Id'))


    def test_request_ids_on_success(self):
        res = self.app.get('/server_status')
        self.assertIsNotNone(res.headers.get('X-Request-Id'))
        self.assertEquals(res.headers['X-Request-Id'], res.json['request_id'])

    def obtain_lock(self):
        res = self.app.put('/nosetests/lock')
        self.assertIsNotNone(res.json.get('lock_key'))
        return res.json['lock_key']


    def test_lock_unlock_behavior(self):
        # Lock, then check that you can read a locked call, then
        # unlock, then check that reading the locked call fails
        lockKey = self.obtain_lock()
        res = self.app.put_json('/nosetests/unlock', {'lock_key': lockKey})
        res = self.app.put_json('/nosetests/unlock', {'lock_key': 'not-a-valid-key'}, status=423)


    def test_put_and_get_record(self):
        recordId = ('column', 'id',)
        recordData = {'some': 'data'}

        lockKey = self.obtain_lock()
        url = '/nosetests/records/' + record_database.record_id_to_url_string(recordId) + '/record'
        self.app.put_json(url, {'lock_key': lockKey, 'record': recordData})
        res = self.app.get(url)
        self.assertIsNotNone(res.json.get('record'))
        self.assertEquals(res.json['record'], record)
