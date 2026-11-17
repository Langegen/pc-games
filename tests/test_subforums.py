"""Тесты изоляции и конфигурации подразделов."""
import unittest
from config.subforums import (
    SUBFORUMS,
    EXCLUDED_SUBFORUM_IDS,
    is_subforum_allowed,
    get_subforum_info,
    get_all_allowed_subforums,
)


class TestSubforums(unittest.TestCase):

    def test_strict_exclusions(self):
        """Проверка, что указанные пользователем разделы строго исключены."""
        # Разделы, явно названные пользователем:
        self.assertIn("1151", EXCLUDED_SUBFORUM_IDS)
        self.assertIn("2228", EXCLUDED_SUBFORUM_IDS)
        self.assertIn("68", EXCLUDED_SUBFORUM_IDS)

        # Ни один из них не должен быть в разрешённых
        self.assertNotIn("1151", SUBFORUMS)
        self.assertNotIn("2228", SUBFORUMS)
        self.assertNotIn("68", SUBFORUMS)

        # Проверка функции допуска
        self.assertFalse(is_subforum_allowed("1151"))
        self.assertFalse(is_subforum_allowed("2228"))
        self.assertFalse(is_subforum_allowed("68"))
        self.assertFalse(is_subforum_allowed(1151))
        self.assertFalse(is_subforum_allowed(2228))
        self.assertFalse(is_subforum_allowed(68))

    def test_allowed_subforums(self):
        """Проверка наличия ключевых подразделов для ПК-игр."""
        self.assertTrue(is_subforum_allowed("635"))   # Новинки
        self.assertTrue(is_subforum_allowed("52"))    # RPG
        self.assertTrue(is_subforum_allowed("646"))   # Action TPS
        self.assertTrue(is_subforum_allowed("647"))   # Action FPS
        self.assertTrue(is_subforum_allowed("51"))    # RTS
        self.assertTrue(is_subforum_allowed("2226"))  # TBS
        self.assertTrue(is_subforum_allowed("53"))    # Приключения
        self.assertTrue(is_subforum_allowed("54"))    # Симуляторы
        self.assertTrue(is_subforum_allowed("50"))    # Хорроры
        self.assertTrue(is_subforum_allowed("127"))   # Аркады

        # Ретро подразделы
        self.assertTrue(is_subforum_allowed("1007"))  # Ретро-аркады
        self.assertTrue(is_subforum_allowed("2205"))  # Ретро-стратегии

    def test_get_subforum_info(self):
        info = get_subforum_info("52")
        self.assertEqual(info["id"], "52")
        self.assertEqual(info["name"], "Ролевые игры")
        self.assertEqual(info["slug"], "rpg")

        all_sf = get_all_allowed_subforums()
        self.assertGreater(len(all_sf), 20)


if __name__ == '__main__':
    unittest.main()
