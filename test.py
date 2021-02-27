import unittest
import re

from utils import *

episodes_test = {
    # standard one
    "苍穹浩瀚S05.The.Expanse.2020.1080p.WEB-DL.x265.AC3￡cXcY@FRDS": ("苍穹浩瀚", "The Expanse", "2020"),
    # have dot inside Chinese name
    "约翰·亚当斯.E01-E07.John.Adams.2008.1080p.Blu-ray.x265.10bit.AC3￡cXcY@FRDS": ("约翰·亚当斯", "John Adams", "2008"),
    # dot is part of name and ':' missing and have extra "Part" suffix => 辛普森：美国制造 O.J.Made in America
    "辛普森.美国制造.O.J.Made.in.America.Part1-5.2016.1080p.Blu-ray.x265.10bit.AC3￡cXcY@FRDS": ("辛普森 美国制造", "O J Made in America", "2016"),
    # have extra "合集"/"Complete" suffix and no Year
    "胜者即是正义合集.Legal.High.Complete.BluRay.1080p.x265.10bit.MNHD-FRDS": ("胜者即是正义", "Legal High", ""),
    # with "全10集"
    "非自然死亡.全10集.UNNATURAL.Blu-ray.LPCM.2.0.x265.10bit-Yumi": ("非自然死亡", "UNNATURAL", ""),
    # with patten: 2015-2016
    "真实的人类S01-S02.Humans.2015-2016.1080p.Blu-ray.x265.10bit.AC3￡cXcY@FRDS": ("真实的人类", "Humans", "2015"),
    # without Chinese name
    "Modern.Family.Complete.AMZN.WEB-DL.1080p.AAC.5.1.x265.10bit-Joy": ("", "Modern Family", ""),
    # no year, with D5 / D9
    "Yes,Minister.S01-S03.D5.MiniSD-TLF": ("", "Yes,Minister", "")
}


class TestParseName(unittest.TestCase):

    def test_getname_episodes(self):
        for key, val in episodes_test.items():
            # print(key)
            with self.subTest():
                self.assertEqual(val, getname_episodes(key))

if __name__ == '__main__':
    unittest.main()