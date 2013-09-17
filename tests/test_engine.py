import sqlalchemy
from sqlalchemy.engine import RowProxy
from sqlalchemy.exc import StatementError

from twisted.trial import unittest

from alchimia import TWISTED_STRATEGY
from alchimia.engine import (
    TwistedEngine, TwistedConnection, TwistedTransaction,
)

from .doubles import FakeThreadedReactor


def create_engine():
    return sqlalchemy.create_engine(
        "sqlite://", strategy=TWISTED_STRATEGY, reactor=FakeThreadedReactor()
    )


class TestEngineCreation(object):
    def test_simple_create_engine(self):
        engine = sqlalchemy.create_engine(
            "sqlite://",
            strategy=TWISTED_STRATEGY,
            reactor=FakeThreadedReactor()
        )
        assert isinstance(engine, TwistedEngine)


class TestEngine(unittest.TestCase):
    def test_connect(self):
        engine = create_engine()
        d = engine.connect()
        connection = self.successResultOf(d)
        assert isinstance(connection, TwistedConnection)

    def test_execute(self):
        engine = create_engine()
        d = engine.execute("SELECT 42")
        result = self.successResultOf(d)
        d = result.scalar()
        assert self.successResultOf(d) == 42


class TestConnection(unittest.TestCase):
    def get_connection(self):
        engine = create_engine()
        d = engine.connect()
        return self.successResultOf(d)

    def test_execute(self):
        conn = self.get_connection()
        d = conn.execute("SELECT 42")
        result = self.successResultOf(d)
        d = result.scalar()
        assert self.successResultOf(d) == 42

    def test_close(self):
        conn = self.get_connection()
        assert not conn.closed
        result = self.successResultOf(conn.execute("SELECT 42"))
        assert self.successResultOf(result.scalar()) == 42

        self.successResultOf(conn.close())
        assert conn.closed
        failure = self.failureResultOf(
            conn.execute("SELECT 42"), StatementError)
        assert "This Connection is closed" in str(failure)

    def test_transaction(self):
        conn = self.get_connection()
        assert not conn.in_transaction()

        transaction = self.successResultOf(conn.begin())
        assert isinstance(transaction, TwistedTransaction)
        assert conn.in_transaction()

        self.successResultOf(transaction.close())
        assert not conn.in_transaction()

    def test_nested_transaction(self):
        conn = self.get_connection()
        assert not conn.in_transaction()

        trx1 = self.successResultOf(conn.begin())
        assert conn.in_transaction()
        trx2 = self.successResultOf(conn.begin())
        assert conn.in_transaction()

        self.successResultOf(trx2.close())
        assert conn.in_transaction()
        self.successResultOf(trx1.close())
        assert not conn.in_transaction()


class TestResultProxy(unittest.TestCase):
    def test_fetchone(self):
        engine = create_engine()
        d = engine.execute("SELECT 42")
        result = self.successResultOf(d)
        d = result.fetchone()
        row = self.successResultOf(d)
        assert isinstance(row, RowProxy)
        assert row[0] == 42

    def test_fetchall(self):
        engine = create_engine()
        d = engine.execute("SELECT 10")
        result = self.successResultOf(d)
        d = result.fetchall()
        rows = self.successResultOf(d)
        assert len(rows) == 1
        assert rows[0][0] == 10
