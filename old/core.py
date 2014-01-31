# encoding: utf-8
from __future__ import division
from uuid import UUID


def get_hashes_from_cache(filename):
    try:
        fp = open(filename, 'rt')
    except IOError:
        hashes = {}
    else:
        hashes = eval(fp.read())
        fp.close()
    return hashes


def hash_hash_structure(struct):
    import hashlib
    return hashlib.md5(repr(sorted([((x.encode('utf-8') if isinstance(x, basestring) else x), sorted([(y.encode('utf-8') if isinstance(y, basestring) else tuple([entry.encode('utf-8') if isinstance(entry, basestring) else entry for entry in y]) if isinstance(y, tuple) else y, z.encode('utf-8') if isinstance(z, basestring) else z) for y, z in subDict.items()])) for x, subDict in struct.items()]))).hexdigest()


def struct_to_json(struct):
    if isinstance(struct, dict):
        raise TypeError, "Can not automatically convert dict"
    elif isinstance(struct, list) or isinstance(struct, tuple):
        return [struct_to_json(x) for x in struct]
    elif isinstance(struct, UUID):
        return repr(struct)
    else:
        return struct


def json_to_struct(json):
    if isinstance(json, list):
        return [json_to_struct(x) for x in json]
    elif isinstance(json, basestring) and (json[:5] == 'UUID('):
        return eval(json)
    else:
        return json


def actions_to_json(actions):
    # Modifies in place and returns the input list
    for sectionName, sectionData in actions.iteritems():
        for action in 'insert', 'update':
            sectionData[action] = struct_to_json(sectionData[action].items())
        sectionData['delete'] = struct_to_json(sectionData['delete'])
    return actions


def actions_from_json(actions):
    # Modifies in place and returns the input list
    for sectionName, sectionData in actions.iteritems():
        for action in 'insert', 'update':
            sectionData[action] = dict([(tuple(key), value) for key, value in json_to_struct(sectionData[action])])
        sectionData['delete'] = [tuple(key) for key in json_to_struct(sectionData['delete'])]
    return actions
