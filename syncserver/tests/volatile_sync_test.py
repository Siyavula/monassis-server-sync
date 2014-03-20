if __name__ == '__main__':
    from syncserver.client import SyncClient
    from syncserver import utils

    def custom_import(name, path=None):
        import imp
        file, pathname, description = imp.find_module(name, path)
        code = compile(file.read(), pathname, "exec", dont_inherit=True)
        file.close()
        module = imp.new_module(name)
        exec code in module.__dict__
        return module

    config_path = 'config/nosetests.ini'
    log_file = 'test_client.log'

    # Create server database and populate with data
    serverdb = custom_import('dbmodel', ['syncserver/tests'])
    serverdb.load_from_uri('sqlite:///test_server.sqlite')
    serverdb.load_db()
    serverdb.create(**{'column1': 'abc', 'column2': 'def', 'column3': 'ghi'})

    # create client database and populate with data
    clientdb = custom_import('dbmodel', ['syncserver/tests'])
    clientdb.load_from_uri('sqlite:///test_client.sqlite')
    clientdb.load_db()
    clientdb.create(**{'column1': 'jkl', 'column2': 'mno', 'column3': 'pqr'})

    # start up sync server
    # run normal sync client, then check if log file and  resulting databases make sense
    sync_time = utils.now_utc()
    with open(log_file, 'wt') as fp:
        SyncClient(config_path, sync_time, log_file=fp)

    # create server database and populate with data
    # create client database and populate with data
    # start sync: compute hashes
    # modify client database, testing all of the volatile paths
    # finish sync
    # check if log file and resulting database makes sense
    pass
