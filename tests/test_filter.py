"""Тесты фильтрации portable и размера раздач."""
import unittest
from core.filter import (
    is_portable,
    parse_size_to_bytes,
    is_allowed_size,
    clean_game_title,
    MAX_SIZE_BYTES,
)


class TestFilter(unittest.TestCase):

    def test_is_portable(self):
        # Должны быть Portable
        self.assertTrue(is_portable("[DL] Repel The Rifts [P] [ENG + 6] (2026, Strategy) (1.0.26) [Portable] [242.7 MB]"))
        self.assertTrue(is_portable("Dungeonbound (v1.0.5) (Portable)"))
        self.assertTrue(is_portable("Game Title [Portable by Canek77]"))
        self.assertTrue(is_portable("Portal 2 [Портативная версия]"))
        self.assertTrue(is_portable("osu! [P] (Portable) [570 MB]"))
        self.assertTrue(is_portable("Retro Game", text="Тип издания: Portable"))

        # НЕ должны быть Portable
        self.assertFalse(is_portable("Dungeonbound [RePack by FitGirl] [3.2 GB]"))
        self.assertFalse(is_portable("Cyberpunk 2077 [Лицензия] [GOG] [65 GB]"))
        self.assertFalse(is_portable("Half-Life 2 [Rip] [1.4 GB]"))
        self.assertFalse(is_portable("Need for Speed Underground 2 [ISO]"))

    def test_parse_size_to_bytes(self):
        self.assertEqual(parse_size_to_bytes("500 KB"), 500 * 1024)
        self.assertEqual(parse_size_to_bytes("306.7 MB"), int(306.7 * 1024 * 1024))
        self.assertEqual(parse_size_to_bytes("1.5 GB"), int(1.5 * 1024 * 1024 * 1024))
        self.assertEqual(parse_size_to_bytes("60 GB"), 60 * 1024 * 1024 * 1024)
        self.assertEqual(parse_size_to_bytes("60,5 ГБ"), int(60.5 * 1024 * 1024 * 1024))
        self.assertIsNone(parse_size_to_bytes("Unknown"))
        self.assertIsNone(parse_size_to_bytes(""))

    def test_is_allowed_size(self):
        # Меньше или равно 60 ГБ
        self.assertTrue(is_allowed_size("242.7 MB"))
        self.assertTrue(is_allowed_size("1.95 GB"))
        self.assertTrue(is_allowed_size("58.4 GB"))
        self.assertTrue(is_allowed_size("60.0 GB"))
        self.assertTrue(is_allowed_size("60 GB"))

        # Больше 60 ГБ
        self.assertFalse(is_allowed_size("60.1 GB"))
        self.assertFalse(is_allowed_size("60.55 GB"))
        self.assertFalse(is_allowed_size("75 GB"))
        self.assertFalse(is_allowed_size("120 GB"))
        self.assertFalse(is_allowed_size("Unknown"))

    def test_clean_game_title(self):
        raw = "[DL] Repel The Rifts [P] [ENG + 6] (2026, Strategy) (1.0.26) [Portable] [242.7 MB]"
        self.assertEqual(clean_game_title(raw), "Repel The Rifts")

        raw2 = "[Обновлено] [DL] [В разработке] Windblown [P] [RUS + ENG + 8] (2024, Action) (0.2.14.0) [Portable] [1.95 GB]"
        self.assertEqual(clean_game_title(raw2), "Windblown")

        raw3 = "[DL] Dungeonbound [P] [RUS + ENG + 11] (2026, RPG) (v1.0.5) [Portable] [306.7 MB]"
        self.assertEqual(clean_game_title(raw3), "Dungeonbound")


if __name__ == '__main__':
    unittest.main()
