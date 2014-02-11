if __name__ == '__main__':
    import monassis.qnxmlservice.dbmodel as templatedb
    import monassis.books.dbmodel as bookdb
    import monassis.usermanagement.dbmodel as userdb
    import monassis.historyservice.dbmodel as historydb

    import sqlalchemy
    from hashlib import md5

    hash_hash = md5()
    for dbmodel in [templatedb, bookdb, userdb, historydb]:
        database = dbmodel.db
        for table_name in sorted(dbmodel.tables.keys()):
            if table_name == 'record_hashes':
                continue
            table_hash = md5()
            table = dbmodel.tables[table_name]

            select = sqlalchemy.sql.select([table]).limit(1)
            result = database.execute(select)
            columns = result.fetchone().keys()
            columns.sort()
            columns = [table.c[column] for column in columns]

            select = sqlalchemy.sql.select(columns).order_by(*columns)
            result = database.execute(select)
            count = 0
            for row in result:
                table_hash.update(repr(tuple(row)))
                if (count < 5) and (count % 1) == 0 and (table_name == 'templates'):
                    print table_hash.hexdigest()
                count += 1
            result.close()
            print table_name, table_hash.hexdigest()
            hash_hash.update(table_hash.hexdigest())
    print hash_hash.hexdigest()
