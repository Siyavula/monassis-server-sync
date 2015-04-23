if __name__ == '__main__':
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
        sync_client.log_to_console(
            'Hash hash is inconsistent between client and server: trying transactions file.')
        sync_client.load_transactions()
        if sync_client.transactions is None:
            sync_client.log_to_console('No unfinished transactions found: refusing to synchronise.')
            sys.exit(-1)
        sync_client.log_to_console('Found unfinished transactions: completing them now.')
        sync_client.execute_transaction_block()
        try:
            sync_client.check_hash_consistency()
        except HashError:
            sync_client.log_to_console(
                'Hash hash is still inconsistent between client and server: '
                'refusing to synchronise.')
            sys.exit(-1)

    # Figure out how to sync
    sync_client.compute_actions()

    # Apply local and remote sync actions
    for method in [
            sync_client.apply_hash_actions, sync_client.apply_local_inserts_batch,
            sync_client.apply_local_updates_batch, sync_client.apply_local_deletes_batch,
            sync_client.apply_remote_inserts_batch, sync_client.apply_remote_updates_batch,
            sync_client.apply_remote_deletes_batch]:
        try:
            method(do_hash_check=True)
        except HashError:
            sys.exit()

    # TODO: Trigger client onchange events

    sync_client.log_to_console('DONE')
