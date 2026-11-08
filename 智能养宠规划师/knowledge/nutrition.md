---
# ===== 热量计算公式（每日 kcal）=====
# 公式：RER(静息能量消耗) × 生命周期系数
# RER = 70 × (体重kg ^ 0.75)  —— 犬猫通用
# 犬额外系数：幼年 3.0 / 成年绝育 1.6 / 成年未绝育 1.8 / 老年 1.4
# 猫额外系数：幼年 2.5 / 成年绝育 1.2 / 成年未绝育 1.4 / 老年 1.1
# 以下「系数表」直接给出 RER 系数，代码根据 RER 公式算出最终值
calorie_formula:
  dog:
    rer_expr: "70 * (weight_kg ** 0.75)"
    factors:
      puppy: 3.0
      adult_sterilized: 1.6
      adult_intact: 1.8
      senior: 1.4
      pregnant: 3.0
      lactating: 4.0
      weight_loss: 1.0
      weight_gain: 1.8
  cat:
    rer_expr: "70 * (weight_kg ** 0.75)"
    factors:
      puppy: 2.5
      adult_sterilized: 1.2
      adult_intact: 1.4
      senior: 1.1
      pregnant: 3.0
      lactating: 2.0
      weight_loss: 0.8
      weight_gain: 1.4

# ===== 营养素比例标准（占干物质）=====
ratios:
  dog:
    puppy:     { protein: 0.28, fat: 0.17, carb: 0.45, fiber: 0.05 }
    adult:     { protein: 0.25, fat: 0.15, carb: 0.50, fiber: 0.05 }
    senior:    { protein: 0.22, fat: 0.10, carb: 0.55, fiber: 0.08 }
    pregnancy: { protein: 0.28, fat: 0.20, carb: 0.42, fiber: 0.04 }
    lactation: { protein: 0.30, fat: 0.22, carb: 0.40, fiber: 0.04 }
  cat:
    puppy:     { protein: 0.36, fat: 0.22, carb: 0.30, fiber: 0.03 }
    adult:     { protein: 0.32, fat: 0.20, carb: 0.35, fiber: 0.03 }
    senior:    { protein: 0.32, fat: 0.18, carb: 0.38, fiber: 0.04 }
    pregnancy: { protein: 0.38, fat: 0.24, carb: 0.28, fiber: 0.03 }
    lactation: { protein: 0.40, fat: 0.26, carb: 0.26, fiber: 0.03 }

# ===== 每日饮水量（ml）=====
water_per_kg:
  dog: 55          # 犬 55ml/kg
  cat: 50          # 猫 50ml/kg

# ===== 各体型每日喂食量参考（干粮 g）=====
feeding_guide:
  dog:
    small:    { weight_range: [0, 10],  min_g: 100, max_g: 200, meals_per_day: 2 }
    medium:   { weight_range: [10, 25], min_g: 200, max_g: 400, meals_per_day: 2 }
    large:    { weight_range: [25, 45], min_g: 400, max_g: 600, meals_per_day: 2 }
    giant:    { weight_range: [45, 200], min_g: 600, max_g: 1000, meals_per_day: 2 }
  cat:
    small:    { weight_range: [0, 3.5],  min_g: 40,  max_g: 70,  meals_per_day: 2 }
    medium:   { weight_range: [3.5, 5.5], min_g: 60,  max_g: 100, meals_per_day: 2 }
    large:    { weight_range: [5.5, 10],  min_g: 90,  max_g: 160, meals_per_day: 2 }

# ===== 特殊需求营养调整（叠加在基础比例之上）=====
functional_adjustments:
  beauty_coat:                       # 美毛
    add:      { "Omega-3脂肪酸": "2g/day", "Omega-6": "1g/day", "Biotin": "5mg/day" }
    reduce:   {}
    note: "推荐选择三文鱼油、蛋黄、含燕麦成分的食物"
  weight_loss:                       # 减肥
    add:      { "粗纤维": "+5%" }
    reduce:   { "脂肪": "-3%", "总热量": "-20%" }
    note: "推荐高纤减肥粮，少食多餐，增加饮水量"
  weight_gain:                       # 增肥
    add:      { "蛋白质": "+3%", "总热量": "+15%" }
    reduce:   {}
    note: "增加喂食次数，适量添加营养膏"
  tear_stain:                        # 去泪痕
    add:      {}
    reduce:   { "盐分": "低钠配方", "谷物": "尽量排除" }
    note: "选择无谷低敏粮，避免过咸食物"
  gut_health:                        # 改善肠胃
    add:      { "益生菌": "每日补充", "膳食纤维": "+2%" }
    reduce:   { "脂肪": "-2%" }
    note: "定期更换肠道处方粮或添加益生菌粉"
  reproduction:                      # 孕期/生育
    add:      { "钙质": "适量补充", "DHA": "孕期第4周开始补充" }
    reduce:   {}
    note: "孕期第4周起切换为孕期专用粮，哺乳期营养需加倍"
  joint_care:                        # 关节护理
    add:      { "葡萄糖胺": "500mg/day", "硫酸软骨素": "400mg/day" }
    reduce:   { "总热量": "控制体重以减轻关节负担" }
    note: "大型犬老年犬推荐，避免剧烈运动"
  dental_care:                       # 口腔护理
    add:      { "洁牙咀嚼片": "每日1次" }
    reduce:   { "高糖零食": "尽量避免" }
    note: "配合每周刷牙2-3次效果最佳"
  urinary_care:                      # 泌尿护理（猫常见）
    add:      { "水分摄入": "增加湿粮比例" }
    reduce:   { "镁离子": "选择低镁配方（<0.1%）", "磷酸铵镁": "避免" }
    note: "猫泌尿问题高发，建议保证充足饮水"
  hairball:                          # 化毛/去毛球（猫常见）
    add:      { "化毛膏": "每周2-3次", "膳食纤维": "+3%" }
    reduce:   {}
    note: "长毛猫推荐每日梳理配合化毛膏"
---

# 营养标准

## 一、热量公式说明

犬猫每日所需能量（MER，维持能量需求）按两步计算：

1. 先算 RER（静息能量消耗）：

   `RER = 70 × (体重kg ^ 0.75)`

2. 再乘生命周期系数：
   - 幼年：犬 ×3.0 / 猫 ×2.5
   - 成年绝育：犬 ×1.6 / 猫 ×1.2
   - 成年未绝育：犬 ×1.8 / 猫 ×1.4
   - 老年：犬 ×1.4 / 猫 ×1.1

## 二、各体型喂食量参考

### 犬

| 体型 | 体重范围 | 每日喂食量（干粮） | 建议餐次 |
| ---- | -------- | ------------------ | -------- |
| 小型 | <10kg    | 100-200g           | 2-3次    |
| 中型 | 10-25kg  | 200-400g           | 2次      |
| 大型 | 25-45kg  | 400-600g           | 2次      |
| 巨型 | >45kg    | 600-1000g          | 2次      |

### 猫

| 体型 | 体重范围  | 每日喂食量（干粮） | 建议餐次 |
| ---- | --------- | ------------------ | -------- |
| 小型 | <3.5kg    | 40-70g             | 2-3次    |
| 中型 | 3.5-5.5kg | 60-100g            | 2次      |
| 大型 | >5.5kg    | 90-160g            | 2次      |

## 三、饮水建议

- 犬：每 kg 体重约 55ml / 天（例如 20kg 犬需 1100ml）
- 猫：每 kg 体重约 50ml / 天（例如 5kg 猫需 250ml）
- 夏季、运动后、喂食干粮时应增加 20-30% 饮水量

## 四、特殊需求调整表

详见 front_matter 的 `functional_adjustments`。每项需求给出：

- `add`: 需要补充 / 增加比例的营养
- `reduce`: 需要控制 / 减少的成分
- `note`: 人类可读的建议说明
