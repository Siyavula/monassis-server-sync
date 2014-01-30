import unittest

from pyramid import testing

from json import loads

from syncserver.tests import init_testing_app, init_testing_db
from syncserver.models.support import DBSession

class APITests(unittest.TestCase):
    USER = 'rest'
    PAYLOAD = {'a': 'b', 'c': ['d', 'e']}

    def setUp(self):
        self.app = init_testing_app()
        self.session = init_testing_db()


    def tearDown(self):
        DBSession.remove()
        testing.tearDown()


    def create(self, user=USER, entry=PAYLOAD):
        res = self.app.post_json('/create', {'user': user, 'entry': entry})
        self.assertEquals(res.content_type, 'application/json')
        return res.json['entry']


    def test_read_bad_entry(self):
        self.app.get('/read/badness', status=404)


    def test_view_create_entry(self):
        entry = self.create()
        self.assertIsNotNone(entry.get('id'))

        res = self.app.get('/read/%s' % entry['id'])
        self.assertEquals(res.content_type, 'application/json')

        # these two should now match
        entry2 = res.json['entry']
        self.assertDictEqual(entry, entry2)


    def test_request_ids_on_error(self):
        res = self.app.get('/read/notthere', status=404)
        self.assertIsNotNone(res.headers.get('X-Request-Id'))


    def test_request_ids_on_success(self):
        res = self.app.get('/list')
        self.assertIsNotNone(res.headers.get('X-Request-Id'))
        self.assertEquals(res.headers['X-Request-Id'], res.json['request_id'])
