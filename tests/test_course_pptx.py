from __future__ import annotations

import re
import os
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from tests.test_course_outline_alignment import schedule_titles
from tests.course_assets import published_docs


ROOT = Path(__file__).resolve().parents[1]
COURSES = ROOT / "docs" / "courses"
BLUEPRINT = COURSES / "课程蓝图.md"
SLIDES = COURSES / "slides"


def pptx_name(number: int, title: str) -> str:
    stem = f"L{number:02d}-{title.replace('`', '')}"
    stem = re.sub(r'[<>:"/\\|?*]', "-", stem)
    stem = re.sub(r"\s+", "", stem)
    stem = re.sub(r"-+", "-", stem)
    return f"{stem}.pptx"


def slide_text(archive: zipfile.ZipFile, number: int) -> str:
    root = ET.fromstring(archive.read(f"ppt/slides/slide{number}.xml"))
    return "".join(root.itertext())


def normalized(text: str) -> str:
    return re.sub(r"[`\s]", "", text)


class CourseBlueprintTests(unittest.TestCase):
    def test_blueprint_has_contiguous_pages_for_each_lesson(self) -> None:
        body = BLUEPRINT.read_text(encoding="utf-8")
        starts = list(re.finditer(r"^## L(\d{2})｜(.+)$", body, re.MULTILINE))
        self.assertEqual(16, len(starts))
        for index, match in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(body)
            section = body[match.end():end]
            pages = re.findall(r"^\|\s*(\d{1,2})\s*\|\s*(\d{1,2}:\d{2})\s*\|", section, re.MULTILINE)
            with self.subTest(lesson=match.group(1)):
                self.assertTrue(pages, "每讲必须有逐页安排")
                self.assertEqual([str(i) for i in range(1, len(pages) + 1)], [page for page, _time in pages])
                self.assertEqual("0:00", pages[0][1])
                self.assertIn("课程大纲四项合同", section)
                self.assertRegex(section, r"一手来源（核验：\d{4}-\d{2}-\d{2}）")

    def test_blueprint_has_ordered_timing_and_beginner_learning_support(self) -> None:
        body = BLUEPRINT.read_text(encoding="utf-8")
        for marker in (
            "不超过 30 分钟",
            "教师示范",
            "学生尝试",
            "独立检查",
            "正常路径",
            "失败路径",
            "任务卡交接",
        ):
            self.assertIn(marker, body)
        sections = re.split(r"^## L\d{2}｜.+$", body, flags=re.MULTILINE)[1:]
        for section in sections:
            times = [60 * int(m) + int(s) for m, s in re.findall(
                r"^\|\s*\d{1,2}\s*\|\s*(\d{1,2}):(\d{2})\s*\|", section, re.MULTILINE)]
            self.assertTrue(all(a < b for a, b in zip(times, times[1:])))
            self.assertTrue(all(0 <= time < 1800 for time in times))

    def test_editable_course_diagrams_and_previews_exist(self) -> None:
        for stem in ("course-three-layer", "workbench-capability-growth", "fde-feedback-loop"):
            source = COURSES / "assets" / f"{stem}.drawio"
            self.assertTrue(source.is_file())
            self.assertTrue((COURSES / "assets" / f"{stem}.svg").is_file())
            ET.parse(source)

    @unittest.skipUnless(os.environ.get('CODEXFDE_VALIDATE_LOCAL_SLIDES') == '1',
                         'PPT 不随 Git 发布；显式启用本地课件检查')
    def test_each_lesson_has_valid_local_decks(self) -> None:
        expected_titles = schedule_titles()
        for number in expected_titles:
            decks = sorted((COURSES / f'L{number:02d}' / 'slides').glob('*.pptx'))
            self.assertTrue(decks, f'L{number:02d} 缺少本地课件')
            for deck in decks:
                with self.subTest(deck=deck.name), zipfile.ZipFile(deck) as archive:
                    self.assertIsNone(archive.testzip())
                    names = [name for name in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', name)]
                    self.assertTrue(names, '课件必须包含幻灯片')
                    for name in names:
                        ET.fromstring(archive.read(name))
                    self.assertIn(f'L{number:02d}', slide_text(archive, 1))

    def test_no_inspection_outputs_are_published_with_student_materials(self) -> None:
        self.assertFalse([p for p in published_docs() if p.name.endswith('.inspect.ndjson')])


if __name__ == "__main__":
    unittest.main()
