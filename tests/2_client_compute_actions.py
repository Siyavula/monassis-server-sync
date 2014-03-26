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

# Figure out how to sync
sync_client.compute_actions()

# Write state to file
sync_client.log_to_console('Writing state to file')
import cPickle
state = {
    'client_actions': sync_client.client_actions,
    'server_actions': sync_client.server_actions,
}
with open('state.pickle', 'wb') as fp:
    cPickle.dump(state, fp, protocol=2)

sync_client.log_to_console('DONE')
