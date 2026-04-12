"""
Tests para core/page_identity.py – PageIdentityMap
"""
import unittest
from core.page_identity import PageIdentityMap


class TestPageIdentityMap(unittest.TestCase):
    """Tests unitarios para el mapa de identidad de páginas."""

    def test_initialize(self):
        m = PageIdentityMap()
        m.initialize(3)
        self.assertEqual(len(m._order), 3)
        # UUIDs únicos
        self.assertEqual(len(set(m._order)), 3)

    def test_uuid_round_trip(self):
        m = PageIdentityMap()
        m.initialize(4)
        uid = m.uuid_for_index(2)
        self.assertEqual(m.index_for_uuid(uid), 2)

    def test_uuid_for_index_out_of_range(self):
        m = PageIdentityMap()
        m.initialize(2)
        self.assertIsNone(m.uuid_for_index(5))

    def test_insert_pages(self):
        m = PageIdentityMap()
        m.initialize(3)
        original = list(m._order)
        new_uuids = m.insert_pages(1, 2)
        self.assertEqual(len(m._order), 5)
        self.assertEqual(len(new_uuids), 2)
        # Las páginas originales se mantienen
        self.assertEqual(m._order[0], original[0])
        self.assertEqual(m._order[3], original[1])
        self.assertEqual(m._order[4], original[2])

    def test_insert_at_end(self):
        m = PageIdentityMap()
        m.initialize(2)
        m.insert_pages(2, 1)
        self.assertEqual(len(m._order), 3)

    def test_remove_page(self):
        m = PageIdentityMap()
        m.initialize(3)
        uid_1 = m.uuid_for_index(1)
        removed = m.remove_page(0)
        self.assertIsNotNone(removed)
        self.assertEqual(len(m._order), 2)
        # La que era la segunda ahora es la primera
        self.assertEqual(m._order[0], uid_1)

    def test_remove_last_page_fails(self):
        m = PageIdentityMap()
        m.initialize(1)
        self.assertIsNone(m.remove_page(0))

    def test_reorder(self):
        m = PageIdentityMap()
        m.initialize(3)
        uids = list(m._order)
        # Invertir [2, 1, 0]
        self.assertTrue(m.reorder([2, 1, 0]))
        self.assertEqual(m._order, [uids[2], uids[1], uids[0]])

    def test_reorder_invalid(self):
        m = PageIdentityMap()
        m.initialize(3)
        self.assertFalse(m.reorder([0, 1]))  # longitud incorrecta
        self.assertFalse(m.reorder([0, 0, 2]))  # duplicado

    def test_move_page(self):
        m = PageIdentityMap()
        m.initialize(4)
        uids = list(m._order)
        self.assertTrue(m.move_page(0, 2))
        # Primero se quita index 0, luego se inserta en index 2
        self.assertEqual(m._order[2], uids[0])

    def test_serialization(self):
        m = PageIdentityMap()
        m.initialize(3)
        data = m.to_list()
        m2 = PageIdentityMap()
        m2.from_list(data)
        self.assertEqual(m._order, m2._order)

    def test_from_list_none(self):
        m = PageIdentityMap()
        m.initialize(2)
        m.from_list(None)
        self.assertEqual(len(m._order), 0)


if __name__ == "__main__":
    unittest.main()
