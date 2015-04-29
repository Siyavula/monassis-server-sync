import json
import random
import requests
import urlparse


class SyncException(Exception):
    def __init__(self, status_code, error_message):
        Exception.__init__(self, str(error_message) + ' [' + str(status_code) + ']')
        self.status_code = status_code
        self.error_message = error_message


class DatabaseLocked(SyncException):
    pass


class UnhandledResponse(SyncException):
    pass


class SyncSession:
    def __init__(self, sync_name, host_uri, sync_time, auth=None, verify=True,
                 simulate_network_errors=False):
        self.sync_name = sync_name
        self.host_uri = host_uri
        self.request_params = {
            'auth': auth,
            'verify': verify,
        }
        self.simulate_network_errors = simulate_network_errors

        # Obtain lock
        self.lock_key = None

        response = requests.put(
            urlparse.urljoin(self.host_uri, '/{}/lock'.format(self.sync_name)),
            data=json.dumps({'sync_time': sync_time.isoformat()}), **self.request_params)
        self.__handle_unexpected_status_codes(response, [200, 423])
        body = json.loads(response.content)
        if response.status_code == 423:
            raise DatabaseLocked(423, body['error']['message'])
        self.lock_key = body['lock_key']
        self.server_vars = body['server_vars']

    def __del__(self):
        if self.lock_key is not None:
            # Release lock
            response = requests.put(
                urlparse.urljoin(self.host_uri, '/{}/unlock'.format(self.sync_name)),
                data=json.dumps({'lock_key': self.lock_key}),
                **self.request_params)
            self.__handle_unexpected_status_codes(response)

    def __handle_unexpected_status_codes(self, response, known_codes=[200]):
        if response.status_code not in known_codes:
            try:
                message = json.loads(response.content)['error']['message']
            except Exception:
                message = None
            raise UnhandledResponse(response.status_code, message)

    def get_hash_hash(self):
        response = requests.get(
            urlparse.urljoin(self.host_uri, '/{}/hash-hash'.format(self.sync_name)),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)
        return json.loads(response.content)['hash-hash']

    def get_hash_actions(self, sync_time, client_vars):
        response = requests.get(
            urlparse.urljoin(self.host_uri, '/{}/hash-actions'.format(self.sync_name)),
            data=json.dumps({
                'lock_key': self.lock_key,
                'sync_time': sync_time.isoformat(),
                'client_vars': client_vars}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)
        return json.loads(response.content)['hash_actions']

    def get_record(self, section_name, record_id):
        response = requests.get(
            urlparse.urljoin(self.host_uri, '/{}/{}/{}/record'.format(
                self.sync_name, section_name, record_id)),
            **self.request_params)
        self.__handle_unexpected_status_codes(response, [200, 404])
        if response.status_code == 200:
            return json.loads(response.content)['record']
        else:
            return None

    def get_records_for_section(self, section_name, record_ids):
        response = requests.get(
            urlparse.urljoin(self.host_uri, '/{}/{}/records'.format(self.sync_name, section_name)),
            data=json.dumps({
                'record_ids': record_ids}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)
        return json.loads(response.content)['records']

    def put_record(self, section_name, record_id, record):
        response = requests.put(
            urlparse.urljoin(self.host_uri, '/{}/{}/{}/record'.format(
                self.sync_name, section_name, record_id)),
            data=json.dumps({
                'lock_key': self.lock_key,
                'record': record}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)

    def delete_record(self, section_name, record_id):
        response = requests.delete(
            urlparse.urljoin(self.host_uri, '/{}/{}/{}/record'.format(
                self.sync_name, section_name, record_id)),
            data=json.dumps({
                'lock_key': self.lock_key}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)

    def put_records_for_section(self, section_name, actions):
        response = requests.put(
            urlparse.urljoin(self.host_uri, '/{}/{}/records'.format(self.sync_name, section_name)),
            data=json.dumps({
                'lock_key': self.lock_key,
                'actions': actions}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)

    def get_hash(self, section_name, record_id):
        response = requests.get(
            urlparse.urljoin(self.host_uri, '/{}/{}/{}/hash'.format(
                self.sync_name, section_name, record_id)),
            **self.request_params)
        self.__handle_unexpected_status_codes(response, [200, 404])
        if response.status_code == 200:
            return json.loads(response.content)['hash']
        else:
            return None

    def put_hash(self, section_name, record_id, hash):
        response = requests.put(
            urlparse.urljoin(self.host_uri, '/{}/{}/{}/hash'.format(
                self.sync_name, section_name, record_id)),
            data=json.dumps({
                'lock_key': self.lock_key,
                'hash': hash}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)

    def delete_hash(self, section_name, record_id):
        response = requests.delete(
            urlparse.urljoin(self.host_uri, '/{}/{}/{}/hash'.format(
                self.sync_name, section_name, record_id)),
            data=json.dumps({
                'lock_key': self.lock_key}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)

    def put_hashes_for_section(self, section_name, actions):
        response = requests.put(
            urlparse.urljoin(self.host_uri, '/{}/{}/hashes' % (self.sync_name, section_name)),
            data=json.dumps({
                'lock_key': self.lock_key,
                'actions': actions}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)

    def get_record_and_hash(self, section_name, record_id):
        response = requests.get(
            urlparse.urljoin(self.host_uri, '/{}/{}/{}/record-hash'.format(
                self.sync_name, section_name, record_id)),
            **self.request_params)
        self.__handle_unexpected_status_codes(response, [200, 404])
        if response.status_code == 200:
            return json.loads(response.content)['record'], json.loads(response.content)['hash']
        else:
            return None, None

    def put_record_and_hash(self, section_name, record_id, record, hash):
        response = requests.put(
            urlparse.urljoin(self.host_uri, '/{}/{}/{}/record-hash'.format(
                self.sync_name, section_name, record_id)),
            data=json.dumps({
                'lock_key': self.lock_key,
                'record': record,
                'hash': hash}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)

    def delete_record_and_hash(self, section_name, record_id):
        response = requests.delete(
            urlparse.urljoin(self.host_uri, '/{}/{}/{}/record-hash'.format(
                self.sync_name, section_name, record_id)),
            data=json.dumps({
                'lock_key': self.lock_key}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)

    def put_records_and_hashes_for_section(self, section_name, actions):
        response = requests.put(
            urlparse.urljoin(self.host_uri, '/{}/{}/record-hashes'.format(
                self.sync_name, section_name)),
            data=json.dumps({
                'lock_key': self.lock_key,
                'actions': actions}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)

    def _random_failure(self):
        if self.simulate_network_errors and random.uniform(0, 1) < 0.5:
            raise requests.ConnectionError("Simulated connection error")
