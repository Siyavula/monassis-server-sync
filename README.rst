monassis-server-sync
--------------------
The Monassis synchronisation server.

Merge strategies
----------------

master-slave:

The master node is the definitive source of information and will never
be updated with changes made to the database at the slave node. Any
changes made to the slave node between synchronisation calls will be
undone during synchronisation.

parent-child:

Changes made at either the parent or the child node will be applied to
the other node. This include all operations: insert, updated and
delete. Should there be any sort of conflict, for example the record
got deleted on one node and updated on the other, conflict resolution
will always favour the parent node.

peer:

Changes made at either peer node will be applied to the other
node. This include all operations: insert, updated and delete. A merge
method needs to be defined to handle conflicts.
