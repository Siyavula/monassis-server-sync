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
