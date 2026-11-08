"""宠物护理技能核心脚本"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    raise ImportError(
        '缺少 PyYAML 依赖。请运行: pip install -r requirements.txt 或 pip install pyyaml'
    ) from None


# ============================================================
# 项目根目录 / 知识库路径（统一计算，避免各模块各自为政）
# ============================================================
_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_ROOT: Path = _ROOT / "knowledge"
DOG_BREEDS_MD = DATA_ROOT / "dog_breeds.md"
CAT_BREEDS_MD = DATA_ROOT / "cat_breeds.md"
NUTRITION_MD = DATA_ROOT / "nutrition.md"
HEALTH_MD = DATA_ROOT / "health.md"


# ============================================================
# 1. 枚举与字段优先级
# ============================================================


class FieldPriority(Enum):
    """字段优先级分级

    - REQUIRED: 第一层，必填项。缺失时立即追问，不跳过。
    - INFERABLE: 第二层，可推断项。缺失时从知识库智能填充 + 事后标注确认。
    - ENHANCEMENT: 第三层，增强项。缺失时跳过，计划生成后以「可优化项」形式统一追问。
    """

    REQUIRED = "required"
    INFERABLE = "inferable"
    ENHANCEMENT = "enhancement"


class PetCategory(Enum):
    """宠物类别"""

    DOG = "dog"
    CAT = "cat"


class PetSize(Enum):
    """体型分级"""

    SMALL = "small"     # <10kg
    MEDIUM = "medium"   # 10-25kg
    LARGE = "large"     # 25-45kg
    GIANT = "giant"     # >45kg


class LifeStage(Enum):
    """生命周期阶段"""

    PUPPY = "puppy"       # 幼犬/幼猫：0-1岁（小型犬可到6-12月，大型犬1-1.5岁）
    ADULT = "adult"       # 成犬/成猫：1-7岁
    SENIOR = "senior"     # 老年：7岁+ (大型犬5岁+)
    PREGNANT = "pregnant" # 孕期/育儿期


class BodyCondition(Enum):
    """体态评估（BCS 简化版）"""

    UNDERWEIGHT = "underweight"   # 偏瘦
    NORMAL = "normal"             # 正常
    OVERWEIGHT = "overweight"     # 偏胖
    OBESE = "obese"               # 肥胖


class Gender(Enum):
    """性别"""

    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class DietMode(Enum):
    """饮食模式偏好"""

    FULL_PRICE = "full_price"     # 全价粮（商业粮）
    HOMEMADE = "homemade"         # 自制
    RAW = "raw"                   # 生骨肉
    MIXED = "mixed"               # 混合


class FunctionalNeed(Enum):
    """功能性需求标签"""

    BEAUTY_COAT = "beauty_coat"           # 美毛增亮
    WEIGHT_LOSS = "weight_loss"           # 减肥
    WEIGHT_GAIN = "weight_gain"           # 增肥
    TEAR_STAIN = "tear_stain"             # 去泪痕
    GUT_HEALTH = "gut_health"             # 改善肠胃
    REPRODUCTION = "reproduction"         # 孕期/生育营养
    JOINT_CARE = "joint_care"             # 关节护理
    DENTAL_CARE = "dental_care"           # 口腔护理
    URINARY_CARE = "urinary_care"         # 泌尿护理（猫常见）
    HAIRBALL = "hairball"                 # 化毛/去毛球（猫常见）


FIELD_PRIORITY_MAP: dict[str, FieldPriority] = {
    # --- 第一层：必填 ---
    "category": FieldPriority.REQUIRED,
    "breed_id": FieldPriority.REQUIRED,
    "breed_name": FieldPriority.REQUIRED,

    # --- 第二层：可推断 ---
    "age_months": FieldPriority.INFERABLE,
    "weight_kg": FieldPriority.INFERABLE,
    "life_stage": FieldPriority.INFERABLE,
    "sterilized": FieldPriority.INFERABLE,
    "monthly_budget": FieldPriority.INFERABLE,
    "body_condition": FieldPriority.INFERABLE,
    "size": FieldPriority.INFERABLE,

    # --- 第三层：增强 ---
    "gender": FieldPriority.ENHANCEMENT,
    "diet_mode": FieldPriority.ENHANCEMENT,
    "food_allergies": FieldPriority.ENHANCEMENT,
    "health_issues": FieldPriority.ENHANCEMENT,
    "functional_needs": FieldPriority.ENHANCEMENT,
}


def get_field_priority(field_name: str) -> FieldPriority:
    """获取指定字段的优先级，未登记字段默认归类为 ENHANCEMENT"""
    return FIELD_PRIORITY_MAP.get(field_name, FieldPriority.ENHANCEMENT)


def get_fields_by_priority(priority: FieldPriority) -> list[str]:
    """获取指定优先级下的所有字段名"""
    return [k for k, v in FIELD_PRIORITY_MAP.items() if v == priority]


FIELD_LABELS: dict[str, str] = {
    "category": "宠物类别",
    "breed_id": "品种ID",
    "breed_name": "品种名称",
    "age_months": "年龄（月）",
    "weight_kg": "体重（kg）",
    "life_stage": "生命周期阶段",
    "sterilized": "是否绝育",
    "monthly_budget": "月预算（元）",
    "body_condition": "体态评估",
    "size": "体型分级",
    "gender": "性别",
    "diet_mode": "饮食模式",
    "food_allergies": "食物过敏史",
    "health_issues": "健康问题/既往病史",
    "functional_needs": "功能性需求",
}


def get_field_label(field_name: str) -> str:
    return FIELD_LABELS.get(field_name, field_name)


FIELD_HINTS: dict[str, str] = {
    "age_months": "示例：36（3岁），范围：0-240 月",
    "weight_kg": "示例：金毛 25-34kg，英短 4-7kg",
    "monthly_budget": "小型犬 300-800元 / 中型犬 500-1200元 / 大型犬 800-2000元",
    "body_condition": "可选：normal（正常）/underweight（偏瘦）/overweight（偏胖）/obese（肥胖）",
    "diet_mode": "可选：full_price（全价粮）/ homemade（自制）/ raw（生骨肉）/ mixed（混合）",
}


def get_field_hint(field_name: str) -> Optional[str]:
    return FIELD_HINTS.get(field_name)


# ============================================================
# 2. 数据模型
# ============================================================


@dataclass
class Breed:
    """品种数据（从 MD front matter + 正文解析而来）"""

    # ----- front matter 结构化字段 -----
    breed_id: str
    breed_name: str
    breed_name_en: str
    category: PetCategory                        # dog | cat
    size: PetSize                                # small | medium | large | giant
    origin: str = ""

    # 体型参数
    adult_weight_min_kg: Optional[float] = None
    adult_weight_max_kg: Optional[float] = None
    adult_height_min_cm: Optional[float] = None
    adult_height_max_cm: Optional[float] = None
    weight_growth: dict[int, float] = field(default_factory=dict)  # {月龄: 标准体重kg}

    # 寿命
    life_span_min: Optional[int] = None
    life_span_max: Optional[int] = None

    # 需求等级 1-5
    energy_level: Optional[int] = None           # 运动量需求
    grooming_needs: Optional[int] = None         # 美容护理需求
    trainability: Optional[int] = None           # 可训练性
    social_needs: Optional[int] = None           # 社交需求

    # 健康倾向
    common_health_issues: list[str] = field(default_factory=list)

    # 饮食参数
    daily_calorie_per_kg: Optional[float] = None
    protein_ratio: Optional[float] = None
    fat_ratio: Optional[float] = None
    special_diet_notes: str = ""

    # 月度参考开销
    monthly_cost: dict[str, int] = field(default_factory=dict)  # {food/grooming/medical/supplies: 元}

    # ----- Markdown 正文描述性内容 -----
    description_sections: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------

    def adult_weight_median_kg(self) -> Optional[float]:
        """成年标准体重中位数（用于推断体重）"""
        if self.adult_weight_min_kg is not None and self.adult_weight_max_kg is not None:
            return round((self.adult_weight_min_kg + self.adult_weight_max_kg) / 2, 1)
        return None

    def monthly_cost_total(self) -> Optional[int]:
        """月度平均开销总和（用于推断预算）"""
        if not self.monthly_cost:
            return None
        return sum(self.monthly_cost.values())

    def is_long_hair(self) -> bool:
        """是否长毛（根据 grooming_needs 等级粗略判断：>=4 视为长毛/高美容需求）"""
        return (self.grooming_needs or 0) >= 4

    def get_section(self, title: str) -> str:
        """获取正文某个章节的内容（标题忽略大小写和空格）"""
        key = title.strip().lower()
        for k, v in self.description_sections.items():
            if k.strip().lower() == key:
                return v
        return ""

    def to_dict(self) -> dict:
        return {
            "breed_id": self.breed_id,
            "breed_name": self.breed_name,
            "breed_name_en": self.breed_name_en,
            "category": self.category.value,
            "size": self.size.value,
            "origin": self.origin,
            "adult_weight_min_kg": self.adult_weight_min_kg,
            "adult_weight_max_kg": self.adult_weight_max_kg,
            "adult_height_min_cm": self.adult_height_min_cm,
            "adult_height_max_cm": self.adult_height_max_cm,
            "weight_growth": {str(k): v for k, v in self.weight_growth.items()},
            "life_span_min": self.life_span_min,
            "life_span_max": self.life_span_max,
            "energy_level": self.energy_level,
            "grooming_needs": self.grooming_needs,
            "trainability": self.trainability,
            "social_needs": self.social_needs,
            "common_health_issues": list(self.common_health_issues),
            "daily_calorie_per_kg": self.daily_calorie_per_kg,
            "protein_ratio": self.protein_ratio,
            "fat_ratio": self.fat_ratio,
            "special_diet_notes": self.special_diet_notes,
            "monthly_cost": dict(self.monthly_cost),
            "description_sections": dict(self.description_sections),
        }


@dataclass
class NutritionStandard:
    """营养标准（从 nutrition.md 解析）"""

    calorie_formula: dict[str, Any] = field(default_factory=dict)
    ratios: dict[str, Any] = field(default_factory=dict)
    water_per_kg: dict[str, float] = field(default_factory=dict)
    feeding_guide: dict[str, Any] = field(default_factory=dict)
    functional_adjustments: dict[str, Any] = field(default_factory=dict)
    notes_markdown: str = ""


@dataclass
class HealthStandard:
    """健康护理标准（从 health.md 解析）"""

    vaccination: dict[str, Any] = field(default_factory=dict)
    deworming: dict[str, Any] = field(default_factory=dict)
    grooming: dict[str, Any] = field(default_factory=dict)
    checkup: dict[str, Any] = field(default_factory=dict)
    notes_markdown: str = ""


@dataclass
class BreedIndexEntry:
    """品种索引条目（来自合并版 MD 动态构建）"""

    breed_id: str
    name: str
    name_en: str
    size: PetSize

    @classmethod
    def from_dict(cls, d: dict, category: PetCategory) -> "BreedIndexEntry":
        return cls(
            breed_id=d["breed_id"],
            name=d["name"],
            name_en=d.get("name_en", ""),
            size=PetSize(d["size"]),
        )


@dataclass
class BreedIndex:
    """品种索引（从合并版 MD 动态构建）"""

    category: PetCategory
    total_breeds: int
    entries: list[BreedIndexEntry] = field(default_factory=list)

    def ids(self) -> list[str]:
        return [e.breed_id for e in self.entries]


# ============================================================
# 3. 宠物档案
# ============================================================


@dataclass
class InferredField:
    """推断字段的元数据

    每个自动填充的 INFERABLE 字段都会附带此对象，
    用于后续阶段展示"推断来源"并允许用户修改。
    """

    value: Any                    # 推断出的值
    source: str                   # 人类可读的推断来源说明
    field_name: str               # 对应字段名
    modified: bool = False        # 用户是否已覆盖修改此推断值

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "source": self.source,
            "field_name": self.field_name,
            "modified": self.modified,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "InferredField":
        return cls(**d)


@dataclass
class PetProfile:
    """宠物档案 - 核心输入数据

    所有字段都明确标注了优先级（见 FIELD_PRIORITY_MAP）
    """

    # ========== REQUIRED（必填项）==========
    category: PetCategory                         # 宠物类别：狗/猫
    breed_id: str                                 # 品种唯一 ID（关联知识库）
    breed_name: str                               # 品种展示名称

    # ========== INFERABLE（可推断项）==========
    age_months: Optional[int] = None              # 年龄（月）。None 表示未采集
    weight_kg: Optional[float] = None             # 体重（kg）
    life_stage: Optional[LifeStage] = None        # 生命周期阶段
    sterilized: Optional[bool] = None             # 是否绝育
    monthly_budget: Optional[int] = None          # 月度预算（元）
    body_condition: Optional[BodyCondition] = None # 体态评估
    size: Optional[PetSize] = None                # 体型分级

    # ========== ENHANCEMENT（增强项）==========
    gender: Optional[Gender] = None               # 性别
    diet_mode: Optional[DietMode] = None          # 饮食模式偏好
    food_allergies: list[str] = field(default_factory=list)   # 食物过敏史
    health_issues: list[str] = field(default_factory=list)    # 既往病史/健康问题
    functional_needs: list[FunctionalNeed] = field(default_factory=list)

    # ========== 元数据（不参与优先级映射）==========
    inferred_fields: dict[str, InferredField] = field(default_factory=dict)
    skipped_fields: list[str] = field(default_factory=list)
    image_analysis_raw: Optional[dict] = None
    notes: str = ""

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------

    def mark_inferred(self, field_name: str, value: Any, source: str) -> None:
        """记录某个字段为推断值，并写入 profile 对应属性"""
        setattr(self, field_name, value)
        self.inferred_fields[field_name] = InferredField(
            value=value,
            source=source,
            field_name=field_name,
            modified=False,
        )

    def user_overwrite(self, field_name: str, value: Any) -> None:
        """用户手动覆盖某个字段。若该字段之前是推断值，标记 modified"""
        setattr(self, field_name, value)
        if field_name in self.inferred_fields:
            self.inferred_fields[field_name].modified = True
            self.inferred_fields[field_name].value = value

    def get_unmodified_inferred(self) -> dict[str, InferredField]:
        """获取所有用户尚未修改的推断字段"""
        return {k: v for k, v in self.inferred_fields.items() if not v.modified}

    def infer_count(self) -> int:
        """推断字段总数（用于报告顶部提示）"""
        return len(self.inferred_fields)

    def to_dict(self) -> dict:
        """序列化为 dict（便于 JSON 落盘或调试）"""
        return {
            "category": self.category.value if self.category else None,
            "breed_id": self.breed_id,
            "breed_name": self.breed_name,
            "age_months": self.age_months,
            "weight_kg": self.weight_kg,
            "life_stage": self.life_stage.value if self.life_stage else None,
            "sterilized": self.sterilized,
            "monthly_budget": self.monthly_budget,
            "body_condition": self.body_condition.value if self.body_condition else None,
            "size": self.size.value if self.size else None,
            "gender": self.gender.value if self.gender else None,
            "diet_mode": self.diet_mode.value if self.diet_mode else None,
            "food_allergies": list(self.food_allergies),
            "health_issues": list(self.health_issues),
            "functional_needs": [n.value for n in self.functional_needs],
            "inferred_fields": {k: v.to_dict() for k, v in self.inferred_fields.items()},
            "skipped_fields": list(self.skipped_fields),
            "notes": self.notes,
        }


# ============================================================
# 3.5 预算规划（用户自定义预算 → 按比例分配 + 差额提示）
# ============================================================


_BUDGET_KEYS = ("food", "grooming", "medical", "supplies")
_BUDGET_LABELS: dict[str, str] = {
    "food": "饮食",
    "grooming": "美容",
    "medical": "医疗",
    "supplies": "用品",
}

# 预算状态判定阈值：与标准总额偏差 ±10% 以内视为 match
_BUDGET_TOLERANCE = 0.10


@dataclass
class BudgetPlan:
    """预算规划结果

    status 取值：
      - "below": 用户预算低于标准 10% 以上，需降级方案
      - "match": 用户预算与标准偏差 ±10% 以内，直接使用标准分配
      - "above": 用户预算高于标准 10% 以上，可升级方案
    """

    standard_total: int                         # 品种标准月度总额
    user_budget: int                            # 用户提供的月度预算
    diff: int                                   # 差额（负=不足，正=充裕）
    status: str                                 # below / match / above
    standard_breakdown: dict[str, int]          # 标准分项 {food, grooming, medical, supplies}
    allocated: dict[str, int]                   # 按用户预算比例分配的分项
    suggestions: list[str] = field(default_factory=list)  # 降级/升级建议（由 SKILL 指令填充）

    def to_dict(self) -> dict:
        return {
            "standard_total": self.standard_total,
            "user_budget": self.user_budget,
            "diff": self.diff,
            "status": self.status,
            "standard_breakdown": dict(self.standard_breakdown),
            "allocated": dict(self.allocated),
            "suggestions": list(self.suggestions),
        }

    def allocated_total(self) -> int:
        return sum(self.allocated.values())


def plan_budget(
    standard_cost: dict[str, int],
    user_budget: int,
) -> BudgetPlan:
    """根据用户预算和品种标准开销生成预算分配方案"""
    std = {k: standard_cost.get(k, 0) for k in _BUDGET_KEYS}
    standard_total = sum(std.values())

    if standard_total <= 0:
        raise ValueError("品种标准开销为 0，无法计算预算比例")

    diff = user_budget - standard_total
    threshold = standard_total * _BUDGET_TOLERANCE

    if diff < -threshold:
        status = "below"
    elif diff > threshold:
        status = "above"
    else:
        status = "match"

    # 按标准比例分配用户预算到各分项
    allocated: dict[str, int] = {}
    for key in _BUDGET_KEYS:
        ratio = std[key] / standard_total
        allocated[key] = round(user_budget * ratio)

    allocated_total = sum(allocated.values())
    if allocated_total != user_budget:
        max_key = max(allocated, key=allocated.get)
        allocated[max_key] += user_budget - allocated_total

    return BudgetPlan(
        standard_total=standard_total,
        user_budget=user_budget,
        diff=diff,
        status=status,
        standard_breakdown=std,
        allocated=allocated,
    )


def format_budget_plan(plan: BudgetPlan) -> str:
    """将 BudgetPlan 格式化为可读文本（供 exec 命令输出）"""
    lines = [
        f"标准月度总额: {plan.standard_total} 元",
        f"用户预算: {plan.user_budget} 元",
        f"差额: {plan.diff:+d} 元",
        f"状态: {plan.status}",
        "",
        "标准分项:",
    ]
    for k in _BUDGET_KEYS:
        lines.append(f"  {_BUDGET_LABELS[k]}: {plan.standard_breakdown[k]} 元")
    lines.append("")
    lines.append("用户预算分配:")
    for k in _BUDGET_KEYS:
        lines.append(f"  {_BUDGET_LABELS[k]}: {plan.allocated[k]} 元")
    return "\n".join(lines)


# ============================================================
# 4. 知识库加载器
# ============================================================


# 合并版 MD 中每个品种块的锚点格式：<!-- breed: dog_001 -->
_BREED_MARKER_RE = re.compile(
    r"<!--\s*breed:\s*([a-z]+_\d+)\s*-->",
    re.IGNORECASE,
)

_FRONT_MATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n?(.*)$",
    re.DOTALL,
)


@dataclass
class ParsedMarkdown:
    front_matter: dict[str, Any]
    body: str


def parse_markdown_text(text: str, source_label: str = "<text>") -> ParsedMarkdown:
    """解析 MD 文本字符串，分离 YAML front matter 和 Markdown 正文"""
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        raise ValueError(f"{source_label}: 缺少 YAML front matter（块须以 --- 开头和结尾）")
    yaml_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{source_label}: front matter YAML 解析错误 -> {exc}") from exc
    if not isinstance(fm, dict):
        raise ValueError(f"{source_label}: front matter 根节点必须为 dict/map 类型")
    return ParsedMarkdown(front_matter=fm, body=body)


def parse_markdown_file(path: Path) -> ParsedMarkdown:
    """读取 MD 文件，分离 YAML front matter 和 Markdown 正文"""
    text = path.read_text(encoding="utf-8")
    return parse_markdown_text(text, source_label=path.name)


def split_merged_breeds_file(path: Path) -> dict[str, str]:
    """按 `<!-- breed: XXX -->` 锚点将合并版 MD 拆分为 {breed_id: 品种块文本}"""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    markers = [(m.start(), m.group(1)) for m in _BREED_MARKER_RE.finditer(text)]
    chunks: dict[str, str] = {}
    n = len(markers)
    for i, (start, bid) in enumerate(markers):
        line_end = text.find("\n", start)
        chunk_start = line_end + 1 if line_end != -1 else len(text)
        chunk_end = markers[i + 1][0] if i + 1 < n else len(text)
        chunk = text[chunk_start:chunk_end].lstrip("\n").rstrip() + "\n"
        chunks[bid] = chunk
    return chunks


def split_markdown_sections(body: str) -> dict[str, str]:
    """将 Markdown 正文按 `## 标题` 分块为 {标题: 内容}"""
    sections: dict[str, str] = {}
    current_title = "__intro__"
    current_lines: list[str] = []

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        m = re.match(r"^\s*#{2,3}\s+(.+)$", line)
        if m:
            if current_lines:
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_title] = "\n".join(current_lines).strip()

    if not sections.get("__intro__"):
        sections.pop("__intro__", None)
    return sections


def _get(d: dict, key: str, default: Any = None) -> Any:
    if key in d:
        return d[key]
    return d.get(key, default)


def _safe_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _build_breed_from_parsed(parsed: ParsedMarkdown, source_label: str) -> Breed:
    """从已解析的 ParsedMarkdown 构建 Breed 对象"""
    fm = parsed.front_matter
    sections = split_markdown_sections(parsed.body)

    required = ["breed_id", "breed_name", "breed_name_en", "category", "size"]
    missing = [k for k in required if k not in fm]
    if missing:
        raise ValueError(f"{source_label}: front matter 缺少必填字段: {missing}")

    wg_raw = fm.get("weight_growth", {}) or {}
    weight_growth: dict[int, float] = {}
    for k, v in wg_raw.items():
        try:
            weight_growth[int(k)] = float(v)
        except (TypeError, ValueError):
            continue

    monthly_cost_raw = fm.get("monthly_cost", {}) or {}
    monthly_cost: dict[str, int] = {}
    for k, v in monthly_cost_raw.items():
        try:
            monthly_cost[k] = int(v)
        except (TypeError, ValueError):
            continue

    category = PetCategory(fm["category"])
    size = PetSize(fm["size"])

    return Breed(
        breed_id=fm["breed_id"],
        breed_name=fm["breed_name"],
        breed_name_en=fm["breed_name_en"],
        category=category,
        size=size,
        origin=_get(fm, "origin", ""),
        adult_weight_min_kg=_safe_float(_get(fm, "adult_weight_min_kg")),
        adult_weight_max_kg=_safe_float(_get(fm, "adult_weight_max_kg")),
        adult_height_min_cm=_safe_float(_get(fm, "adult_height_min_cm")),
        adult_height_max_cm=_safe_float(_get(fm, "adult_height_max_cm")),
        weight_growth=weight_growth,
        life_span_min=_safe_int(_get(fm, "life_span_min")),
        life_span_max=_safe_int(_get(fm, "life_span_max")),
        energy_level=_safe_int(_get(fm, "energy_level")),
        grooming_needs=_safe_int(_get(fm, "grooming_needs")),
        trainability=_safe_int(_get(fm, "trainability")),
        social_needs=_safe_int(_get(fm, "social_needs")),
        common_health_issues=list(_get(fm, "common_health_issues", []) or []),
        daily_calorie_per_kg=_safe_float(_get(fm, "daily_calorie_per_kg")),
        protein_ratio=_safe_float(_get(fm, "protein_ratio")),
        fat_ratio=_safe_float(_get(fm, "fat_ratio")),
        special_diet_notes=_get(fm, "special_diet_notes", ""),
        monthly_cost=monthly_cost,
        description_sections=sections,
    )


def _build_breed_from_text(text: str, source_label: str) -> Breed:
    """从 MD 文本块构建 Breed 对象（用于合并版 MD 切分后）"""
    parsed = parse_markdown_text(text, source_label=source_label)
    return _build_breed_from_parsed(parsed, source_label=source_label)


def _build_nutrition(path: Path) -> NutritionStandard:
    """解析 nutrition.md"""
    parsed = parse_markdown_file(path)
    fm = parsed.front_matter
    return NutritionStandard(
        calorie_formula=fm.get("calorie_formula", {}) or {},
        ratios=fm.get("ratios", {}) or {},
        water_per_kg=fm.get("water_per_kg", {}) or {},
        feeding_guide=fm.get("feeding_guide", {}) or {},
        functional_adjustments=fm.get("functional_adjustments", {}) or {},
        notes_markdown=parsed.body,
    )


def _build_health(path: Path) -> HealthStandard:
    """解析 health.md"""
    parsed = parse_markdown_file(path)
    fm = parsed.front_matter
    return HealthStandard(
        vaccination=fm.get("vaccination", {}) or {},
        deworming=fm.get("deworming", {}) or {},
        grooming=fm.get("grooming", {}) or {},
        checkup=fm.get("checkup", {}) or {},
        notes_markdown=parsed.body,
    )


class KnowledgeLoader:
    """知识库加载器

    品种库读取优先级：
      1. 合并版 MD 文件：dog_breeds.md / cat_breeds.md（按 `<!-- breed:XXX -->` 锚点切分）

    缓存策略：
      - 首次加载后，结果缓存在实例属性中
      - 品种按 breed_id 缓存
      - 合并版 MD 切分结果按 category 单独缓存
    """

    def __init__(self, data_root: Optional[Path] = None) -> None:
        self._data_root = Path(data_root) if data_root else DATA_ROOT
        self._breed_cache: dict[str, Breed] = {}
        self._index_cache: dict[PetCategory, BreedIndex] = {}
        self._merged_chunk_cache: dict[PetCategory, dict[str, str]] = {}
        self._nutrition_cache: Optional[NutritionStandard] = None
        self._health_cache: Optional[HealthStandard] = None

    def _breeds_merged_md(self, category: PetCategory) -> Path:
        if category == PetCategory.DOG:
            return self._data_root / "dog_breeds.md"
        if category == PetCategory.CAT:
            return self._data_root / "cat_breeds.md"
        raise ValueError(f"未知 category: {category}")

    def _ensure_merged_loaded(self, category: PetCategory) -> dict[str, str]:
        if category not in self._merged_chunk_cache:
            self._merged_chunk_cache[category] = split_merged_breeds_file(
                self._breeds_merged_md(category)
            )
        return self._merged_chunk_cache[category]

    def load_breed_index(self, category: PetCategory) -> BreedIndex:
        """从合并版 MD 的锚点 + front matter 自动构建品种索引"""
        if category in self._index_cache:
            return self._index_cache[category]

        merged_chunks = self._ensure_merged_loaded(category)
        if not merged_chunks:
            raise FileNotFoundError(f"缺少合并版品种库文件: {self._breeds_merged_md(category)}")

        entries: list[BreedIndexEntry] = []
        for breed_id, chunk_text in merged_chunks.items():
            try:
                parsed = parse_markdown_text(
                    chunk_text, source_label=f"{self._breeds_merged_md(category).name}:{breed_id}"
                )
                fm = parsed.front_matter
                entries.append(BreedIndexEntry(
                    breed_id=fm["breed_id"],
                    name=fm.get("breed_name", ""),
                    name_en=fm.get("breed_name_en", ""),
                    size=PetSize(fm.get("size", "medium")),
                ))
            except (ValueError, KeyError, yaml.YAMLError):
                continue

        index = BreedIndex(category=category, total_breeds=len(entries), entries=entries)
        self._index_cache[category] = index
        return index

    def load_breed(self, breed_id: str) -> Breed:
        """根据 breed_id 加载单个品种"""
        if breed_id in self._breed_cache:
            return self._breed_cache[breed_id]

        if breed_id.startswith("dog_"):
            category = PetCategory.DOG
        elif breed_id.startswith("cat_"):
            category = PetCategory.CAT
        else:
            raise ValueError(f"breed_id 格式非法: {breed_id}，必须以 dog_ 或 cat_ 开头")

        merged_chunks = self._ensure_merged_loaded(category)
        if breed_id in merged_chunks:
            source_label = f"{self._breeds_merged_md(category).name}:{breed_id}"
            breed = _build_breed_from_text(merged_chunks[breed_id], source_label=source_label)
            self._breed_cache[breed_id] = breed
            return breed

        index = self.load_breed_index(category)
        valid_ids = index.ids()
        raise FileNotFoundError(
            f"找不到品种 {breed_id}：合并版 MD 中未收录；"
            f"该类别有效 ID（前10个）: {valid_ids[:10]}...（共 {len(valid_ids)} 个）"
        )


# 常见别名映射（用户常用简称 -> 知识库完整名）
    _BREED_ALIASES: dict[str, str] = {
        '英短': '英国短毛猫',
        '美短': '美国短毛猫',
        '加菲猫': '异国短毛猫',
        '哈士奇': '西伯利亚雪橇犬',
        '二哈': '西伯利亚雪橇犬',
        '柯基': '威尔士柯基犬',
        '金毛': '金毛寻回犬',
        '金毛犬': '金毛寻回犬',
        '金毛寻回': '金毛寻回犬',
        '拉布拉多': '拉布拉多犬',
        '德牧': '德国牧羊犬',
        '边牧': '边境牧羊犬',
        '法斗': '法国斗牛犬',
        '约克夏': '约克夏㹴',
        '吉娃娃': '吉娃娃',
        '缅因': '缅因猫',
        '布偶': '布偶猫',
        '折耳': '苏格兰折耳猫',
        '波斯': '波斯猫',
        '暹罗': '暹罗猫',
        '斯芬克斯': '斯芬克斯无毛猫',
        '无毛猫': '斯芬克斯无毛猫',
        '狸花': '狸花猫',
        '中华田园猫': '狸花猫',
    }

    def load_breed_by_name(self, name: str) -> Optional[Breed]:
        """按品种中文名模糊匹配第一个命中的品种（支持别名展开）"""
        resolved = self._BREED_ALIASES.get(name, name)
        for cat in (PetCategory.DOG, PetCategory.CAT):
            idx = self.load_breed_index(cat)
            for entry in idx.entries:
                if entry.name == resolved or resolved in entry.name:
                    try:
                        return self.load_breed(entry.breed_id)
                    except FileNotFoundError:
                        continue
        return None

    def search_breeds(self, keyword: str) -> list[BreedIndexEntry]:
        """按关键字（中文名/英文名/ID/别名）搜索品种索引条目"""
        kw = keyword.strip().lower()
        kw_aliased = self._BREED_ALIASES.get(keyword.strip(), keyword).lower()
        result: list[BreedIndexEntry] = []
        for cat in (PetCategory.DOG, PetCategory.CAT):
            idx = self.load_breed_index(cat)
            for entry in idx.entries:
                if (
                    kw in entry.breed_id.lower()
                    or kw in entry.name
                    or kw in entry.name_en.lower()
                    or kw_aliased in entry.name
                ):
                    result.append(entry)
        return result

    def load_all_breeds(self, category: PetCategory) -> list[Breed]:
        """加载某类别所有品种"""
        idx = self.load_breed_index(category)
        breeds: list[Breed] = []
        for entry in idx.entries:
            try:
                breeds.append(self.load_breed(entry.breed_id))
            except FileNotFoundError:
                continue
        return breeds

    def list_breed_ids(self, category: PetCategory) -> list[str]:
        return self.load_breed_index(category).ids()

    def list_existing_breed_ids(self, category: PetCategory) -> list[str]:
        return self.list_breed_ids(category)

    def list_missing_breed_ids(self, category: PetCategory) -> list[str]:
        return []

    def nutrition(self) -> NutritionStandard:
        if self._nutrition_cache is None:
            path = self._data_root / "nutrition.md"
            if not path.exists():
                raise FileNotFoundError(f"缺少营养标准文件: {path}")
            self._nutrition_cache = _build_nutrition(path)
        return self._nutrition_cache

    def health(self) -> HealthStandard:
        if self._health_cache is None:
            path = self._data_root / "health.md"
            if not path.exists():
                raise FileNotFoundError(f"缺少健康标准文件: {path}")
            self._health_cache = _build_health(path)
        return self._health_cache

    def invalidate(self) -> None:
        """强制清空所有缓存"""
        self._breed_cache.clear()
        self._index_cache.clear()
        self._merged_chunk_cache.clear()
        self._nutrition_cache = None
        self._health_cache = None


# ============================================================
# 5. 知识库验证
# ============================================================


def run_verify_knowledge_loader() -> int:
    """验证知识库加载正确性"""
    kl = KnowledgeLoader()
    errors: list[str] = []

    print("=" * 60)
    print("阶段一 知识库加载器验证")
    print("=" * 60)

    # ---------- 索引 ----------
    print("\n[1] 品种索引（从合并版 MD 动态构建）")
    for cat, label in [(PetCategory.DOG, "犬类"), (PetCategory.CAT, "猫类")]:
        idx = kl.load_breed_index(cat)
        all_ids = idx.ids()
        print(f"  ✓ {label}: 合并版 MD 收录 {len(all_ids)} 个品种")
        if all_ids:
            print(f"      品种列表: {all_ids}")

    # ---------- 示例品种逐个加载 ----------
    print("\n[2] 示例品种加载验证（狗10个 + 猫10个）")
    dog_examples = [f"dog_{i:03d}" for i in [1, 2, 3, 5, 7, 19, 21, 26, 39, 40]]
    cat_examples = [f"cat_{i:03d}" for i in [1, 2, 9, 10, 11, 30, 31, 41, 47, 55]]

    for bid in dog_examples + cat_examples:
        try:
            b = kl.load_breed(bid)
            median = b.adult_weight_median_kg()
            cost = b.monthly_cost_total()
            sections = list(b.description_sections.keys())
            extras = []
            if median:
                extras.append(f"中位体重 {median}kg")
            if cost:
                extras.append(f"月度开销约 {cost}元")
            extras.append(f"描述章节 {len(sections)} 个")
            print(f"  ✓ {bid:<8} {b.breed_name:<14} {' | '.join(extras)}")
        except Exception as exc:
            errors.append(f"{bid}: {exc}")
            print(f"  ✗ {bid:<8} 失败: {exc}")

    # ---------- 名称搜索 ----------
    print("\n[3] 名称搜索验证")
    for kw in ["金毛", "布偶", "Chihuahua"]:
        hits = kl.search_breeds(kw)
        names = [f"{e.breed_id}({e.name})" for e in hits[:3]]
        print(f"  搜索 '{kw}' → {len(hits)} 条命中: {names}")
    hit = kl.load_breed_by_name("英短")
    print(f"  精确匹配 '英短' → {hit.breed_name if hit else '未找到'}")

    # ---------- 营养标准 ----------
    print("\n[4] 营养标准加载")
    try:
        nut = kl.nutrition()
        print(f"  ✓ calorie_formula.dog.factors: {list(nut.calorie_formula['dog']['factors'].keys())}")
        print(f"  ✓ ratios.dog 生命周期: {list(nut.ratios['dog'].keys())}")
        print(f"  ✓ functional_adjustments 需求: {list(nut.functional_adjustments.keys())}")
        print(f"  ✓ 营养正文长度: {len(nut.notes_markdown)} 字符")
    except Exception as exc:
        errors.append(f"nutrition: {exc}")
        print(f"  ✗ 失败: {exc}")

    # ---------- 健康标准 ----------
    print("\n[5] 健康标准加载")
    try:
        h = kl.health()
        dog_core = len(h.vaccination.get("dog", {}).get("core", []))
        dog_non_core = len(h.vaccination.get("dog", {}).get("non_core", []))
        cat_core = len(h.vaccination.get("cat", {}).get("core", []))
        print(f"  ✓ 犬疫苗 core({dog_core})+non_core({dog_non_core}) 种")
        print(f"  ✓ 猫疫苗 core({cat_core}) 种")
        print(f"  ✓ 犬驱虫体内(成犬): {h.deworming['dog']['internal']['adult']['frequency']}")
        print(f"  ✓ 犬驱虫体外(成犬): {h.deworming['dog']['external']['adult']['frequency']}")
        print(f"  ✓ 美容周期: short_hair/long_hair = {len(h.grooming)} 套")
        print(f"  ✓ 体检: 犬成犬 {h.checkup['dog']['adult']['frequency']}")
        print(f"  ✓ 健康正文长度: {len(h.notes_markdown)} 字符")
    except Exception as exc:
        errors.append(f"health: {exc}")
        print(f"  ✗ 失败: {exc}")

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    if errors:
        print(f"[FAIL] 共 {len(errors)} 个错误:")
        for e in errors:
            print(f"  • {e}")
        return 1
    print("[PASS] 全部检查通过 ✓")
    print(
        "品种收录情况：犬类 {dog_total} 个，猫类 {cat_total} 个".format(
            dog_total=len(kl.list_breed_ids(PetCategory.DOG)),
            cat_total=len(kl.list_breed_ids(PetCategory.CAT)),
        )
    )
    return 0


# ============================================================
# 6. 合并品种 MD
# ============================================================


_SPLIT_MARKER_TEMPLATE = "<!-- breed: {breed_id} -->\n"


def merge_one_breeds(category_dir: Path, output_file: Path) -> None:
    """合并某类别（dog_breeds / cat_breeds）目录下的单品种 MD 为合并版"""
    md_files = [
        p for p in category_dir.glob("*.md")
        if p.name != "_index.md"
    ]
    md_files.sort(key=lambda p: p.stem)

    blocks: list[str] = []
    title = {
        "dog_breeds": "犬类品种库（合并版）",
        "cat_breeds": "猫类品种库（合并版）",
    }[category_dir.name]

    header_parts = [
        f"# {title}",
        "",
        f"> 共收录 **{len(md_files)}** 个品种（按 `breed_id` 升序排列）。",
        f"> 本文件自动合并生成，每品种独立使用 `<!-- breed: XXX -->` HTML 注释锚点分隔。",
        "",
    ]

    breed_id_re = re.compile(r'breed_id:\s*"([^"]+)"')

    for md in md_files:
        raw = md.read_text(encoding="utf-8")
        m = breed_id_re.search(raw)
        breed_id = m.group(1) if m else md.stem

        block = _SPLIT_MARKER_TEMPLATE.format(breed_id=breed_id) + raw.rstrip() + "\n"
        blocks.append(block)

    output_text = "\n".join(header_parts) + "\n\n".join(blocks) + "\n"
    output_file.write_text(output_text, encoding="utf-8")
    print(f"✓ 合并完成：{output_file.relative_to(Path.cwd())}（{len(md_files)} 个品种，按 breed_id 升序）")


def run_merge_breeds() -> None:
    """合并 dog_breeds / cat_breeds 目录为单文件 MD"""
    for sub_dir, out_name in [("dog_breeds", "dog_breeds.md"), ("cat_breeds", "cat_breeds.md")]:
        category_dir = DATA_ROOT / sub_dir
        output_file = DATA_ROOT / out_name
        if not category_dir.is_dir():
            print(f"! 跳过：{category_dir} 不存在")
            continue
        merge_one_breeds(category_dir, output_file)


# ============================================================
# 7. Markdown 排版规范化
# ============================================================


_DEFAULT_TIDY_FILES = [
    _ROOT / "readme.md",
    _ROOT / "SKILL.md",
    _ROOT / "knowledge" / "nutrition.md",
    _ROOT / "knowledge" / "health.md",
    _ROOT / "knowledge" / "dog_breeds.md",
    _ROOT / "knowledge" / "cat_breeds.md",
    _ROOT / "knowledge" / "constraints.md",
    _ROOT / "examples" / "example1-talk.md",
    _ROOT / "examples" / "example2-photo.md",
    _ROOT / "examples" / "example3-budget.md",
    _ROOT / "examples" / "example4-test.md",
]

_TAB_RE = re.compile(r"\t")
_HEADING_RE = re.compile(r"^ {0,3}#{1,6}(\s|$)")
_HR_RE = re.compile(r"^ {0,3}(-{3,}|\*{3,}|_{3,})\s*$")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_LIST_ITEM_RE = re.compile(r"^( {0,3}[-*+]\s+|\s*\d+\.\s+)")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")


def _strip_line(s: str) -> str:
    s = _TAB_RE.sub("    ", s)
    return s.rstrip() + "\n"


def _normalize_list_bullet(line: str) -> str:
    m = re.match(r"^( *)[*+](\s+)", line)
    if m:
        return f"{m.group(1)}-{m.group(2)}{line[m.end():]}"
    return line


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def _split_cells(line: str) -> list[str]:
    s = line.rstrip("\n").strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _align_table_block(block: list[str]) -> list[str]:
    if len(block) < 2:
        return block
    header_cells = _split_cells(block[0])
    sep_match = _TABLE_SEP_RE.match(block[1])
    if not sep_match:
        return block
    sep_raw = [c.strip() for c in _split_cells(block[1])]
    n_cols = len(header_cells)
    if len(sep_raw) != n_cols:
        return block

    data_cells_list: list[list[str]] = []
    for ln in block[2:]:
        if not _TABLE_ROW_RE.match(ln):
            return block
        cells = _split_cells(ln)
        if len(cells) < n_cols:
            cells = cells + [""] * (n_cols - len(cells))
        elif len(cells) > n_cols:
            cells = cells[:n_cols]
        data_cells_list.append(cells)

    def display_width(text: str) -> int:
        w = 0
        for ch in text:
            if "\u4e00" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u303f" or "\uff00" <= ch <= "\uffef":
                w += 2
            else:
                w += 1
        return w

    widths = [display_width(h) for h in header_cells]
    for cells in data_cells_list:
        for i, c in enumerate(cells):
            widths[i] = max(widths[i], display_width(c))
    widths = [max(w, 3) for w in widths]

    alignments = []
    for s in sep_raw:
        left = s.startswith(":")
        right = s.endswith(":")
        if left and right:
            alignments.append("center")
        elif right and not left:
            alignments.append("right")
        else:
            alignments.append("left")

    def pad_cell(text: str, width: int, align: str) -> str:
        dw = display_width(text)
        pad = width - dw
        if pad < 0:
            pad = 0
        if align == "center":
            l = pad // 2
            r = pad - l
        elif align == "right":
            l = pad
            r = 0
        else:
            l = 0
            r = pad
        return " " * l + text + " " * r

    def pad_sep(width: int, align: str) -> str:
        if align == "center":
            return ":" + "-" * (width - 2) + ":"
        elif align == "right":
            return "-" * (width - 1) + ":"
        else:
            return "-" * width

    out = []
    header_str = "| " + " | ".join(
        pad_cell(header_cells[i], widths[i], alignments[i]) for i in range(n_cols)
    ) + " |"
    out.append(header_str + "\n")
    sep_str = "| " + " | ".join(pad_sep(widths[i], alignments[i]) for i in range(n_cols)) + " |"
    out.append(sep_str + "\n")
    for cells in data_cells_list:
        row = "| " + " | ".join(
            pad_cell(cells[i], widths[i], alignments[i]) for i in range(n_cols)
        ) + " |"
        out.append(row + "\n")
    return out


def tidy_text(text: str) -> str:
    """对 MD 文本进行排版规范化（仅调整格式，不更改语义）"""
    raw_lines = text.splitlines(keepends=True)

    # Step 1: 行尾空格 + Tab 展开 + 统一列表符号
    lines: list[str] = []
    in_fence = False
    fence_mark = ""
    for ln in raw_lines:
        s = _strip_line(ln)
        fm = _FENCE_RE.match(s)
        if fm:
            mark = fm.group(1)
            if not in_fence:
                in_fence = True
                fence_mark = mark[0] * 3
            elif s.lstrip().startswith(fence_mark):
                in_fence = False
                fence_mark = ""
            lines.append(s)
            continue
        if not in_fence:
            s = _normalize_list_bullet(s)
        lines.append(s)

    # Step 2: frontmatter 边界
    frontmatter_end = -1
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                frontmatter_end = i
                break

    # Step 3: 表格块原地替换
    i = 0
    processed: list[str] = []
    while i < len(lines):
        if frontmatter_end >= 0 and i <= frontmatter_end:
            processed.append(lines[i])
            i += 1
            continue
        if _FENCE_RE.match(lines[i]):
            processed.append(lines[i])
            i += 1
            while i < len(lines) and not _FENCE_RE.match(lines[i]):
                processed.append(lines[i])
                i += 1
            if i < len(lines):
                processed.append(lines[i])
                i += 1
            continue
        if _TABLE_ROW_RE.match(lines[i]) and i + 1 < len(lines) and _TABLE_SEP_RE.match(lines[i + 1]):
            block = [lines[i], lines[i + 1]]
            j = i + 2
            while j < len(lines) and _TABLE_ROW_RE.match(lines[j]):
                block.append(lines[j])
                j += 1
            processed.extend(_align_table_block(block))
            i = j
            continue
        processed.append(lines[i])
        i += 1
    lines = processed

    # Step 4: 标题/代码块/分割线 前后空行
    out: list[str] = []

    def prev_nonblank(offset: int = 1) -> str | None:
        k = len(out) - 1
        skipped = 0
        while k >= 0:
            if not _is_blank(out[k]):
                if skipped == offset - 1:
                    return out[k]
                skipped += 1
            k -= 1
        return None

    def last_out() -> str:
        return out[-1] if out else "\n"

    in_fence = False
    in_frontmatter = 0
    for idx, ln in enumerate(lines):
        if frontmatter_end >= 0 and idx == 0 and ln.strip() == "---":
            in_frontmatter = 1
            out.append(ln)
            continue
        if in_frontmatter == 1 and ln.strip() == "---":
            in_frontmatter = 2
            out.append(ln)
            continue
        if in_frontmatter == 1:
            out.append(ln)
            continue

        if _FENCE_RE.match(ln):
            if not in_fence and out and not _is_blank(last_out()) and in_frontmatter != 1:
                out.append("\n")
            out.append(ln)
            in_fence = not in_fence
            if not in_fence:
                if idx + 1 < len(lines) and not _is_blank(lines[idx + 1]):
                    out.append("\n")
            continue
        if in_fence:
            out.append(ln)
            continue

        if _is_blank(ln):
            if out and not _is_blank(last_out()):
                out.append("\n")
            continue

        if _HEADING_RE.match(ln):
            if out and not _is_blank(last_out()):
                out.append("\n")
            out.append(ln)
            if idx + 1 < len(lines) and not _is_blank(lines[idx + 1]) and not _HEADING_RE.match(lines[idx + 1]):
                out.append("\n")
            continue

        if _HR_RE.match(ln) and not (in_frontmatter in (1, 2) and ln.strip() == "---"):
            if out and not _is_blank(last_out()):
                out.append("\n")
            out.append(ln)
            if idx + 1 < len(lines) and not _is_blank(lines[idx + 1]):
                out.append("\n")
            continue

        prev_nb = prev_nonblank(1)
        is_list = bool(_LIST_ITEM_RE.match(ln))
        is_table = bool(_TABLE_ROW_RE.match(ln))

        prev_is_list = bool(prev_nb and _LIST_ITEM_RE.match(prev_nb))
        prev_is_table = bool(prev_nb and _TABLE_ROW_RE.match(prev_nb))
        prev_is_heading = bool(prev_nb and _HEADING_RE.match(prev_nb))
        prev_is_fence = bool(prev_nb and _FENCE_RE.match(prev_nb))
        prev_is_hr = bool(prev_nb and _HR_RE.match(prev_nb))

        need_blank_before = False
        if out and not _is_blank(last_out()):
            if prev_is_heading or prev_is_hr or prev_is_fence:
                pass
            elif (is_list and not prev_is_list) or (not is_list and prev_is_list):
                need_blank_before = True
            elif is_table and not prev_is_table:
                need_blank_before = True
            elif not is_table and prev_is_table:
                need_blank_before = True
            elif not is_list and not is_table and not prev_is_list and not prev_is_table:
                need_blank_before = True

        if need_blank_before:
            out.append("\n")
        out.append(ln)

    # Step 5: 压缩连续空行 + 首尾空白处理
    final: list[str] = []
    blank_run = 0
    for ln in out:
        if _is_blank(ln):
            blank_run += 1
            if blank_run <= 1:
                final.append("\n")
        else:
            blank_run = 0
            final.append(ln)

    while final and _is_blank(final[0]):
        final.pop(0)
    if final and not final[-1].endswith("\n"):
        final[-1] = final[-1] + "\n"
    if not final:
        return "\n"
    while len(final) >= 2 and _is_blank(final[-1]) and _is_blank(final[-2]):
        final.pop()
    if not final[-1].endswith("\n"):
        final[-1] = final[-1] + "\n"
    return "".join(final)


def tidy_file(path: Path) -> tuple[bool, str]:
    """对单个文件执行排版规范化，返回 (是否改变, 文件名)"""
    original = path.read_text(encoding="utf-8")
    normalized = tidy_text(original)
    changed = original != normalized
    if changed:
        path.write_text(normalized, encoding="utf-8")
    return changed, path.name


def run_tidy_md(file_args: list[str] | None = None) -> int:
    """MD 排版规范化入口"""
    if file_args:
        files = [Path(a).resolve() for a in file_args]
    else:
        files = list(_DEFAULT_TIDY_FILES)

    total = 0
    modified = 0
    for f in files:
        if not f.exists():
            print(f"[SKIP] {f} not found")
            continue
        total += 1
        changed, name = tidy_file(f)
        if changed:
            modified += 1
            print(f"[TIDIED] {name}")
        else:
            print(f"[OK]     {name}")
    print(f"\n合计 {total} 个文件，{modified} 个调整排版，{total - modified} 个无需改动。")
    return 0


# ============================================================
# 8. 统一 CLI 入口
# ============================================================


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pet_care_core",
        description="宠物护理技能核心脚本",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # verify
    p_verify = subparsers.add_parser("verify", help="验证知识库加载正确性")

    # merge-breeds
    p_merge = subparsers.add_parser("merge-breeds", help="合并单品种 MD 为合并版")

    # tidy-md
    p_tidy = subparsers.add_parser("tidy-md", help="Markdown 排版规范化")
    p_tidy.add_argument("files", nargs="*", help="指定 MD 文件路径（不传则处理内置列表）")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "verify":
        return run_verify_knowledge_loader()
    elif args.command == "merge-breeds":
        run_merge_breeds()
        return 0
    elif args.command == "tidy-md":
        return run_tidy_md(args.files if args.files else None)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
