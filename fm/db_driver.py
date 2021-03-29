# -*- coding:utf-8 -*-

class SqlFormat(object):
    def insert_format(self, table):
        row = self.__dict__
        keys = row.keys()
        cmd = ['insert into %s(' % table]

        for k in keys:
            cmd.append('"%s"' % k)
            cmd.append(',')

        cmd[-1] = ') values('

        for k in keys:
            v = row[k]
            if isinstance(v, str):
                cmd.append("'%s'" % v.replace("'", "''"))
            else:
                cmd.append('%s' % v)

            cmd.append(',')

        cmd[-1] = ');'

        return ''.join(cmd)


class DB(object):
    def __init__(self):
        self.delay = False

    def _exec(self, cmd):
        if not self.conn:
            return

        try:
            return self.c.execute(cmd)
        except:
            print(cmd)
            raise(Exception(cmd))

    def commit(self):
        self.conn.commit()
        self.delay = False

    def set_delay(self):
        self.delay = True

    def last_rowid(self):
        cmd = 'SELECT last_insert_rowid();'
        self._exec(cmd)
        return self.c.fetchone()[0]

class Filter(object):
    def __init__(self, table, **f):
        self.table = table.table
        self.sel_handle = getattr(table, 'sel_handle', None)
        self.kv_handle = getattr(table, 'kv_handle', None)
        self.db = table.db
        self.where = []

        self.filter(**f)

    def get_where(self):
        return self.where

    def filter(self, **f):
        w = self.where
        for k, v in f.items():
            if self.kv_handle:
                k, v = self.kv_handle(k, v)

            if w:
                w.append('and')

            if isinstance(v, str):
                v = v.replace("'", "''")
                w.append("%s='%s'" % (k, v))
            else:
                w.append('%s=%s' % (k, v))

    def __add__(self, obj):
        self.where.append('or')
        self.where.extend(obj.where)
        return self

    def delete(self):
        cmd = []
        cmd.append('delete from')
        cmd.append(self.table)
        cmd.append('where')
        cmd.extend(self.get_where())
        cmd = ' '.join(cmd)

        self.db._exec(cmd)
        self.db.conn.commit()

    def select(self):
        cmd = []
        cmd.append('select rowid,* from')
        cmd.append(self.table)

        w = self.get_where()
        if w:
            cmd.append('where')
            cmd.extend(self.get_where())
        cmd = ' '.join(cmd)

        self.db._exec(cmd)
        ret =  self.db.c.fetchall()
        if self.sel_handle:
            return self.sel_handle(ret)
        else:
            return ret

    def update(self, **kv):
        cmd = []
        cmd.append('update')
        cmd.append(self.table)
        cmd.append('set')

        for k,v in kv.items():
            if self.kv_handle:
                k, v = self.kv_handle(k, v)
            cmd.append('%s=' % k)

            if isinstance(v, str):
                cmd.append("'%s'" % v.replace("'", "''"))
            else:
                cmd.append('%s' % v)

            cmd.append(',')

        cmd[-1] = 'where'
        cmd.extend(self.get_where())
        cmd = ' '.join(cmd)

        self.db._exec(cmd)
        self.db.conn.commit()


class Table(object):
    def last_rowid(self):
        return self.db.last_rowid()

    def filter(self, **f):
        return Filter(self, **f)

    def select_handler(self, rets):
        return rets


