import unittest
import json

from pyramid import testing

from syncserver.tests import init_testing_app, init_testing_db
from syncserver.models.support import DBSession
from syncserver import record_database


class TestApi(unittest.TestCase):
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
        lock_date = {'sync_time': '2015-12-31T01:02:03+04:05'}
        res = self.app.put('/nosetests/lock', json.dumps(lock_date))
        self.assertIsNotNone(res.json.get('lock_key'))
        return res.json['lock_key']

    def test_lock_unlock_behavior(self):
        # Lock, then check that you can read a locked call, then
        # unlock, then check that reading the locked call fails
        lock_key = self.obtain_lock()
        res = self.app.put_json('/nosetests/unlock', {'lock_key': lock_key})
        res = self.app.put_json('/nosetests/unlock', {'lock_key': 'not-a-valid-key'}, status=423)

    def test_create_read_update_delete(self):
        records = [
            ([0], ['abc', 'def', 'ghi']),
            ([1], ['jkl', 'mno', 'pqr']),
            ([2], ['stu', 'vwx', 'yza']),
            ([0], ['bcd', 'efg', 'hij']),
        ]

        lock_key = self.obtain_lock()

        # Create, update, read
        for record_id, data_values in records:
            url = '/nosetests/records/{}/record'.format(
                record_database.record_id_to_url_string(record_id))
            self.app.put_json(url, {'lock_key': lock_key, 'record': data_values})
            res = self.app.get(url)
            self.assertIsNotNone(res.json.get('record'))
            self.assertEquals(res.json['record'], data_values)

        # Delete
        deleted_ids = []
        for record_id, data_values in records:
            if record_id in deleted_ids:
                continue
            url = '/nosetests/records/{}/record'.format(
                record_database.record_id_to_url_string(record_id))
            res = self.app.get(url)                            # record still there
            self.app.delete_json(url, {'lock_key': lock_key})  # delete
            self.app.delete_json(url, {'lock_key': lock_key})  # idempotent
            res = self.app.get(url, status=404)                # record gone
            deleted_ids.append(record_id)
