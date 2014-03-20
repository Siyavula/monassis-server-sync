from syncserver import record_database, utils
from syncserver.errors import VolatileConflict
import sync_api


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
        self.config = record_database.load_config_from_file(config_path, 'client', run_setup=True, sync_time=sync_time)
        self.section_names = record_database.get_config_section_names(self.config)


    def log_to_console(self, string):
        if self.log_file is not None:
            self.log_file.write(string + '\n')
            self.log_file.flush()


    def connect_to_server(self):
        connected = False
        attempts = 0
        while not connected and (attempts < self.max_connection_attempts):
            try:
                self.sync_session = sync_api.SyncSession(record_database.get_config_sync_name(self.config), record_database.get_config_sync_url(self.config))
                connected = True
            except sync_api.DatabaseLocked:
                import time
                minutes = 2**attempts # Exponential back-off waiting time
                self.log_to_console('Database locked, waiting %i minutes...'%(minutes))
                time.sleep(60 * minutes)
                attempts += 1
        if not connected:
            self.log_to_console('Could not obtain database lock after max (%i) attempts'%(self.max_connection_attempts))
            raise ConnectionError


    def check_hash_consistency(self):
        client_hash_hash = record_database.get_hash_hash(self.config)
        server_hash_hash = self.sync_session.get_hash_hash()
        if client_hash_hash != server_hash_hash:
            raise HashError, "Client and server have inconsistent hash-hashes"


    def compute_actions(self):
        self.log_to_console('Compute hash actions')

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
                    output = '   %-20s -- '%(section_name)
                    for action in ['insert', 'update', 'delete']:
                        if action_count[action] == 0:
                            output += ' '*(len(action)+8)
                        else:
                            output += '%s: %4i, '%(action, action_count[action])
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
                output = '   %-20s -- '%(section_name)
                for role, actions in [('client', self.client_actions), ('server', self.server_actions)]:
                    action_count = {'insert': 0, 'update': 0, 'delete': 0, 'insert-hash': 0, 'update-hash': 0, 'delete-hash': 0}
                    for record_id, action in actions[section_name]:
                        action_count[action['our-action']] += 1
                    for action in ['insert', 'update', 'delete', 'insert-hash', 'update-hash', 'delete-hash']:
                        if action_count[action] != 0:
                            output += '%s.%s%s: %4i, '%(role[0], action[0], 'h' if action[-5:] == '-hash' else 't', action_count[action])
                self.log_to_console(output)


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
                    new_hash = actions.get('new-hash')
                    other_action = actions.get('their-action')
                    if source == self.client_actions:
                        client_action = my_action
                        server_action = other_action
                    else:
                        client_action = other_action
                        server_action = my_action
                    self.remote_hash_action(server_action, new_hash, section_name, record_id)
                    self.local_hash_action(client_action, new_hash, section_name, record_id)
                    counter += 1
                if counter > 0:
                    total_applied += counter
                    self.log_to_console('   %-20s -- %4i applied'%(section_name, counter))

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
                new_hash = actions['new-hash']
                server_action = actions.get('their-action')
                packed_record_id = record_database.record_id_to_url_string(record_id)
                record_data = self.sync_session.get_record(section_name, packed_record_id)
                self.remote_hash_action(server_action, new_hash, section_name, record_id)
                try:
                    record_database.insert_record(self.config, section_name, record_id, record_data, volatile_hash=new_hash)
                except VolatileConflict:
                    if record_database.get_config_merge_strategy_for_section(self.config, section_name) in ['slave', 'child']:
                        record_database.update_record(self.config, section_name, record_id, record_data)
                record_database.insert_hash(self.config, section_name, record_id, new_hash)
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied'%(section_name, counter))

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
                old_hash = actions['old-hash']
                new_hash = actions['new-hash']
                server_action = actions.get('their-action')
                packed_record_id = record_database.record_id_to_url_string(record_id)
                record_data = self.sync_session.get_record(section_name, packed_record_id)
                self.remote_hash_action(server_action, new_hash, section_name, record_id)
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
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied'%(section_name, counter))

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
                old_hash = actions['old-hash']
                server_action = actions.get('their-action')
                self.remote_hash_action(server_action, None, section_name, record_id)
                try:
                    record_database.delete_record(self.config, section_name, record_id, volatile_hash=old_hash)
                except VolatileConflict:
                    if record_database.get_config_merge_strategy_for_section(self.config, section_name) in ['slave', 'child']:
                        record_database.delete_record(self.config, section_name, record_id)
                record_database.delete_hash(self.config, section_name, record_id)
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied'%(section_name, counter))

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
                new_hash = actions['new-hash']
                client_action = actions.get('their-action')
                record_data, volatile_hash = record_database.get_record_and_compute_hash(self.config, section_name, record_id)
                packed_record_id = record_database.record_id_to_url_string(record_id)
                if volatile_hash is None:
                    # Record got deleted locally before we could insert it
                    # remotely. Do nothing remotely since it doesn't exist
                    # there. Delete local hash if necessary.
                    if client_action != 'insert-hash':
                        record_database.delete_hash(self.config, section_name, record_id)
                else:
                    # If record got modified locally before we could
                    # insert it remotely, just sent the new record and
                    # update the local hash from the new record.
                    self.sync_session.put_record_and_hash(section_name, packed_record_id, record_data, volatile_hash)
                    if (new_hash != volatile_hash) and (client_action is None):
                        client_action = 'update-hash'
                    self.local_hash_action(client_action, volatile_hash, section_name, record_id)
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied'%(section_name, counter))

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
                new_hash = actions['new-hash']
                client_action = actions.get('their-action')
                record_data, volatile_hash = record_database.get_record_and_compute_hash(self.config, section_name, record_id)
                packed_record_id = record_database.record_id_to_url_string(record_id)
                if volatile_hash is None:
                    # Record got deleted locally before we could update it
                    # remotely. Delete it remotely and from the local hash
                    # table.
                    self.sync_session.delete_record_and_hash(section_name, packed_record_id)
                    record_database.delete_hash(self.config, section_name, record_id)
                else:
                    # If record got modified locally before we could
                    # update it remotely, just sent the new record and
                    # update the local hash from the new record.
                    self.sync_session.put_record_and_hash(section_name, packed_record_id, record_data, volatile_hash)
                    if (new_hash != volatile_hash) and (client_action is None):
                        client_action = 'update-hash'
                    self.local_hash_action(client_action, volatile_hash, section_name, record_id)
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied'%(section_name, counter))

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
                client_action = actions.get('their-action')
                packed_record_id = record_database.record_id_to_url_string(record_id)
                self.sync_session.delete_record_and_hash(section_name, packed_record_id)
                self.local_hash_action(client_action, None, section_name, record_id)
                counter += 1
            if counter > 0:
                total_applied += counter
                self.log_to_console('   %-20s -- %4i applied'%(section_name, counter))

        if do_hash_check and (total_applied > 0):
            # Sanity check our updated hashes
            self.check_hash_consistency()
