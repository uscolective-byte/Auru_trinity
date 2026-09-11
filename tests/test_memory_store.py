from datetime import UTC, datetime, timedelta
import unittest

from trinity.memory.models import (
    LongTermUserMemory, ProjectFact, RetentionRule, Sensitivity, ShortTermContext,
)
from trinity.memory.store import SQLiteMemoryStore


class SQLiteMemoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = SQLiteMemoryStore()

    def tearDown(self):
        self.store.close()

    def test_reads_are_scoped_and_round_trip_models(self):
        self.store.write(LongTermUserMemory(
            owner_id="u1", source="explicit", sensitivity=Sensitivity.INTERNAL,
            retention=RetentionRule.DAYS_365, content={"language": "sk"},
        ))
        self.store.write(LongTermUserMemory(
            owner_id="u2", source="explicit", sensitivity=Sensitivity.INTERNAL,
            retention=RetentionRule.DAYS_365, content={"language": "en"},
        ))
        self.store.write(ProjectFact(
            owner_id="u2", project_id="p1", source="document",
            sensitivity=Sensitivity.CONFIDENTIAL, retention=RetentionRule.DAYS_365,
            content={"status": "active"},
        ))
        self.assertEqual(["u1"], [x.owner_id for x in self.store.search(user_id="u1")])
        self.assertEqual(["p1"], [x.project_id for x in self.store.search(project_id="p1")])
        with self.assertRaises(ValueError):
            self.store.search()
        with self.assertRaises(ValueError):
            self.store.search(user_id="u1", project_id="p1")

    def test_secret_fields_are_rejected(self):
        for content in ({"password": "bad"}, {"nested": {"api_token": "bad"}},
                        {"environment": {"PATH": "/bin"}}):
            with self.subTest(content=content), self.assertRaises(ValueError):
                self.store.write(LongTermUserMemory(
                    owner_id="u1", source="test", sensitivity=Sensitivity.RESTRICTED,
                    retention=RetentionRule.DAYS_30, content=content,
                ))

    def test_expiry_session_export_and_delete(self):
        self.store.write(LongTermUserMemory(
            owner_id="u1", source="old", sensitivity=Sensitivity.INTERNAL,
            retention=RetentionRule.DAYS_30,
            created_at=datetime.now(UTC) - timedelta(days=31), content={"old": True},
        ))
        session = ShortTermContext(
            owner_id="u1", source="chat", sensitivity=Sensitivity.INTERNAL,
            retention=RetentionRule.SESSION, session_id="s1", content={"step": 2},
        )
        self.store.write(session)
        exported = self.store.export(user_id="u1")
        self.assertEqual([session.id], [item["id"] for item in exported])
        self.assertEqual(1, self.store.clear_session(user_id="u1", session_id="s1"))
        self.assertEqual([], self.store.search(user_id="u1"))

    def test_record_delete_cannot_cross_scope(self):
        record = LongTermUserMemory(
            owner_id="u1", source="test", sensitivity=Sensitivity.INTERNAL,
            retention=RetentionRule.DAYS_365, content={"preference": "concise"},
        )
        self.store.write(record)
        self.assertEqual(0, self.store.delete(user_id="u2", record_id=record.id))
        self.assertEqual(1, self.store.delete(user_id="u1", record_id=record.id))


if __name__ == "__main__":
    unittest.main()
