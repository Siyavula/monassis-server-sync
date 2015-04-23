import datetime
from dateutil.parser import parse
from dateutil.tz import tzutc


def parse_iso8601(s, field=None):
    """
    Parse a string, possibly None, from ISO8601
    into a UTC-based datetime instance.

    If the value is None, None is returned.

    If the value is bad, a ValueError with a user-friendly
    error is raised, including the field name +field+ if given.
    """
    if not s:
        return None

    try:
        dt = parse(s)
        return dt.astimezone(tzutc())
    except ValueError:
        if field:
            raise ValueError("The ISO8601 timestamp '%s' for %s is not valid" % (s, field))
        else:
            raise ValueError("The ISO8601 timestamp '%s' is not valid" % s)


def now_utc():
    """
    Return now in UTC, with second precision.
    """
    return datetime.datetime.now(tzutc()).replace(microsecond=0)


def force_utc(dt):
    """
    If the given datetime +dt+ does not have a timezone associated with it,
    force it to be UTC.
    """
    if dt and not dt.tzinfo:
        return dt.replace(tzinfo=tzutc())
    else:
        return dt


def _sync_master_slave_or_parent_child(master_hash_actions, slave_hash_actions, is_master_slave):
    '''
    hash_actions: { record_id: ('insert', new_hash) or ('update', old_hash, new_hash) or
                               ('delete', old_hash) }
    > { record_id: {'our-action', 'their-action', 'old-hash', 'new-hash'} }
    '''
    master_action_idents = set(master_hash_actions.keys())
    slave_action_idents = set(slave_hash_actions.keys())
    master_data_actions = {}
    slave_data_actions = {}

    for ident in master_action_idents - slave_action_idents:
        # Add things that master/parent did, but slave/child did not
        # do to slave/child's list of actions
        master_action = master_hash_actions[ident]
        entry = {
            'our-action': master_action[0],
            'their-action': master_action[0] + '-hash',
        }
        if master_action[0] == 'insert':
            entry['new-hash'] = master_action[1]
        elif master_action[0] == 'update':
            entry['old-hash'] = master_action[1]
            entry['new-hash'] = master_action[2]
        else:
            assert master_action[0] == 'delete'
            entry['old-hash'] = master_action[1]
        slave_data_actions[ident] = entry

    # This is the only difference between master-slave and parent-
    # child merges. A slave has to reverse its actions, while a
    # child's actions get applied to the parent.
    if is_master_slave:
        for ident in slave_action_idents - master_action_idents:
            slave_action = slave_hash_actions[ident]
            entry = {'our-action': {'insert': 'delete', 'update': 'update', 'delete': 'insert'}[
                slave_action[0]]}
            if slave_action[0] == 'insert':          # Note: hash checking for volatile
                entry['old-hash'] = slave_action[1]  # slaves should really not be
            elif slave_action[0] == 'update':        # necessary since it still needs
                entry['old-hash'] = slave_action[2]  # to conform to the master's state.
                entry['new-hash'] = slave_action[1]
            else:
                assert slave_action[0] == 'delete'
                entry['new-hash'] = slave_action[1]
            slave_data_actions[ident] = entry
    else:
        for ident in slave_action_idents - master_action_idents:
            slave_action = slave_hash_actions[ident]
            entry = {
                'our-action': slave_action[0],
                'their-action': slave_action[0] + '-hash',
            }
            if slave_action[0] == 'insert':
                entry['new-hash'] = slave_action[1]
            elif slave_action[0] == 'update':
                entry['old-hash'] = slave_action[1]
                entry['new-hash'] = slave_action[2]
            else:
                assert slave_action[0] == 'delete'
                entry['old-hash'] = slave_action[1]
            master_data_actions[ident] = entry

    # When there are conflicting actions on the same ident, the
    # master/parent always wins.
    for ident in master_action_idents.intersection(slave_action_idents):
        master_action = master_hash_actions[ident]
        slave_action = slave_hash_actions[ident]
        if master_action != slave_action:
            action = {
                'insert': {'insert': 'update'},
                'update': {'update': 'update', 'delete': 'insert'},
                'delete': {'update': 'delete'},
            }[master_action[0]].get(slave_action[0])
            assert action is not None, (
                "Weird inconsistency between master and slave actions (ident: %s, master: %s, "
                "slave: %s)" % (
                    repr(ident), repr(master_hash_actions[ident], slave_hash_actions[ident])))
            entry = {
                'our-action': action,
                'their-action': master_action[0] + '-hash',
            }

            if master_action[0] == 'insert':
                entry['new-hash'] = master_action[1]
            elif master_action[0] == 'update':
                entry['new-hash'] = master_action[2]
            else:
                assert master_action[0] == 'delete'

            if slave_action[0] == 'insert':
                entry['old-hash'] = slave_action[1]
            elif slave_action[0] == 'update':
                entry['old-hash'] = slave_action[2]
            else:
                assert slave_action[0] == 'delete'

            slave_data_actions[ident] = entry
        else:
            entry = {
                'our-action': master_action[0] + '-hash',
                'their-action': master_action[0] + '-hash',
            }
            if master_action[0] == 'insert':
                entry['new-hash'] = master_action[1]
            elif master_action[0] == 'update':
                entry['new-hash'] = master_action[2]
            else:
                assert master_action[0] == 'delete'
            master_data_actions[ident] = entry

    return master_data_actions, slave_data_actions


def sync_master_slave(master_hash_actions, slave_hash_actions):
    return _sync_master_slave_or_parent_child(
        master_hash_actions, slave_hash_actions, is_master_slave=True)


def sync_parent_child(parent_hash_actions, child_hash_actions):
    return _sync_master_slave_or_parent_child(
        parent_hash_actions, child_hash_actions, is_master_slave=False)


def sync_on_strategy(merge_strategy, our_hash_actions, their_hash_actions):
    if merge_strategy == 'master':
        our_data_actions, their_data_actions = sync_master_slave(
            our_hash_actions, their_hash_actions)
    elif merge_strategy == 'slave':
        their_data_actions, our_data_actions = sync_master_slave(
            their_hash_actions, our_hash_actions)
    elif merge_strategy == 'parent':
        our_data_actions, their_data_actions = sync_parent_child(
            our_hash_actions, their_hash_actions)
    elif merge_strategy == 'child':
        their_data_actions, our_data_actions = sync_parent_child(
            their_hash_actions, our_hash_actions)
    else:
        ValueError, "Unknown merge strategy: %s" % (repr(merge_strategy))
    return our_data_actions, their_data_actions
