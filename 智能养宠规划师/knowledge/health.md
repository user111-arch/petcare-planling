---
# ===== 疫苗计划 =====
vaccination:
  dog:
    core:
      - { name: "犬瘟热疫苗（CDV）", schedule: "6-8周首针，每3周加强1次，共3针", boost: "每年1次", cost_est: 80 }
      - { name: "犬细小病毒疫苗（CPV）", schedule: "6-8周首针，每3周加强1次，共3针", boost: "每年1次", cost_est: 80 }
      - { name: "犬副流感疫苗（CPiV）", schedule: "6-8周首针，每3周加强1次，共3针", boost: "每年1次", cost_est: 60 }
      - { name: "犬传染性肝炎疫苗（CAV）", schedule: "6-8周首针，每3周加强1次，共3针", boost: "每年1次", cost_est: 60 }
    non_core:
      - { name: "狂犬疫苗（Rabies）", schedule: "12周首针", boost: "每年1次", cost_est: 80 }
      - { name: "犬钩端螺旋体疫苗", schedule: "9周首针，3周后加强", boost: "每年1次", cost_est: 100 }
      - { name: "犬窝咳疫苗（Bordetella）", schedule: "8周首针", boost: "每6个月1次", cost_est: 120 }
      - { name: "犬莱姆病疫苗", schedule: "12周首针，3周后加强", boost: "每年1次", cost_est: 150 }
  cat:
    core:
      - { name: "猫瘟热疫苗（FPV）", schedule: "8周首针，每3周加强1次，共3针", boost: "每年1次", cost_est: 100 }
      - { name: "猫杯状病毒疫苗（FCV）", schedule: "8周首针，每3周加强1次，共3针", boost: "每年1次", cost_est: 100 }
      - { name: "猫疱疹病毒疫苗（FHV-1）", schedule: "8周首针，每3周加强1次，共3针", boost: "每年1次", cost_est: 100 }
    non_core:
      - { name: "狂犬疫苗（Rabies）", schedule: "12周首针", boost: "每年1次", cost_est: 80 }
      - { name: "猫白血病病毒疫苗（FeLV）", schedule: "8周首针，3周后加强", boost: "每年1次", cost_est: 150 }
      - { name: "猫衣原体疫苗", schedule: "9周首针，3周后加强", boost: "每年1次", cost_est: 120 }
      - { name: "猫传染性腹膜炎疫苗（FIP）", schedule: "16周首针", boost: "每年1次", cost_est: 200 }

# ===== 驱虫计划 =====
deworming:
  dog:
    internal:
      puppy:   { frequency: "每月1次（2周龄起）", cost_est: 50 }
      adult:   { frequency: "每3个月1次", cost_est: 50 }
    external:
      puppy:   { frequency: "每月1次（8周龄起）", cost_est: 120 }
      adult:   { frequency: "每月1次，4-10月高频期务必按时", cost_est: 120 }
      note: "夏季蚊虫多可增加频率，建议体内体外同驱"
  cat:
    internal:
      puppy:   { frequency: "每月1次（6周龄起）", cost_est: 50 }
      adult:   { frequency: "每3个月1次", cost_est: 50 }
    external:
      puppy:   { frequency: "每月1次（8周龄起）", cost_est: 100 }
      adult:   { frequency: "每月1次", cost_est: 100 }
      note: "室内猫也需体外驱虫，避免带入虫卵"

# ===== 美容护理周期 =====
grooming:
  # 短毛犬/猫（短毛品种按此值，长毛品种代码中按 breed.grooming_needs 等级放大）
  short_hair:
    bathing:      { frequency: "每4-6周", cost_est: 80, duration_min: 60 }
    brushing:     { frequency: "每周1-2次", cost_est: 0,  duration_min: 10 }
    nail_trim:    { frequency: "每3-4周", cost_est: 30, duration_min: 15 }
    ear_cleaning: { frequency: "每2周1次", cost_est: 30, duration_min: 10 }
    dental_care:  { frequency: "每周2-3次刷牙", cost_est: 0, duration_min: 10 }
    anal_gland:   { frequency: "每1-2个月", cost_est: 30, duration_min: 10 }
  # 长毛犬/猫
  long_hair:
    bathing:      { frequency: "每3-4周", cost_est: 150, duration_min: 90 }
    brushing:     { frequency: "每日1次", cost_est: 0,   duration_min: 15 }
    nail_trim:    { frequency: "每3-4周", cost_est: 30,  duration_min: 15 }
    ear_cleaning: { frequency: "每周1次", cost_est: 30,  duration_min: 10 }
    dental_care:  { frequency: "每周2-3次刷牙", cost_est: 0, duration_min: 10 }
    anal_gland:   { frequency: "每1-2个月", cost_est: 30,  duration_min: 10 }
    fur_trim:     { frequency: "每6-8周修剪", cost_est: 180, duration_min: 120 }

# ===== 体检频率 =====
checkup:
  dog:
    puppy:   { frequency: "每3-4周（配合疫苗期）", cost_est: 200, items: ["基础检查", "疫苗评估", "驱虫评估"] }
    adult:   { frequency: "每年1次", cost_est: 350, items: ["血常规", "生化10项", "X光", "听诊", "触诊"] }
    senior:  { frequency: "每半年1次", cost_est: 550, items: ["血常规", "生化18项", "X光", "B超", "心电图", "眼压"] }
  cat:
    puppy:   { frequency: "每3-4周（配合疫苗期）", cost_est: 200, items: ["基础检查", "疫苗评估", "驱虫评估"] }
    adult:   { frequency: "每年1次", cost_est: 350, items: ["血常规", "生化10项", "X光", "听诊", "触诊"] }
    senior:  { frequency: "每半年1次", cost_est: 550, items: ["血常规", "生化18项", "X光", "B超", "血压", "眼科"] }
---

# 健康护理标准

## 一、疫苗

**犬核心四联**：犬瘟热 + 犬细小 + 犬副流感 + 犬传肝。幼犬需连续3针（间隔3周），首年完成后每年加强1次。

**猫核心三联**：猫瘟 + 杯状 + 疱疹。同样需3针基础免疫。

**狂犬疫苗**：国内强制，12周龄首针，每年加强。

## 二、驱虫

- 体内驱虫：幼年期每月1次，成年后每季度1次
- 体外驱虫：建议每月1次（尤其夏季）
- 体内外同驱产品可选（如大宠爱、爱沃克），代码按成本取中位值

## 三、美容

品种 `grooming_needs` 等级（1-5）作为系数：

- 1-2（短毛低需求）→ 采用 short_hair 周期
- 3-5（长毛高需求）→ 采用 long_hair 周期，加 fur_trim 项

## 四、体检

老年期（7岁+）、大型犬（5岁+）按 senior 频率执行，项目增加B超、心电图等。
