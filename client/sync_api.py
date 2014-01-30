import requests, urlparse, json


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
    def __init__(self, sync_name, host_uri, auth=None, verify=True):
        self.sync_name = sync_name
        self.host_uri = host_uri
        self.request_params = {
            'auth': auth,
            'verify': verify,
        }
        # Obtain lock
        response = requests.put(
            urlparse.urljoin(self.host_uri, '/%s/lock'%(self.sync_name)),
            **self.request_params)
        self.__handle_unexpected_status_codes(response, [200, 423])
        if response.status_code == 200:
            self.lock_key = json.loads(response.content)['lock_key']
        else:
            self.lock_key = None
            raise DatabaseLocked(423, json.loads(response.content)['error']['message'])


    def __del__(self):
        if self.lock_key is not None:
            # Release lock
            response = requests.put(
                urlparse.urljoin(self.host_uri, '/%s/unlock'%(self.sync_name)),
                data = json.dumps({'lock_key': self.lock_key}),
                **self.request_params)
            self.__handle_unexpected_status_codes(response)


    def __handle_unexpected_status_codes(self, response, known_codes=[200]):
        if response.status_code not in known_codes:
            try:
                message = json.loads(response.content)['error']['message']
            except Exception:
                message = None
            raise UnhandledResponse(response.status_code, message)
            

    def get_hashes(self):
        response = requests.get(
            urlparse.urljoin(self.host_uri, '/%s/hashes'%(self.sync_name)),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)
        return json.loads(response.content)['hashes']

        
    def get_hash_actions(self):
        response = requests.get(
            urlparse.urljoin(self.host_uri, '/%s/hash-actions'%(self.sync_name)),
            data = json.dumps({'lock_key': self.lock_key}),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)
        return json.loads(response.content)['hash_actions']


    def get_record(self, section, record_id):
        # TODO: how to process record_id
        response = requests.get(
            urlparse.urljoin(self.host_uri, '/%s/records/%s/%s'%(self.sync_name, section, record_id)),
            **self.request_params)
        self.__handle_unexpected_status_codes(response)
        return json.loads(response.content)['record']
