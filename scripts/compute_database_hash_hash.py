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
        for table_name in dbmodel.tables:
            if table_name == 'record_hashes':
                continue
            print table_name
            table = dbmodel.tables[table_name]
            select = sqlalchemy.sql.select([table])
            result = database.execute(select)
            start = True
            for row in result:
                if start:
                    columns = sorted(row.keys())
                    start = False
                for column in columns:
                    hash_hash.update(repr(row[column]))
            result.close()
    print hash_hash.hexdigest()
