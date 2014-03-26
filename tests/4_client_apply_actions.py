import sys
from syncserver.client import SyncClient, ConnectionError, HashError
from syncserver import utils

# Load config
config_path = sys.argv[1]
sync_time = utils.now_utc()
sync_client = SyncClient(config_path, sync_time, log_file=sys.stdout)

# Connect to server
try:
    sync_client.connect_to_server()
except ConnectionError:
    sys.exit(-1)

# Check database consistency using hash_hash
try:
    sync_client.check_hash_consistency()
except HashError:
    sync_client.log_to_console('Hash hash is inconsistent between client and server. Refusing to synchronise.')
    sys.exit(-1)

# Read state from file
sync_client.log_to_console('Reading state from file')
import cPickle
with open('state.pickle', 'rb') as fp:
    state = cPickle.load(fp)
sync_client.client_actions = state['client_actions']
sync_client.server_actions = state['server_actions']

# Apply local and remote sync actions
for method in [sync_client.apply_hash_actions, sync_client.apply_local_inserts, sync_client.apply_local_updates, sync_client.apply_local_deletes, sync_client.apply_remote_inserts, sync_client.apply_remote_updates, sync_client.apply_remote_deletes]:
    try:
        method(do_hash_check=True)
    except HashError:
        sys.exit()

sync_client.log_to_console('DONE')
