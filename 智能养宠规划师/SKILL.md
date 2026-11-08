---
name: petcare-planning
description: 根据宠物品种、体重、年龄等信息生成月度养宠规划（预算/健康护理/饮食计划/陪伴训练），内置犬猫品种知识库。触发词：养宠规划、宠物月度计划、养宠预算、宠物饮食计划、宠物健康护理、养狗养猫多少钱、养宠年度规划、宠物成长计划、养宠月度开销、养猫养狗成本核算、宠物照料方案、宠物健康管理

user-invocable: true
---

# Pet Care Planning Skill

根据宠物信息生成月度养宠规划，涵盖预算明细、健康护理、饮食计划、陪伴训练四大模块。

> **⚠️ 行为约束**：执行本 Skill 前，必须先阅读 `knowledge/constraints.md` 并严格遵守。该文档定义了数据来源、用户信息处理、输出范围、防幻觉等强制约束。

## 何时触发

### 正向触发

- 用户提到"养宠规划""月度宠物计划""宠物月报"等综合规划需求
- 用户询问"养狗/养猫一个月花多少钱""宠物预算""养宠开销"
- 用户询问"宠物每天喂多少""宠物饮食""宠物营养""猫/狗每天吃多少克"
- 用户询问"宠物疫苗""驱虫周期""体检频率""美容周期"等健康护理问题
- 用户提到宠物品种 + 需要建议（如"我养了一只金毛，需要什么计划"）
- 用户提到功能性需求（如"狗狗减肥""猫泌尿护理""美毛""关节护理"）

### 负向排除

- 用户仅询问医疗诊断（如"狗狗呕吐怎么办"）→ 建议就医，不生成规划
- 用户仅要求识别品种（如"帮我看看这是什么猫"）→ 仅识别，不生成规划
- 用户仅查询百科知识（如"金毛寿命多少"）→ 直接回答
- 用户在调试代码本身 → 这是开发任务，不是养宠规划

## 执行流程

### 第一步：采集宠物信息

按以下优先级采集用户输入，缺失字段从知识库推断：

| 优先级 | 字段                                                                               | 缺失处理                                                                     |
| ------ | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 必填   | category（猫/狗）、breed_id 或 breed_name                                          | 立即追问，流程阻塞                                                           |
| 可推断 | size、weight_kg、age_months、sterilized、monthly_budget、body_condition            | 从品种库自动填充；若用户主动提供月度预算数字，作为自定义预算触发预算方案计算 |
| 派生   | life_stage（由 age_months 自动计算：≤12 月=puppy/kitten，12-84=adult，>84=senior） | 无需询问、无需确认，自动派生                                                 |
| 增强   | gender、diet_mode、food_allergies、health_issues、functional_needs                 | 跳过，计划生成后统一追问                                                     |

**functional_needs 可选值**：weight_loss（减肥）、weight_gain（增肥）、beauty_coat（美毛）、joint_care（关节护理）、urinary_care（泌尿护理）、hairball（化毛）、tear_stain（去泪痕）、dental_care（口腔护理）

### 第二步：从知识库加载品种数据

使用 `exec` 工具运行以下命令加载品种数据：

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from pet_care_core import KnowledgeLoader
kl = KnowledgeLoader()
breed = kl.load_breed('dog_001')
print(f'品种: {breed.breed_name}')
print(f'体型: {breed.size}')
print(f'体重范围: {breed.adult_weight_min_kg}-{breed.adult_weight_max_kg} kg')
print(f'每日热量: {breed.daily_calorie_per_kg} kcal/kg')
print(f'蛋白质比例: {breed.protein_ratio}')
print(f'脂肪比例: {breed.fat_ratio}')
print(f'运动量: {breed.energy_level}/5')
print(f'美容需求: {breed.grooming_needs}/5')
print(f'训练性: {breed.trainability}/5')
print(f'常见健康问题: {breed.common_health_issues}')
print(f'饮食注意: {breed.special_diet_notes}')
print(f'月度开销: {breed.monthly_cost}')
print(f'月度开销合计: {breed.monthly_cost_total()} 元')
"
```

按品种名搜索：

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from pet_care_core import KnowledgeLoader
kl = KnowledgeLoader()
entries = kl.search_breeds('金毛')
for e in entries:
    print(f'{e.breed_id}: {e.name} ({e.name_en})')
"
```

加载营养和健康标准：

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from pet_care_core import KnowledgeLoader
kl = KnowledgeLoader()
n = kl.nutrition()
print('=== 营养标准 ===')
for cat in ['dog', 'cat']:
    formula = n.calorie_formula[cat]
    print(f'{cat} RER: {formula[\"rer_expr\"]}')
    for stage, mult in formula['factors'].items():
        print(f'  {stage}: x{mult}')
h = kl.health()
print('=== 健康标准 ===')
for cat in ['dog', 'cat']:
    core = [v['name'] for v in h.vaccination[cat]['core']]
    print(f'{cat} 核心疫苗: {core}')
    internal = h.deworming[cat]['internal']['adult']
    external = h.deworming[cat]['external']['adult']
    print(f'{cat} 驱虫: 体内{internal[\"frequency\"]} / 体外{external[\"frequency\"]}')
    checkup = h.checkup[cat]['adult']
    print(f'{cat} 体检: {checkup[\"frequency\"]}, 项目{checkup[\"items\"]}')
"
```

### 第三步：计算饮食计划

根据品种数据和用户信息计算：

1. **RER（静息能耗）** = 70 × 体重^0.75
2. **每日目标热量** = RER × 生命周期系数（成年绝育 ×1.6 犬 / ×1.2 猫）
3. **营养素比例**：从品种库取 protein_ratio / fat_ratio，叠加功能性需求调整
4. **每日喂食量** = 目标热量 ÷ 粮食热量密度（约 3500 kcal/kg 干粮，即 3.5 kcal/g）

功能性需求叠加规则（来自 nutrition.md）：

- weight_loss：总热量 -20%，脂肪 -3%，纤维 +5%
- beauty_coat：+Omega-3 2g/天，+Biotin 5mg/天
- joint_care：+葡萄糖胺 500mg + 硫酸软骨素 400mg/天
- urinary_care：低镁 <0.1%，增加湿粮比例
- hairball：纤维 +3%

### 第三步半：预算方案计算（可选）

信息采集完成后，若用户未主动提供月度预算，询问一句："是否需要按自定义预算规划月度开销？如有预算请告诉我金额。"

用户提供了预算数字后，运行以下命令计算分配方案：

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from pet_care_core import KnowledgeLoader, plan_budget, format_budget_plan
kl = KnowledgeLoader()
breed = kl.load_breed('dog_019')
plan = plan_budget(breed.monthly_cost, 500)
print(format_budget_plan(plan))
"
```

输出包含：标准总额、用户预算、差额、状态（below/match/above）、按比例分配的各分项金额。

**降级/升级建议规则**（根据 status 生成）：

| 状态  | 条件                  | 建议方向                                                                                                                       |
| ----- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| below | 预算低于标准 10% 以上 | 饮食：自制粮替代商业粮、减少零食；美容：居家洗澡剪指甲替代门店；医疗：保留驱虫和疫苗不可削减，体检降为年度；用品：仅补充消耗品 |
| match | 偏差 ±10% 以内        | 直接使用标准分配，无需调整                                                                                                     |
| above | 预算高于标准 10% 以上 | 饮食：升级功能性粮或增加湿粮补充剂；美容：专业美容或增加 SPA；医疗：增加体检频次或牙科护理；用品：升级玩具床品                 |

> 降级方案必须确保基本健康需求（驱虫、疫苗）不被削减，仅调整非必要开支。

### 第四步：生成规划报告

**输出原则**：简洁、具体、可执行。用户只需要知道"该做什么、喂什么、花多少钱、注意什么"，不需要原理推导、数据来源、占比图等。

严格按以下模板输出（4 个模块，不超过 60 行）：

```markdown
# 🐾 [品种名] 本月养宠指南

> [品种名] · [年龄]岁 · [体重]kg · [绝育状态] · [特殊需求]

## 🍖 本月喂什么

| 餐次 | 时间 | 食物 | 用量 |
|------|------|------|------|
| 早餐 | 08:00 | [粮名] + [补充品] | [X]g + [X]粒 |
| 晚餐 | 18:00 | [粮名] + [补充品] | [X]g + [X]g |

- 每日总量：[X]g 干粮 + [X]g 湿粮（约 [X] kcal）
- 零食：≤ [X] kcal/天（训练奖励用）
- 饮水：≥ [X] ml/天
- 禁忌：[品种特殊饮食禁忌，1-2 条]

## ✅ 本月做什么

- [ ] [驱虫/疫苗/体检 — 本月到期项]
- [ ] [洗澡/剪指甲/梳毛 — 美容项]
- [ ] [称重 1 次]
- [ ] [运动打卡：每日 [X] 分钟]
- [ ] [功能性需求相关项，如补充剂]

## 💰 月度开销

**无自定义预算时**，直接展示品种标准开销：

| 项目 | 金额 |
|------|------|
| 🥩 饮食 | [X] 元 |
| ✂️ 美容 | [X] 元 |
| 💊 医疗 | [X] 元 |
| 🎽 用品 | [X] 元 |
| **合计** | **[X] 元** |

**有自定义预算时**，展示标准 vs 用户预算对比 + 差额提示 + 降级/升级建议：

| 项目 | 标准 | 您的预算 |
|------|------|----------|
| 🥩 饮食 | [X] 元 | [X] 元 |
| ✂️ 美容 | [X] 元 | [X] 元 |
| 💊 医疗 | [X] 元 | [X] 元 |
| 🎽 用品 | [X] 元 | [X] 元 |
| **合计** | **[X] 元** | **[X] 元** |

> 您的预算[低于/高于]品种标准 [X] 元。[1-2 条降级/升级建议]

## ⚠️ 注意事项

- [品种高发健康问题，1-2 条，如"金毛易发髋关节问题，避免高强度跳跃"]
- [饮食/运动禁忌，1 条]
```

**输出约束**：

- 总长度控制在 50-60 行以内
- 每个模块只保留用户"需要做"的信息，不写原理和数据来源
- 表格优先，文字从简
- 食物用量必须具体到克数/粒数
- 行动清单必须可勾选、可执行
- 注意事项不超过 3 条，只列最关键的

## 知识库结构

| 文件                      | 内容                                                                     |
| ------------------------- | ------------------------------------------------------------------------ |
| `knowledge/dog_breeds.md` | 合并版犬类品种库（按 breed_id 升序，`<!-- breed: dog_XXX -->` 锚点分隔） |
| `knowledge/cat_breeds.md` | 合并版猫类品种库                                                         |
| `knowledge/nutrition.md`  | 营养标准（热量公式/营养素比例/喂食指南/功能性调整）                      |
| `knowledge/health.md`     | 健康标准（疫苗/驱虫/美容/体检）                                          |

> 品种索引从合并版 MD 的锚点 + front matter 自动构建，无需额外索引文件。

## 脚本工具

| 脚本                                    | 用途                   | 调用方式                                       |
| --------------------------------------- | ---------------------- | ---------------------------------------------- |
| `scripts/pet_care_core.py` verify       | 验证知识库加载正确性   | `python3 scripts/pet_care_core.py verify`       |
| `scripts/pet_care_core.py` merge-breeds | 合并单品种 MD 为合并版 | `python3 scripts/pet_care_core.py merge-breeds` |
| `scripts/pet_care_core.py` tidy-md      | Markdown 排版规范化    | `python3 scripts/pet_care_core.py tidy-md`      |

## 品种字段参考

| 字段                   | 说明                                         |
| ---------------------- | -------------------------------------------- |
| `breed_id`             | 品种唯一 ID，格式 `dog_XXX` 或 `cat_XXX`     |
| `size`                 | small / medium / large / giant               |
| `energy_level`         | 1-5，运动量需求                              |
| `grooming_needs`       | 1-5，≥4 视为长毛                             |
| `trainability`         | 1-5，训练性                                  |
| `daily_calorie_per_kg` | 每日热量基准（kcal/kg）                      |
| `monthly_cost`         | {food, grooming, medical, supplies} 月度开销 |
| `common_health_issues` | 常见健康风险列表                             |
| `special_diet_notes`   | 饮食注意事项                                 |

## 示例文件

- `knowledge/constraints.md` — **行为约束规范（执行 Skill 前必读）**
- `examples/example1-talk.md` — 大型犬，无特殊需求
- `examples/example2-photo.md` — 小型犬，照片输入识别品种+体型，双功能性需求叠加
- `examples/example3-budget.md` — 中型猫，猫双高发需求叠加
- `examples/example4-test.md` — 信息不完整场景：推断确认 + 用户修正
- `examples/example5-multi-turn dialogue.md` — 无毛猫品种特异性场景：1.5倍代谢+皮肤护理流程+未绝育系数
