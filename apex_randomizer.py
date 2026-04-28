import random
import re
import sys
import zipfile
import xml.etree.ElementTree as ElementTree

if sys.version_info < (3, 8):
    raise SystemExit("请使用 Python 3.8 或更高版本运行本程序；PyQt6 不支持当前旧版本解释器。")

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


BASE_DIR = Path(__file__).resolve().parent
ROLL_LOG_PATH = BASE_DIR / "apex_roll_log.txt"
FETCH_LOG_PATH = BASE_DIR / "apex_fetch_log.txt"


@dataclass(frozen=True)
class Legend:
    """英雄数据：pick_rate 越高，热门优先模式下越容易被抽中。"""

    name: str
    pick_rate: float
    source_name: str = ""


@dataclass(frozen=True)
class Weapon:
    """武器数据：power_rank 越小代表越强，热门优先模式下越容易被抽中。"""

    name: str
    category: str
    is_care_package: bool
    power_rank: int
    source_name: str = ""


@dataclass(frozen=True)
class PlayerLoadout:
    """单名玩家的最终配置。"""

    player: str
    legend: Legend
    weapons: Tuple[Weapon, Weapon]


class DefaultData:
    """内置默认数据，保证断网或爬虫失败时应用仍可正常使用。"""

    LEGENDS = [
        Legend("变幻", 11, "Alter"),
        Legend("艾许", 1.6, "Ash"),
        Legend("弹道", 0.6, "Ballistic"),
        Legend("班加罗尔", 7.1, "Bangalore"),
        Legend("寻血猎犬", 0.4, "Bloodhound"),
        Legend("卡特莉丝", 0.7, "Catalyst"),
        Legend("侵蚀", 2.2, "Caustic"),
        Legend("导线管", 2.4, "Conduit"),
        Legend("密客", 1, "Crypto"),
        Legend("暴雷", 2.6, "Fuse"),
        Legend("直布罗陀", 4.3, "Gibraltar"),
        Legend("地平线", 1.9, "Horizon"),
        Legend("命脉", 2.6, "Lifeline"),
        Legend("罗芭", 1.5, "Loba"),
        Legend("疯玛吉", 16.3, "Mad Maggie"),
        Legend("幻象", 2.2, "Mirage"),
        Legend("纽卡斯尔", 1.1, "Newcastle"),
        Legend("动力小子", 12.7, "Octane"),
        Legend("探路者", 2.3, "Pathfinder"),
        Legend("兰伯特", 0.6, "Rampart"),
        Legend("亡灵", 3, "Revenant"),
        Legend("希尔", 0.7, "Seer"),
        Legend("瓦尔基里", 9.6, "Valkyrie"),
        Legend("万蒂奇", 0.6, "Vantage"),
        Legend("沃特森", 2.7, "Wattson"),
        Legend("恶灵", 5.9, "Wraith"),
        Legend("琉雀", 2.4, "Sparrow"),
    ]

    WEAPONS = [
        Weapon("R-301 卡宾枪", "mid", False, 11, "R-301 Carbine"),
        Weapon("VK-47 平行步枪", "mid", False, 9, "VK-47 Flatline"),
        Weapon("赫姆洛克连发突击步枪", "mid", False, 19, "Hemlok Burst AR"),
        Weapon("复仇女神连发突击步枪", "mid", False, 7, "Nemesis Burst AR"),
        Weapon("哈沃克步枪", "mid", False, 3, "HAVOC Rifle"),
        Weapon("专注轻机枪", "mid", False, 20, "Devotion LMG"),
        Weapon("R-99 冲锋枪", "close", False, 5, "R-99 SMG"),
        Weapon("C.A.R. 冲锋枪", "close", True, 1, "C.A.R. SMG"),
        Weapon("电能冲锋枪", "close", False, 14, "Volt SMG"),
        Weapon("转换者冲锋枪", "close", False, 12, "Alternator SMG"),
        Weapon("猎兽冲锋枪", "close", False, 2, "Prowler Burst PDW"),
        Weapon("和平捍卫者霰弹枪", "close", False, 23, "Peacekeeper"),
        Weapon("敖犬霰弹枪", "close", False, 21, "Mastiff Shotgun"),
        Weapon("EVA-8自动霰弹枪", "close", False, 8, "EVA-8 Auto"),
        Weapon("莫桑比克", "close", False, 6, "Mozambique Shotgun"),
        Weapon("辅助手枪", "mid", False, 17, "Wingman"),
        Weapon("RE-45 自动手枪", "close", False, 4, "RE-45"),
        Weapon("P2020", "close", False, 15, "P2020"),
        Weapon("M600 喷火轻机枪", "mid", False, 13, "M600 Spitfire"),
        Weapon("暴走", "mid", False, 10, "Rampage LMG"),
        Weapon("L-STAR 能量机枪", "mid", False, 16, "L-STAR EMG"),
        Weapon("G7 侦察枪", "long", True, 18, "G7 Scout"),
        Weapon("30-30 连发枪", "long", False, 22, "30-30 Repeater"),
        Weapon("三重式狙击枪", "long", False, 27, "Triple Take"),
        Weapon("哨兵狙击步枪", "long", False, 29, "Sentinel"),
        Weapon("长弓精确步枪", "long", False, 26, "Longbow DMR"),
        Weapon("充能步枪", "long", False, 28, "Charge Rifle"),
        Weapon("克雷贝尔 50口径狙击枪", "long", True, 24, "Kraber .50-Cal Sniper"),
        Weapon("波塞克 2.0", "long", False, 25, "Bocek Compound Bow"),
    ]


class AppLogger:
    """集中处理日志写入，避免 GUI 和随机引擎直接操作文件。"""

    def __init__(
        self,
        roll_log_path: Path = ROLL_LOG_PATH,
        fetch_log_path: Path = FETCH_LOG_PATH,
    ) -> None:
        self.roll_log_path = roll_log_path
        self.fetch_log_path = fetch_log_path

    @staticmethod
    def _now_text() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log_roll(self, loadouts: Iterable[PlayerLoadout]) -> None:
        lines = [f"[{self._now_text()}] ROLL"]
        for item in loadouts:
            weapon_names = " + ".join(weapon.name for weapon in item.weapons)
            lines.append(f"  {item.player}: {item.legend.name} | {weapon_names}")
        lines.append("")
        self.roll_log_path.write_text(
            self.roll_log_path.read_text(encoding="utf-8") + "\n".join(lines) + "\n"
            if self.roll_log_path.exists()
            else "\n".join(lines) + "\n",
            encoding="utf-8",
        )

    def log_fetch(self, source: str, success: bool, detail: str) -> None:
        status = "SUCCESS" if success else "FAILED"
        line = f"[{self._now_text()}] {status} | {source} | {detail}\n"
        self.fetch_log_path.write_text(
            self.fetch_log_path.read_text(encoding="utf-8") + line
            if self.fetch_log_path.exists()
            else line,
            encoding="utf-8",
        )


class LegendDataFetcher:
    """从 apexlegendsstatus.com 抓取英雄登场率。

    该网站 HTML 结构可能变化，因此解析逻辑采用“宽松匹配”：
    只要文本里同时出现英雄名和百分比，就尝试提取为 pick rate。
    """

    URL = "https://apexlegendsstatus.com/game-stats/legends-pick-rates"

    def fetch(self):
        response = requests.get(self.URL, timeout=15, headers=self._headers())
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text(" ", strip=True)
        parsed = []

        for default_legend in DefaultData.LEGENDS:
            query_name = default_legend.source_name or default_legend.name
            pattern = rf"{re.escape(query_name)}\s+([0-9]+(?:\.[0-9]+)?)\s*%"
            match = re.search(pattern, page_text, flags=re.IGNORECASE)
            if match:
                parsed.append(
                    Legend(
                        default_legend.name,
                        float(match.group(1)),
                        default_legend.source_name,
                    )
                )

        if len(parsed) < 10:
            raise ValueError("英雄登场率解析结果过少，网页结构可能已变化。")

        return parsed

    @staticmethod
    def _headers():
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        }


class WeaponDataFetcher:
    """从当前目录的 weapon.xlsx 读取武器强度排名。

    表格 Q 列是紫甲 TTK，秒数越低代表武器越强。
    第 6 行和第 58 行是传奇技能，不是游戏武器，读取时必须忽略。
    """

    SOURCE_PATH = BASE_DIR / "weapon.xlsx"
    URL = str(SOURCE_PATH)
    IGNORED_ROWS = {6, 58}

    def fetch(self):
        if not self.SOURCE_PATH.exists():
            raise FileNotFoundError(f"未找到武器数据文件：{self.SOURCE_PATH}")

        rows = self._read_sheet_rows(self.SOURCE_PATH)
        weapon_by_name = {weapon.name: weapon for weapon in DefaultData.WEAPONS}
        ranked_rows = []

        for row_number, cells in rows:
            if row_number in self.IGNORED_ROWS:
                continue

            weapon_name = str(cells.get("B", "")).strip()
            ttk_text = str(cells.get("Q", "")).strip()
            if not cells.get("A") or not weapon_name or not ttk_text:
                continue

            ttk = self._parse_ttk_seconds(ttk_text)
            if ttk is None:
                continue

            default_weapon = weapon_by_name.get(weapon_name)
            if default_weapon is None:
                continue

            ranked_rows.append((ttk, row_number, default_weapon))

        if len(ranked_rows) < 8:
            raise ValueError("weapon.xlsx 中可识别的武器数据过少，请检查 B 列武器名和 Q 列紫甲 TTK。")

        ranked_rows.sort(key=lambda item: (item[0], item[1]))
        return [
            Weapon(
                name=weapon.name,
                category=weapon.category,
                is_care_package=weapon.is_care_package,
                power_rank=rank,
                source_name=weapon.source_name,
            )
            for rank, (_, _, weapon) in enumerate(ranked_rows, start=1)
        ]

    @classmethod
    def _read_sheet_rows(cls, path):
        namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

        with zipfile.ZipFile(str(path)) as workbook:
            shared_strings = cls._read_shared_strings(workbook, namespace)
            sheet_xml = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
            rows = []

            for row in sheet_xml.findall(".//a:row", namespace):
                row_number = int(row.attrib.get("r", 0))
                cells = {}

                for cell in row.findall("a:c", namespace):
                    reference = cell.attrib.get("r", "")
                    column = "".join(char for char in reference if char.isalpha())
                    cells[column] = cls._read_cell_value(cell, shared_strings, namespace)

                rows.append((row_number, cells))

        return rows

    @staticmethod
    def _read_shared_strings(workbook, namespace):
        if "xl/sharedStrings.xml" not in workbook.namelist():
            return []

        shared_xml = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
        shared_strings = []
        for item in shared_xml.findall("a:si", namespace):
            text_parts = [node.text or "" for node in item.findall(".//a:t", namespace)]
            shared_strings.append("".join(text_parts))
        return shared_strings

    @staticmethod
    def _read_cell_value(cell, shared_strings, namespace):
        value_node = cell.find("a:v", namespace)
        if value_node is None:
            inline_text = cell.find(".//a:t", namespace)
            return inline_text.text if inline_text is not None else ""

        raw_value = value_node.text or ""
        if cell.attrib.get("t") == "s":
            return shared_strings[int(raw_value)]
        return raw_value

    @staticmethod
    def _parse_ttk_seconds(text):
        normalized = str(text).strip().replace("~", "-")

        # 形如“0.93s→0.89s”时，取箭头后的当前版本数值。
        if "→" in normalized:
            normalized = normalized.split("→")[-1]

        # 形如“蓄力0.42s\n秒杀0.83s”时，Q 列 TTK 应取秒杀耗时。
        instant_kill_marker = "\u79d2\u6740"
        if instant_kill_marker in normalized:
            normalized = normalized.split(instant_kill_marker)[-1]

        matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*s", normalized)
        if not matches:
            matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)", normalized)
        if not matches:
            return None

        return min(float(value) for value in matches)


class RandomLoadoutEngine:
    """负责所有随机逻辑，GUI 只传入模式和过滤选项。"""

    PLAYERS = ("玩家1", "玩家2", "玩家3")
    STANDARD = "随机模式"
    META = "热门优先"
    MEME = "冷门优先"

    def __init__(self) -> None:
        self.legends = list(DefaultData.LEGENDS)
        self.weapons = list(DefaultData.WEAPONS)

    def update_legends(self, legends) -> None:
        if len(legends) < len(self.PLAYERS):
            raise ValueError("英雄数量不足，无法为三名玩家分配不重复英雄。")
        self.legends = legends

    def update_weapons(self, weapons) -> None:
        if len(weapons) < 2:
            raise ValueError("武器数量不足，无法为玩家分配两把武器。")
        self.weapons = weapons

    def generate(
        self,
        legend_mode: str,
        weapon_mode: str,
        exclude_care_package: bool,
        forbid_odd_combo: bool,
        player_names=None,
    ):
        players = player_names or self.PLAYERS
        available_legends = list(self.legends)
        available_weapons = [
            weapon
            for weapon in self.weapons
            if not (exclude_care_package and weapon.is_care_package)
        ]

        if len(available_legends) < len(players):
            raise ValueError("可用英雄不足，无法生成三人小队。")
        if len(available_weapons) < 2:
            raise ValueError("可用武器不足，无法生成武器组合。")

        loadouts = []
        for player in players:
            legend = self._pick_one(available_legends, self._legend_weights(available_legends, legend_mode))
            available_legends.remove(legend)
            weapons = self._pick_weapon_pair(available_weapons, weapon_mode, forbid_odd_combo)
            loadouts.append(PlayerLoadout(player, legend, weapons))
        return loadouts

    def _pick_weapon_pair(
        self,
        weapons,
        mode: str,
        forbid_odd_combo: bool,
    ):
        weights = self._weapon_weights(weapons, mode)

        # 随机重试足够多次，通常可快速得到合法组合。
        for _ in range(200):
            first = self._pick_one(weapons, weights)
            second = self._pick_one(weapons, weights)
            if self._is_valid_pair(first, second, forbid_odd_combo):
                return first, second

        # 如果随机一直失败，枚举所有合法组合兜底，避免界面无响应。
        valid_pairs = [
            (first, second)
            for first in weapons
            for second in weapons
            if self._is_valid_pair(first, second, forbid_odd_combo)
        ]
        if not valid_pairs:
            raise ValueError("当前过滤条件下没有可用的合法武器组合。")

        return random.choice(valid_pairs)

    @staticmethod
    def _is_valid_pair(first: Weapon, second: Weapon, forbid_odd_combo: bool) -> bool:
        if first.name == second.name:
            return False
        if forbid_odd_combo and first.category == second.category:
            return False
        return True

    @classmethod
    def _legend_weights(cls, legends, mode):
        if mode == cls.STANDARD:
            return [1.0 for _ in legends]
        if mode == cls.META:
            return [max(legend.pick_rate, 0.1) for legend in legends]

        max_rate = max((legend.pick_rate for legend in legends), default=1.0)
        return [max(max_rate - legend.pick_rate + 0.1, 0.1) for legend in legends]

    @classmethod
    def _weapon_weights(cls, weapons, mode):
        if mode == cls.STANDARD:
            return [1.0 for _ in weapons]

        max_rank = max((weapon.power_rank for weapon in weapons), default=1)
        if mode == cls.META:
            return [max(max_rank - weapon.power_rank + 1, 1) for weapon in weapons]

        return [max(weapon.power_rank, 1) for weapon in weapons]

    @staticmethod
    def _pick_one(items, weights):
        return random.choices(items, weights=weights, k=1)[0]


class PlayerCard(QFrame):
    """展示单个玩家结果的大卡片。"""

    def __init__(self, player_name: str) -> None:
        super().__init__()
        self.setObjectName("PlayerCard")
        self.setMinimumHeight(230)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.player_input = QLineEdit(player_name)
        self.player_input.setObjectName("PlayerNameInput")
        self.player_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.player_input.setMaxLength(20)

        self.legend_label = QLabel("开始选择吧")
        self.legend_label.setObjectName("LegendName")
        self.legend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.legend_label.setWordWrap(True)

        self.weapon_label = QLabel("Weapon 1\nWeapon 2")
        self.weapon_label.setObjectName("WeaponNames")
        self.weapon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weapon_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(self.player_input)
        layout.addStretch(1)
        layout.addWidget(self.legend_label)
        layout.addWidget(self.weapon_label)
        layout.addStretch(1)

    def update_loadout(self, loadout: PlayerLoadout) -> None:
        self.legend_label.setText(loadout.legend.name)
        self.weapon_label.setText(f"{loadout.weapons[0].name}\n{loadout.weapons[1].name}")

    def player_name(self) -> str:
        name = self.player_input.text().strip()
        return name or self.player_input.placeholderText() or "玩家"


class ApexRandomizerWindow(QMainWindow):
    """主窗口：负责 UI 布局、用户交互和调用各业务类。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Apex Legends 英雄与武器生成器")
        self.resize(1120, 720)

        self.engine = RandomLoadoutEngine()
        self.legend_fetcher = LegendDataFetcher()
        self.weapon_fetcher = WeaponDataFetcher()
        self.logger = AppLogger()

        self.player_cards = []
        self._build_ui()
        self._apply_styles()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(18)
        self.setCentralWidget(root)

        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar, 0)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(18)

        header = QLabel("你的小队")
        header.setObjectName("Header")
        content_layout.addWidget(header)

        card_grid = QGridLayout()
        card_grid.setSpacing(16)
        for index, player in enumerate(RandomLoadoutEngine.PLAYERS):
            card = PlayerCard(player)
            self.player_cards.append(card)
            card_grid.addWidget(card, 0, index)
        content_layout.addLayout(card_grid, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(28)
        content_layout.addWidget(self.status_label)

        self.roll_button = QPushButton("开始新一轮跳伞")
        self.roll_button.setObjectName("RollButton")
        self.roll_button.setMinimumHeight(72)
        self.roll_button.clicked.connect(self.roll)
        content_layout.addWidget(self.roll_button)

        root_layout.addWidget(content, 1)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(300)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("设置")
        title.setObjectName("SidebarTitle")
        layout.addWidget(title)

        self.exclude_care_package_checkbox = QCheckBox("排除空投武器")
        self.forbid_odd_combo_checkbox = QCheckBox("禁止奇葩配置")
        self.exclude_care_package_checkbox.setChecked(True)
        self.forbid_odd_combo_checkbox.setChecked(True)
        layout.addWidget(self.exclude_care_package_checkbox)
        layout.addWidget(self.forbid_odd_combo_checkbox)

        layout.addSpacing(10)
        layout.addWidget(self._field_label("英雄权重模式"))
        self.legend_mode_combo = self._mode_combo()
        layout.addWidget(self.legend_mode_combo)

        layout.addWidget(self._field_label("武器权重模式"))
        self.weapon_mode_combo = self._mode_combo()
        layout.addWidget(self.weapon_mode_combo)

        layout.addSpacing(12)
        self.fetch_weapon_button = QPushButton("读取武器强度")
        self.fetch_weapon_button.clicked.connect(self.fetch_weapons)
        layout.addWidget(self.fetch_weapon_button)

        self.fetch_legend_button = QPushButton("抓取英雄登场率")
        self.fetch_legend_button.clicked.connect(self.fetch_legends)
        layout.addWidget(self.fetch_legend_button)

        layout.addStretch(1)

        hint = QLabel("日志文件会写入程序同目录：\napex_roll_log.txt\napex_fetch_log.txt")
        hint.setObjectName("HintLabel")
        layout.addWidget(hint)

        return sidebar

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    @staticmethod
    def _mode_combo() -> QComboBox:
        combo = QComboBox()
        combo.addItems(
            [
                RandomLoadoutEngine.STANDARD,
                RandomLoadoutEngine.META,
                RandomLoadoutEngine.MEME,
            ]
        )
        return combo

    def roll(self) -> None:
        try:
            loadouts = self.engine.generate(
                legend_mode=self.legend_mode_combo.currentText(),
                weapon_mode=self.weapon_mode_combo.currentText(),
                exclude_care_package=self.exclude_care_package_checkbox.isChecked(),
                forbid_odd_combo=self.forbid_odd_combo_checkbox.isChecked(),
                player_names=[card.player_name() for card in self.player_cards],
            )
        except Exception as exc:
            QMessageBox.warning(self, "生成失败", str(exc))
            return

        for card, loadout in zip(self.player_cards, loadouts):
            card.update_loadout(loadout)
        self.logger.log_roll(loadouts)
        self.status_label.setText("祝您成为捍卫者")

    def fetch_legends(self) -> None:
        self._set_fetching_state(True)
        try:
            legends = self.legend_fetcher.fetch()
            self.engine.update_legends(legends)
            detail = f"成功解析 {len(legends)} 名英雄。"
            self.logger.log_fetch(self.legend_fetcher.URL, True, detail)
            self.status_label.setText(detail)
            QMessageBox.information(self, "抓取成功", detail)
        except Exception as exc:
            detail = f"英雄登场率抓取失败，继续使用当前缓存：{exc}"
            self.logger.log_fetch(self.legend_fetcher.URL, False, detail)
            QMessageBox.warning(self, "抓取失败", detail)
        finally:
            self._set_fetching_state(False)

    def fetch_weapons(self) -> None:
        self._set_fetching_state(True)
        try:
            weapons = self.weapon_fetcher.fetch()
            self.engine.update_weapons(weapons)
            detail = f"成功解析 {len(weapons)} 把武器。"
            self.logger.log_fetch(self.weapon_fetcher.URL, True, detail)
            self.status_label.setText(detail)
            QMessageBox.information(self, "抓取成功", detail)
        except Exception as exc:
            detail = f"武器强度抓取失败，继续使用当前缓存：{exc}"
            self.logger.log_fetch(self.weapon_fetcher.URL, False, detail)
            QMessageBox.warning(self, "抓取失败", detail)
        finally:
            self._set_fetching_state(False)

    def _set_fetching_state(self, is_fetching: bool) -> None:
        self.fetch_legend_button.setDisabled(is_fetching)
        self.fetch_weapon_button.setDisabled(is_fetching)
        self.roll_button.setDisabled(is_fetching)
        if is_fetching:
            self.status_label.setText("正在抓取数据，请稍候...")
            QApplication.processEvents()

    def _apply_styles(self) -> None:
        self.setFont(QFont("Microsoft YaHei UI", 10))
        self.setStyleSheet(
            """
            QMainWindow {
                background: #111318;
            }
            QLabel {
                color: #eef2f7;
            }
            #Header {
                font-size: 30px;
                font-weight: 800;
                letter-spacing: 0px;
            }
            #Sidebar {
                background: #1a1d24;
                border: 1px solid #2b303a;
                border-radius: 8px;
            }
            #SidebarTitle {
                font-size: 28px;
                font-weight: 900;
            }
            #FieldLabel {
                color: #aab3c2;
                font-size: 16px;
                font-weight: 700;
                margin-top: 10px;
            }
            #HintLabel, #StatusLabel {
                color: #aab3c2;
                line-height: 1.4;
            }
            #HintLabel {
                font-size: 14px;
            }
            #StatusLabel {
                font-size: 18px;
                font-weight: 800;
                color: #f5c451;
            }
            QCheckBox {
                color: #eef2f7;
                spacing: 10px;
                font-size: 16px;
                font-weight: 700;
            }
            QComboBox {
                background: #232833;
                color: #eef2f7;
                border: 1px solid #343b49;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton {
                background: #273242;
                color: #eef2f7;
                border: 1px solid #3b4658;
                border-radius: 6px;
                padding: 12px 14px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #334257;
            }
            QPushButton:disabled {
                color: #717987;
                background: #20242c;
            }
            #RollButton {
                background: #d33f2f;
                border: 1px solid #ef6b58;
                font-size: 28px;
                font-weight: 900;
            }
            #RollButton:hover {
                background: #e34d3d;
            }
            #PlayerCard {
                background: #1a1d24;
                border: 1px solid #303846;
                border-radius: 8px;
            }
            #PlayerNameInput {
                background: #232833;
                color: #eef2f7;
                border: 1px solid #343b49;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 15px;
                font-weight: 800;
            }
            #LegendName {
                font-size: 24px;
                font-weight: 900;
            }
            #WeaponNames {
                color: #d8dee9;
                font-size: 17px;
                font-weight: 700;
            }
            """
        )


def main() -> None:
    app = QApplication(sys.argv)
    window = ApexRandomizerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
