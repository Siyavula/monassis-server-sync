import sys
from syncserver.client import SyncClient, ConnectionError, HashError
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
import cPickle
with open('state.pickle', 'rb') as fp:
    state = cPickle.load(fp)
sync_client.client_actions = state['client_actions']
sync_client.server_actions = state['server_actions']

# Apply local and remote sync actions
for method in [sync_client.apply_hash_actions, sync_client.apply_local_inserts_batch, sync_client.apply_local_updates, sync_client.apply_local_deletes, sync_client.apply_remote_inserts_batch, sync_client.apply_remote_updates, sync_client.apply_remote_deletes]:
    method(do_hash_check=True)

sync_client.log_to_console('DONE')
