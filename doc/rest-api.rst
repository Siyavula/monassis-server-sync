============================
REST API for the sync server
============================

Conventions
===========

Timestamps
----------
All timestamps, such as expiration dates, are in ISO8601 format in the UTC (Z) timezone.

Errors
------
Most non-200 response codes (except 404) will include a JSON error
document. Error descriptions look like::

    {
        "error": {
            "status":  423,                          # HTTP status code
            "code":    "DatabaseLocked",             # error code
            "message": "The database is already locked by someone else",
        }
    }

Request ids
-----------
Every request has an associated unique request id (a UUID). This is
returned in the HTTP response headers as::

    X-Request-Id: a8098c1a-f86e-11da-bd1a-00112444be1e

and in the body of all JSON response documents as::

    {
        "request_id": "a8098c1a-f86e-11da-bd1a-00112444be1e",
        ...
    }

These are also associated with log messages. This makes it easy to tie
a request in a remote system to a request on the server.

CRUD API for records and hashes
===============================
Each HTTP command below is of the form::

    VERB url
        < json in request body
        > json in response (on HTTP 200)
        > raises HTTP code: Internal error code (exception name)

Database lock
-------------
Most actions, excepting some read actions, require the client to have
lock on the database. Exceptions are marked below. Only one client can
have lock on the database. Lock will time out after 15 minutes of
inactivity. This ensures that the sync server database is guaranteed
to remain unchanged by any process other than the current client.

To obtain database lock::

    PUT /{sync-name}/lock
        < {}
        > {'lock_key': string}
        > raises 423: DatabaseLocked

The returned lock_key value must be sent to subsequent calls to the
sync server. DatabaseLocked is raised if another process already has
lock on the database.

To release database lock::

    PUT /{sync-name}/unlock
        < {'lock_key': string}
        > {}
        > raises 423: DatabaseLocked

Records
-------
Read a record (no lock required)::

    GET /{sync-name}/{section}/{id}/record

Insert or update a record::

    PUT /{sync-name}/{section}/{id}/record

Delete a record::

    DELETE /{sync-name}/{section}/{id}/record

Hashes
------
Read a record hash (no lock required)::

    GET /{sync-name}/{section}/{id}/hash

Insert or update a record hash::

    PUT /{sync-name}/{section}/{id}/hash

Delete a record hash::

    DELETE /{sync-name}/{section}/{id}/hash

Compute a hash of the hash table::

    GET /{sync-name}/hash-hash

Compute all the CRUD actions needed to go from the last hashed state
to the current record state::

    GET /{sync-name}/hash-actions

Combined records and hashes
---------------------------
Read a record and its hash (no lock required)::

    GET /{sync-name}/{section}/{id}/record-hash

Insert or update a record and its hash::

    PUT /{sync-name}/{section}/{id}/record-hash

Delete a record and its hash::

    DELETE /{sync-name}/{section}/{id}/record-hash
