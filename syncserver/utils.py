from datetime import *

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
    return datetime.now(tzutc()).replace(microsecond=0)


def force_utc(dt):
    """
    If the given datetime +dt+ does not have a timezone associated with it,
    force it to be UTC.
    """
    if dt and not dt.tzinfo:
        return dt.replace(tzinfo=tzutc())
    else:
        return dt


def compute_hash_actions(old_hash_hierarchy, new_hash_hierarchy):
    '''
    Compute the hash actions to be applied to get from old to new
    hashes.
    > {section: {'insert': {ident: hash}, 'update': {ident: hash}, 'delete': [ident]}}
    '''
    hash_actions = {}
    sections = set(old_hash_hierarchy.keys() + new_hash_hierarchy.keys())
    for section in sections:
        old_dict = old_hash_hierarchy.get(section, {})
        old_keys = set(old_dict.keys())
        new_dict = new_hash_hierarchy.get(section, {})
        new_keys = set(new_dict.keys())
        hash_actions[section] = {
            'insert': dict([(ident, new_dict[ident]) for ident in new_keys - old_keys]),
            'update': dict([(ident, new_dict[ident]) for ident in new_keys.intersection(old_keys) if new_dict[ident] != old_dict[ident]]),
            'delete': list(old_keys - new_keys),
        }
