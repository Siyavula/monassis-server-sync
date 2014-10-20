from syncserver import record_database, utils
from syncserver.errors import VolatileConflict
import sync_api


TRANSACTIONS_FILENAME = '.sync_transactions'

class SyncClientError(Exception):
    pass


class ConnectionError(SyncClientError):
    pass


class HashError(SyncClientError):
    pass


class SyncClient:
    max_connection_attempts = 4

    def __init__(self, config_path, sync_time, log_file=None):
        self.sync_session = None
        self.log_file = log_file
        # Load config and adjust for client side
        self.log_to_console('Sync time: ' + repr(sync_time))
        self.config_path = config_path
        self.sync_time = sync_time
        self.config = record_database.load_config_from_file(
            config_path,
            'client',
            run_setup=True,
            sync_time=sync_time)
        self.section_names = record_database.get_config_section_names(self.config)
        self.transactions = None

    def log_to_console(self, string):
        if self.log_file is not None:
            self.log_file.write(string + '\n')
            self.log_file.flush()

    def connect_to_server(self):
        connected = False
        attempts = 0
        while not connected and (attempts < self.max_connection_attempts):
            try:
                self.sync_session = sync_api.SyncSession(
                    record_database.get_config_sync_name(self.config),
                    record_database.get_config_sync_url(self.config),
                    record_database.get_config_sync_time(self.config))
                connected = True
            except sync_api.DatabaseLocked:
                import time
                minutes = 2**attempts # Exponential back-off waiting time
                self.log_to_console('Database locked, waiting %i minutes...' % (minutes))
                time.sleep(60 * minutes)
                attempts += 1
        if not connected:
            self.log_to_console('Could not obtain database lock after max (%i) attempts' % (self.max_connection_attempts))
            raise ConnectionError()

    def check_hash_consistency(self):
        client_hash_hash = record_database.get_hash_hash(self.config)
        server_hash_hash = self.sync_session.get_hash_hash()
        if client_hash_hash != server_hash_hash:
            raise HashError("Client and server have inconsistent hash-hashes")

    def compute_actions(self):
        self.log_to_console('Compute hash actions')

        # Update config with server variables
        self.config = record_database.load_config_from_file(
            self.config_path,
            'client',
            run_setup=True,
            sync_time=self.sync_time,
            server_vars=self.sync_session.server_vars)

        # Compute client hash actions to get from old to new hashes
        client_hash_actions = record_database.get_hash_actions(self.config)

        # Find out how hashes have changed on the server
        server_hash_actions = self.sync_session.get_hash_actions(record_database.get_config_sync_time(self.config), record_database.get_config_client_vars(self.config))

        # Write summary to log
        if self.log_file is not None:
            for role, actions in [('client', client_hash_actions), ('server', server_hash_actions)]:
                self.log_to_console(role)
                for section_name in self.section_names:
                    action_count = {'insert': 0, 'update': 0, 'delete': 0}
                    for entry in actions[section_name]:
                        action_count[entry[1][0]] += 1
                    output = '   %-20s -- ' % (section_name)
                    for action in ['insert', 'update', 'delete']:
                        if action_count[action] == 0:
                            output += ' '*(len(action)+8)
                        else:
                            output += '%s: %4i, ' % (action, action_count[action])
                    self.log_to_console(output)

        self.log_to_console('Compute data actions')

        # Figure out how to sync
        self.client_actions = {}
        self.server_actions = {}
        for section_name in self.section_names:
            act = {'client': client_hash_actions[section_name], 'server': server_hash_actions[section_name]}
            for agent in ['client', 'server']:
                act[agent] = dict([(record_database.record_id_to_url_string(record_id), tuple(hash_action)) for record_id, hash_action in act[agent]])
            merge_strategy = record_database.get_config_merge_strategy_for_section(self.config, section_name)
            act['client'], act['server'] = utils.sync_on_strategy(merge_strategy, act['client'], act['server'])
            for agent in ['client', 'server']:
                act[agent] = [(record_database.url_string_to_record_id(record_id), data_action) for record_id, data_action in act[agent].iteritems()]
            self.client_actions[section_name] = act['client']
            self.server_actions[section_name] = act['server']

        # Write summary to log
        if self.log_file is not None:
            for section_name in self.section_names:
                output = '   %-20s -- ' % (section_name)
                for role, actions in [('client', self.client_actions), ('server', self.server_actions)]:
                    action_count = {'insert': 0, 'update': 0, 'delete': 0, 'insert-hash': 0, 'update-hash': 0, 'delete-hash': 0}
                    for record_id, action in actions[section_name]:
                        action_count[action['our-action']] += 1
                    for action in ['insert', 'update', 'delete', 'insert-hash', 'update-hash', 'delete-hash']:
                        if action_count[action] != 0:
                            output += '%s.%s%s: %4i, ' % (role[0], action[0], 'h' if action[-5:] == '-hash' else 't', action_count[action])
                self.log_to_console(output)

    def load_transactions(self):
        if self.transactions is not None:
            raise ValueError("Loading transactions from file while another block is still open")
        from ast import literal_eval
        with open(TRANSACTIONS_FILENAME, 'rt') as fp:
            transactions = [literal_eval(line) for line in fp.read().strip().split('\n')]
        if len(transactions) > 0:
            self.transactions = transactions

    def start_transaction_block(self):
        if self.transactions is not None:
            raise ValueError("Starting a new transaction block while the previous one has not been emptied")
        # Truncate transactions file
        self.transactions = []
        with open(TRANSACTIONS_FILENAME, 'wt') as fp:
            pass

    def add_transaction(self, method, *args, **kwargs):
        if self.transactions is None:
            raise ValueError("Trying to add a transaction without having started a transaction block")
        if (method != 'remote_hash_action') and (method[:method.find('.')] != 'sync_session'):
            self.log_to_console('WARNING: Unrecognised transaction method ' + repr(method))
        self.transactions.append((method, args, kwargs))
        with open(TRANSACTIONS_FILENAME, 'at') as fp:
            fp.write(repr(self.transactions[-1]) + '\n')

    def execute_transaction_block(self):
        if self.transactions is None:
            raise ValueError("Trying to execute a transaction block without having started it")
        while True:
            try:
                method, args, kwargs = self.transactions.pop(0)
            except IndexError:
                break
            else:
                obj = self
                for part in method.split('.'):
                    obj = getattr(obj, part)
                obj(*args, **kwargs)
                with open(TRANSACTIONS_FILENAME, 'rt') as fp:
                    from ast import literal_eval
                    assert literal_eval(fp.readline().strip()) == (method, args, kwargs)
                with open(TRANSACTIONS_FILENAME, 'wt') as fp:
                    for transaction in self.transactions:
                        fp.write(repr(x) + '\n')
        self.transactions = None

    def remote_hash_action(self, action, hash, section_name, record_id):
        if action is not None:
            packed_record_id = record_database.record_id_to_url_string(record_id)
            if action in ['insert-hash', 'update-hash']:
                assert hash is not None
                self.sync_session.put_hash(section_name, packed_record_id, hash)
            else:
                assert action == 'delete-hash'
                self.sync_session.delete_hash(section_name, packed_record_id)

    def local_hash_action(self, action, hash, section_name, record_id):
        if action == 'insert-hash':
            assert hash is not None
            record_database.insert_hash(self.config, section_name, record_id, hash)
        elif action == 'update-hash':
            assert hash is not None
            record_database.update_hash(self.config, section_name, record_id, hash)
        elif action == 'insert-or-update-hash':
            assert hash is not None
            record_database.insert_or_update_hash(self.config, section_name, record_id, hash)
        elif action == 'delete-hash':
            record_database.delete_hash(self.config, section_name, record_id)
        else:
            assert action is None

    def apply_hash_actions(self, do_hash_check=False):
        self.log_to_console('Apply all hash actions')
        total_applied = 0
        for source in [self.client_actions, self.server_actions]:
            for section_name in self.section_names:
                counter = 0
                for record_id, actions in source[section_name]:
                    my_action = actions['our-action']
                    if my_action[-5:] != '-hash':
                        continue
                    self.start_transaction_block()
                    new_hash = actions.get('new-hash')
                    other_action = actions.get('their-action')
                    if source == self.client_actions:
                        client_action = my_action
                        server_action = other_action
                    else:
                        client_action = other_action
                        server_action = my_action
                    self.add_transaction('remote_hash_action', server_action, new_hash, section_name, record_id)
                    self.local_hash_action(client_action, new_hash, section_name, record_id)
                    self.execute_transaction_block()
                    counter += 1
                if counter > 0:
                    total_applied += counter
                    self.log_to_console('   %-20s -- %4i applied' % (section_name, counter))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_local_inserts(self, do_hash_check=False):
        self.log_to_console('Apply local inserts')
        total_applied = 0
        for section_name in self.section_names:
            counter = 0
            for record_id, actions in self.client_actions[section_name]:
                if actions['our-action'] != 'insert':
                    continue
                self.start_transaction_block()
                new_hash = actions['new-hash']
                server_action = actions.get('their-action')
                packed_record_id = record_database.record_id_to_url_string(record_id)
                record_data = self.sync_session.get_record(section_name, packed_record_id)
                self.add_transaction('remote_hash_action', server_action, new_hash, section_name, record_id)
                try:
                    record_database.insert_record(self.config, section_name, record_id, record_data, volatile_hash=new_hash)
                except VolatileConflict:
                    if record_database.get_config_merge_strategy_for_section(self.config, section_name) in ['slave', 'child']:
                        record_database.update_record(self.config, section_name, record_id, record_data)
                # NOTE: Can't just do insert_hash() below since client
                # might do a local insert when the client deleted a
                # record while the server updated it under some sync
                # strategies.
                record_database.insert_or_update_hash(self.config, section_name, record_id, new_hash)
                self.execute_transaction_block()
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied' % (section_name, counter))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_local_inserts_batch(self, do_hash_check=False):
        self.log_to_console('Apply local inserts')
        total_applied = 0
        for section_name in self.section_names:
            self.start_transaction_block()
            # Aggregate actions
            actions_to_apply = [(record_id, actions) for record_id, actions in self.client_actions[section_name] if actions['our-action'] == 'insert']
            # Get records from server
            packed_record_ids = [record_database.record_id_to_url_string(record_id) for record_id, actions in actions_to_apply]
            if len(packed_record_ids) > 0:
                records = self.sync_session.get_records_for_section(section_name, packed_record_ids)
            else:
                records = []
            # Apply actions on server
            server_actions = []
            for i in xrange(len(actions_to_apply)):
                record_id, actions = actions_to_apply[i]
                packed_record_id = packed_record_ids[i]
                new_hash = actions['new-hash']
                server_action = actions.get('their-action')
                if server_action in ['insert-hash', 'update-hash']:
                    assert new_hash is not None
                    server_actions.append({'action': 'put', 'id': packed_record_id, 'hash': new_hash})
                elif server_action == 'delete-hash':
                    server_actions.append({'action': 'delete', 'id': packed_record_id})
                else:
                    assert server_action is None
            if len(server_actions) > 0:
                self.add_transaction('sync_session.put_hashes_for_section', section_name, server_actions)
            # Apply actions on client
            for i in xrange(len(actions_to_apply)):
                record_id, actions = actions_to_apply[i]
                record_data = records[i]
                new_hash = actions['new-hash']
                try:
                    record_database.insert_record(self.config, section_name, record_id, record_data, volatile_hash=new_hash)
                except VolatileConflict:
                    if record_database.get_config_merge_strategy_for_section(self.config, section_name) in ['slave', 'child']:
                        record_database.update_record(self.config, section_name, record_id, record_data)
                # NOTE: Can't just do insert_hash() below since client
                # might do a local insert when the client deleted a
                # record while the server updated it under some sync
                # strategies.
                record_database.insert_or_update_hash(self.config, section_name, record_id, new_hash)
            # Update log
            self.execute_transaction_block()
            count = len(actions_to_apply)
            if count > 0:
                total_applied += count
                self.log_to_console('   %-20s -- %4i applied' % (section_name, count))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_local_updates(self, do_hash_check=False):
        self.log_to_console('Apply local updates')
        total_applied = 0
        for section_name in self.section_names:
            counter = 0
            for record_id, actions in self.client_actions[section_name]:
                if actions['our-action'] != 'update':
                    continue
                self.start_transaction_block()
                old_hash = actions['old-hash']
                new_hash = actions['new-hash']
                server_action = actions.get('their-action')
                packed_record_id = record_database.record_id_to_url_string(record_id)
                record_data = self.sync_session.get_record(section_name, packed_record_id)
                self.add_transaction('remote_hash_action', server_action, new_hash, section_name, record_id)
                try:
                    record_database.update_record(self.config, section_name, record_id, record_data, volatile_hashes=(old_hash, new_hash))
                except VolatileConflict, error:
                    if record_database.get_config_merge_strategy_for_section(self.config, section_name) in ['slave', 'child']:
                        if 'deleted' in error.message:
                            record_database.insert_record(self.config, section_name, record_id, record_data)
                        else:
                            assert 'updated' in error.message
                            record_database.update_record(self.config, section_name, record_id, record_data)
                record_database.insert_or_update_hash(self.config, section_name, record_id, new_hash)
                self.execute_transaction_block()
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied' % (section_name, counter))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_local_updates_batch(self, do_hash_check=False):
        self.log_to_console('Apply local updates')
        total_applied = 0
        for section_name in self.section_names:
            self.start_transaction_block()
            # Aggregate actions
            actions_to_apply = [(record_id, actions) for record_id, actions in self.client_actions[section_name] if actions['our-action'] == 'update']
            # Get records from server
            packed_record_ids = [record_database.record_id_to_url_string(record_id) for record_id, actions in actions_to_apply]
            if len(packed_record_ids) > 0:
                records = self.sync_session.get_records_for_section(section_name, packed_record_ids)
            else:
                records = []
            # Apply actions on server
            server_actions = []
            for i in xrange(len(actions_to_apply)):
                record_id, actions = actions_to_apply[i]
                packed_record_id = packed_record_ids[i]
                new_hash = actions['new-hash']
                server_action = actions.get('their-action')
                if server_action in ['insert-hash', 'update-hash']:
                    assert new_hash is not None
                    server_actions.append({'action': 'put', 'id': packed_record_id, 'hash': new_hash})
                elif server_action == 'delete-hash':
                    server_actions.append({'action': 'delete', 'id': packed_record_id})
                else:
                    assert server_action is None
            if len(server_actions) > 0:
                self.add_transaction('sync_session.put_hashes_for_section', section_name, server_actions)
            # Apply actions on client
            for i in xrange(len(actions_to_apply)):
                record_id, actions = actions_to_apply[i]
                record_data = records[i]
                old_hash = actions['old-hash']
                new_hash = actions['new-hash']
                try:
                    record_database.update_record(self.config, section_name, record_id, record_data, volatile_hashes=(old_hash, new_hash))
                except VolatileConflict, error:
                    if record_database.get_config_merge_strategy_for_section(self.config, section_name) in ['slave', 'child']:
                        if 'deleted' in error.message:
                            record_database.insert_record(self.config, section_name, record_id, record_data)
                        else:
                            assert 'updated' in error.message
                            record_database.update_record(self.config, section_name, record_id, record_data)
                record_database.insert_or_update_hash(self.config, section_name, record_id, new_hash)
            # Update log
            self.execute_transaction_block()
            count = len(actions_to_apply)
            if count > 0:
                total_applied += count
                self.log_to_console('   %-20s -- %4i applied' % (section_name, count))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_local_deletes(self, do_hash_check=False):
        self.log_to_console('Apply local deletes')
        total_applied = 0
        for section_name in reversed(self.section_names):
            counter = 0
            for record_id, actions in self.client_actions[section_name]:
                if actions['our-action'] != 'delete':
                    continue
                self.start_transaction_block()
                old_hash = actions['old-hash']
                server_action = actions.get('their-action')
                self.add_transaction('remote_hash_action', server_action, None, section_name, record_id)
                try:
                    record_database.delete_record(self.config, section_name, record_id, volatile_hash=old_hash)
                except VolatileConflict:
                    if record_database.get_config_merge_strategy_for_section(self.config, section_name) in ['slave', 'child']:
                        record_database.delete_record(self.config, section_name, record_id)
                record_database.delete_hash(self.config, section_name, record_id)
                self.execute_transaction_block()
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied' % (section_name, counter))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_local_deletes_batch(self, do_hash_check=False):
        self.log_to_console('Apply local deletes')
        total_applied = 0
        for section_name in reversed(self.section_names):
            self.start_transaction_block()
            # Aggregate actions
            actions_to_apply = [(record_id, actions) for record_id, actions in self.client_actions[section_name] if actions['our-action'] == 'delete']
            # Apply actions on server
            server_actions = []
            for record_id, actions in actions_to_apply:
                server_action = actions.get('their-action')
                if server_action is not None:
                    assert server_action == 'delete-hash'
                    packed_record_id = record_database.record_id_to_url_string(record_id)
                    server_actions.append({'action': 'delete', 'id': packed_record_id})
            if len(server_actions) > 0:
                self.add_transaction('sync_session.put_hashes_for_section', section_name, server_actions)
            # Apply actions on client
            for record_id, actions in actions_to_apply:
                old_hash = actions['old-hash']
                try:
                    record_database.delete_record(self.config, section_name, record_id, volatile_hash=old_hash)
                except VolatileConflict:
                    if record_database.get_config_merge_strategy_for_section(self.config, section_name) in ['slave', 'child']:
                        record_database.delete_record(self.config, section_name, record_id)
                record_database.delete_hash(self.config, section_name, record_id)
            # Update log
            self.execute_transaction_block()
            count = len(actions_to_apply)
            if count > 0:
                total_applied += count
                self.log_to_console('   %-20s -- %4i applied' % (section_name, count))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_remote_inserts(self, do_hash_check=False):
        self.log_to_console('Apply remote insert')
        total_applied = 0
        for section_name in self.section_names:
            counter = 0
            for record_id, actions in self.server_actions[section_name]:
                if actions['our-action'] != 'insert':
                    continue
                self.start_transaction_block()
                new_hash = actions['new-hash']
                client_action = actions.get('their-action')
                record_data, volatile_hash = record_database.get_record_and_compute_hash(self.config, section_name, record_id)
                packed_record_id = record_database.record_id_to_url_string(record_id)
                if volatile_hash is None:
                    # Record got deleted locally before we could
                    # insert it remotely. Do nothing remotely since it
                    # doesn't exist there. Delete local hash if
                    # necessary. Delete remote hash if necessary.
                    if client_action != 'insert-hash':
                        record_database.delete_hash(self.config, section_name, record_id)
                    self.add_transaction('remote_hash_action', 'delete-hash', None, section_name, record_id)
                else:
                    # If record got modified locally before we could
                    # insert it remotely, just send the new record and
                    # update the local hash from the new record.
                    self.add_transaction('sync_session.put_record_and_hash', section_name, packed_record_id, record_data, volatile_hash)
                    if (new_hash != volatile_hash) and (client_action is None):
                        client_action = 'update-hash'
                    self.local_hash_action(client_action, volatile_hash, section_name, record_id)
                self.execute_transaction_block()
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied' % (section_name, counter))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_remote_inserts_batch(self, do_hash_check=False):
        self.log_to_console('Apply remote insert')
        total_applied = 0
        for section_name in self.section_names:
            # Aggregate client and server actions
            self.start_transaction_block()
            actions_to_apply = [(record_id, actions) for record_id, actions in self.server_actions[section_name] if actions['our-action'] == 'insert']
            client_actions = []
            server_actions = []
            for record_id, actions in actions_to_apply:
                new_hash = actions['new-hash']
                client_action = actions.get('their-action')
                record_data, volatile_hash = record_database.get_record_and_compute_hash(self.config, section_name, record_id)
                packed_record_id = record_database.record_id_to_url_string(record_id)
                if volatile_hash is None:
                    # Record got deleted locally before we could
                    # insert it remotely. Do nothing remotely since it
                    # doesn't exist there. Delete local hash if
                    # necessary. Delete remote hash if necessary.
                    if client_action != 'insert-hash':
                        client_actions.append({'action': 'delete-hash', 'id': record_id})
                    server_actions.append({'action': 'delete-hash', 'id': packed_record_id})
                else:
                    # If record got modified locally before we could
                    # insert it remotely, just send the new record and
                    # update the local hash from the new record.
                    server_actions.append({'action': 'put', 'id': packed_record_id, 'record': record_data, 'hash': volatile_hash})
                    if (new_hash != volatile_hash) and (client_action is None):
                        client_action = 'update-hash'
                    if client_action is not None:
                        client_actions.append({'action': client_action, 'id': record_id, 'hash': volatile_hash})
            # Apply server actions
            if len(server_actions) > 0:
                self.add_transaction('sync_session.put_records_and_hashes_for_section', section_name, server_actions)
            # Apply client actions (of which all are hash actions)
            for entry in client_actions:
                self.local_hash_action(entry['action'], entry.get('hash'), section_name, entry['id'])
            # Update log
            self.execute_transaction_block()
            count = len(actions_to_apply)
            if count > 0:
                total_applied += count
                self.log_to_console('   %-20s -- %4i applied' % (section_name, count))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_remote_updates(self, do_hash_check=False):
        self.log_to_console('Apply remote updates')
        total_applied = 0
        for section_name in self.section_names:
            counter = 0
            for record_id, actions in self.server_actions[section_name]:
                if actions['our-action'] != 'update':
                    continue
                self.start_transaction_block()
                new_hash = actions['new-hash']
                client_action = actions.get('their-action')
                record_data, volatile_hash = record_database.get_record_and_compute_hash(self.config, section_name, record_id)
                packed_record_id = record_database.record_id_to_url_string(record_id)
                if volatile_hash is None:
                    # Record got deleted locally before we could update it
                    # remotely. Delete it remotely and from the local hash
                    # table.
                    self.add_transaction('sync_session.delete_record_and_hash', section_name, packed_record_id)
                    record_database.delete_hash(self.config, section_name, record_id)
                else:
                    # If record got modified locally before we could
                    # update it remotely, just send the new record and
                    # update the local hash from the new record.
                    self.add_transaction('sync_session.put_record_and_hash', section_name, packed_record_id, record_data, volatile_hash)
                    if (new_hash != volatile_hash) and (client_action is None):
                        client_action = 'update-hash'
                    self.local_hash_action(client_action, volatile_hash, section_name, record_id)
                self.execute_transaction_block()
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied' % (section_name, counter))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_remote_updates_batch(self, do_hash_check=False):
        self.log_to_console('Apply remote updates')
        total_applied = 0
        for section_name in self.section_names:
            # Aggregate client and server actions
            self.start_transaction_block()
            actions_to_apply = [(record_id, actions) for record_id, actions in self.server_actions[section_name] if actions['our-action'] == 'update']
            client_actions = []
            server_actions = []
            for record_id, actions in actions_to_apply:
                new_hash = actions['new-hash']
                client_action = actions.get('their-action')
                record_data, volatile_hash = record_database.get_record_and_compute_hash(self.config, section_name, record_id)
                packed_record_id = record_database.record_id_to_url_string(record_id)
                if volatile_hash is None:
                    # Record got deleted locally before we could update it
                    # remotely. Delete it remotely and from the local hash
                    # table.
                    server_actions.append({'action': 'delete', 'id': packed_record_id})
                    client_actions.append({'action': 'delete-hash', 'id': record_id})
                else:
                    # If record got modified locally before we could
                    # update it remotely, just send the new record and
                    # update the local hash from the new record.
                    server_actions.append({'action': 'put', 'id': packed_record_id, 'record': record_data, 'hash': volatile_hash})
                    if (new_hash != volatile_hash) and (client_action is None):
                        client_action = 'update-hash'
                    if client_action is not None:
                        client_actions.append({'action': client_action, 'id': record_id, 'hash': volatile_hash})
            # Apply server actions
            if len(server_actions) > 0:
                self.add_transaction('sync_session.put_records_and_hashes_for_section', section_name, server_actions)
            # Apply client actions (of which all are hash actions)
            for entry in client_actions:
                self.local_hash_action(entry['action'], entry.get('hash'), section_name, entry['id'])
            # Update log
            self.execute_transaction_block()
            count = len(actions_to_apply)
            if count > 0:
                total_applied += count
                self.log_to_console('   %-20s -- %4i applied' % (section_name, count))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_remote_deletes(self, do_hash_check=False):
        self.log_to_console('Apply remote deletes')
        total_applied = 0
        for section_name in reversed(self.section_names):
            counter = 0
            for record_id, actions in self.server_actions[section_name]:
                if actions['our-action'] != 'delete':
                    continue
                self.start_transaction_block()
                client_action = actions.get('their-action')
                record_data, volatile_hash = record_database.get_record_and_compute_hash(self.config, section_name, record_id)
                packed_record_id = record_database.record_id_to_url_string(record_id)
                if volatile_hash is None:
                    self.add_transaction('sync_session.delete_record_and_hash', section_name, packed_record_id)
                    self.local_hash_action(client_action, None, section_name, record_id)
                else:
                    # Record got inserted or re-inserted. Update
                    # remotely rather than deleting and insert or
                    # update the local hash from the new record.
                    self.add_transaction('sync_session.put_record_and_hash', section_name, packed_record_id, record_data, volatile_hash)
                    self.local_hash_action('insert-or-update-hash', volatile_hash, section_name, record_id)
                self.execute_transaction_block()
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied' % (section_name, counter))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()

    def apply_remote_deletes_batch(self, do_hash_check=False):
        self.log_to_console('Apply remote deletes')
        total_applied = 0
        for section_name in reversed(self.section_names):
            # Aggregate client and server actions
            self.start_transaction_block()
            actions_to_apply = [(record_id, actions) for record_id, actions in self.server_actions[section_name] if actions['our-action'] == 'delete']
            client_actions = []
            server_actions = []
            for record_id, actions in actions_to_apply:
                client_action = actions.get('their-action')
                record_data, volatile_hash = record_database.get_record_and_compute_hash(self.config, section_name, record_id)
                packed_record_id = record_database.record_id_to_url_string(record_id)
                if volatile_hash is None:
                    server_actions.append({'action': 'delete', 'id': packed_record_id})
                    if client_action is not None:
                        assert client_action == 'delete-hash'
                        client_actions.append({'action': client_action, 'id': record_id})
                else:
                    # Record got inserted or re-inserted. Update
                    # remotely rather than deleting and insert or
                    # update the local hash from the new record.
                    server_actions.append({'action': 'put', 'id': packed_record_id, 'record': record_data, 'hash': volatile_hash})
                    client_actions.append({'action': 'insert-or-update-hash', 'id': record_id, 'hash': volatile_hash})
            # Apply server actions
            if len(server_actions) > 0:
                self.add_transaction('sync_session.put_records_and_hashes_for_section', section_name, server_actions)
            # Apply client actions (of which all are hash actions)
            for entry in client_actions:
                self.local_hash_action(entry['action'], entry.get('hash'), section_name, entry['id'])
            # Update log
            self.execute_transaction_block()
            count = len(actions_to_apply)
            if count > 0:
                total_applied += count
                self.log_to_console('   %-20s -- %4i applied' % (section_name, count))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()
