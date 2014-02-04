import datetime
from dateutil.parser import parse
from dateutil.tz import tzutc
from uuid import UUID


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


def __sync_master_slave_or_parent_child(master_hash_actions, slave_hash_actions, is_master_slave):
    master_action_idents = set(master_hash_actions.keys())
    slave_action_idents = set(slave_hash_actions.keys())
    master_data_actions = {} # { ident: (my_action, [hash,] [other_action, [hash]]) }
    slave_data_actions = {}

    for ident in master_action_idents - slave_action_idents:
        master_action = master_hash_actions[ident]
        entry = {
            'my-action': master_action[0],
            'other-action': master_action[0] + '-hash',
        }
        if len(master_action) > 1:
            entry['hash'] = master_action[1]
        slave_data_actions[ident] = entry

    # This is the only difference between master-slave and
    # parent-child merges. A slave has to reverse its actions, while a
    # child's actions get applied to the parent.
    if is_master_slave:
        for ident in slave_action_idents - master_action_idents:
            slave_action = slave_hash_actions[ident]
            entry = {'my-action': {'insert': 'delete', 'update': 'update', 'delete': 'insert'}[slave_action[0]]}
            if len(slave_action) > 1:
                entry['hash'] = slave_action[1]
            slave_data_actions[ident] = entry
    else:
        for ident in slave_action_idents - master_action_idents:
            slave_action = slave_hash_actions[ident]
            entry = {
                'my-action': slave_action[0],
                'other-action': slave_action[0] + '-hash',
            }
            if len(slave_action) > 1:
                entry['hash'] = slave_action[1]
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
            assert action is not None, "Weird inconsistency between master and slave actions (ident: %s, master: %s, slave: %s)"%(repr(ident), repr(master_hash_actions[ident], slave_hash_actions[ident]))
            entry = {
                'my-action': action,
                'other-action': master_action[0] + '-hash',
            }
            if len(master_action) > 1:
                entry['hash'] = master_action[1]
            slave_data_actions[ident] = entry
        else:
            entry = {
                'my-action': master_action[0] + '-hash',
                'other-action': master_action[0] + '-hash',
            }
            if len(master_action) > 1:
                entry['hash'] = master_action[1]
            master_data_actions[ident] = entry

    return master_data_actions, slave_data_actions


def sync_master_slave(master_hash_actions, slave_hash_actions):
    return __sync_master_slave_or_parent_child(master_hash_actions, slave_hash_actions, is_master_slave=True)


def sync_parent_child(parent_hash_actions, child_hash_actions):
    return __sync_master_slave_or_parent_child(parent_hash_actions, child_hash_actions, is_master_slave=False)


def struct_to_json(struct):
    if isinstance(struct, dict):
        raise TypeError, "Cannot automatically convert dict"
    elif isinstance(struct, list) or isinstance(struct, tuple):
        return [struct_to_json(x) for x in struct]
    elif isinstance(struct, UUID):
        return repr(struct)
    elif isinstance(struct, datetime.datetime):
        return struct.isoformat()
    else:
        return struct


def json_to_struct(json):
    if isinstance(json, list):
        return [json_to_struct(x) for x in json]
    elif isinstance(json, basestring) and (json[:5] == 'UUID('):
        return eval(json)

    try:
        return datetime.datetime.strptime(json, '%Y-%m-%dT%H:%M:%S.%f')
    except Exception:
        pass

    return json


def actions_to_json(actions):
    # Modifies in place and returns the input list
    for section_name, section_data in actions.iteritems():
        actions[section_name] = struct_to_json(section_data.items())
    return actions


def actions_from_json(actions):
    # Modifies in place and returns the input list
    for section_name, section_data in actions.iteritems():
        actions[section_name] = dict([(tuple(key), tuple(value)) for key, value in json_to_struct(section_data)])
    return actions
