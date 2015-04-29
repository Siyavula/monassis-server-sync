import cPickle
import sys

from syncserver.client import SyncClient
from syncserver import utils

# Load config
config_path = sys.argv[1]
sync_time = utils.now_utc()
sync_client = SyncClient(config_path, sync_time, log_file=sys.stdout)

# Connect to server
sync_client.connect_to_server()

# Check database consistency using hash_hash
sync_client.check_hash_consistency()

# Read state from file
sync_client.log_to_console('Reading state from file')
with open('state.pickle', 'rb') as fp:
    state = cPickle.load(fp)

sync_client.client_actions = state['client_actions']
sync_client.server_actions = state['server_actions']

# CLIENT ACTIONS
# {'records': [
#     (
#         ('5',),
#         {
#             'old-hash': u'2ca2c44405b4822353fb1e7bd2c8cea2',
#             'our-action': 'update',
#             'new-hash': u'ecf6bf0f43e7c06d6ed38384f0f17b5d'}),
#     (
#         ('14',), {
#             'old-hash': u'be3939cbe782002a7870c25d492922b3',
#             'their-action': u'update-hash',
#             'our-action': 'update',
#             'new-hash': u'1f614ed8473bfb86b36fb506a917b9f6'}),
#     (
#         ('7',), {
#             'old-hash': u'711d14ace2ff5c6f8d67be57ff0f375c',
#             'their-action': u'update-hash',
#             'our-action': u'update',
#             'new-hash': u'182fa6753e68b1beb6a1162e6ab402c9'}),
#     (
#         ('6',), {
#             'old-hash': u'895dea6a73cc5dd4515b65449d8ae78e',
#             'our-action': 'update',
#             'new-hash': u'f3cb440b2fae1ac3a0c56e7aa4a06bc4'}),
#     (
#         ('10',), {
#             'old-hash': u'ddcf2d042fb12d69a6aa025091863079',
#             'their-action': u'update-hash',
#             'our-action': u'update',
#             'new-hash': u'f044433068ac279e50ebb5b3a835fad9'})]}
# SERVER ACTIONS
# {'records': [
#     (
#         ('4',), {
#             'their-action': u'update-hash',
#             'our-action': u'update-hash',
#             'new-hash': u'2f019ad1aa9818c34561cff03685b4d2'})]}

# Apply local and remote sync actions
for method in [
        sync_client.apply_hash_actions, sync_client.apply_local_inserts_batch,
        sync_client.apply_local_updates_batch, sync_client.apply_local_deletes_batch,
        sync_client.apply_remote_inserts_batch, sync_client.apply_remote_updates_batch,
        sync_client.apply_remote_deletes_batch]:
    method(do_hash_check=True)

sync_client.log_to_console('DONE')
