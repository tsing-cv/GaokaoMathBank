# 高考数学题库 · 设计Token体系 v3.0

> iPad竖屏优先 (1024×1366 @2x) · 学术严谨感 + 现代呼吸感

## 1. 色彩系统 (Color & Mood)

### 背景色系
| Token | 值 | 用途 |
|-------|-----|------|
| `--bg-page` | `#F9F8F4` | 护眼纸张色(主背景) |
| `--bg-card` | `#FFFFFF` | 卡片白 |
| `--bg-inset` | `#F3F1EC` | 凹陷/公式块底色 |
| `--bg-sidebar` | `#F5F3EE` | 侧边栏底色 |
| `--bg-hover` | `rgba(0,0,0,0.025)` | 通用hover底色 |

### 主色(学术深蓝灰)
| Token | 值 | 用途 |
|-------|-----|------|
| `--primary` | `#3D5A80` | 主色 |
| `--primary-bright` | `#4A7FB5` | 亮主色(链接) |
| `--primary-deep` | `#2C3E50` | 公式/标题墨色 |
| `--primary-tint` | `#E8EDF3` | 主色浅底 |
| `--primary-line` | `#C8D4E2` | 主色浅边 |

### 功能色(莫兰迪)
| Token | 值 | 用途 |
|-------|-----|------|
| `--sage` | `#6B9E78` | 正确/掌握(鼠尾草绿) |
| `--sage-tint` | `#EDF5EF` | 正确浅底 |
| `--terracotta` | `#C47D7D` | 错误/待复习(陶土红) |
| `--terra-tint` | `#F8EDED` | 错误浅底 |
| `--amber` | `#D4A853` | 重点/收藏/PDF链接(琥珀黄) |
| `--amber-tint` | `#FBF5E6` | 重点浅底 |

### 文字色阶
| Token | 值 | 用途 | 对比度(vs #F9F8F4) |
|-------|-----|------|-------------------|
| `--ink` | `#2C3E50` | 主文字 | ≥7:1 ✓ |
| `--ink-2` | `#5A6B7D` | 次文字 | ≥4.5:1 ✓ |
| `--ink-3` | `#8B95A3` | 弱文字/占位 | ≥3:1 ✓ |
| `--ink-inverse` | `#FFFFFF` | 深色底反白 | - |

## 2. 字体排印 (Typography)

### 字体栈
```css
--font-body:  -apple-system, "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
--font-math:  "Latin Modern Math", "STIX Two Math", "Cambria Math", Georgia, serif;
--font-mono:  "SF Mono", "Fira Code", "Source Code Pro", monospace;
```

### 字号体系
| Token | 值 | 用途 |
|-------|-----|------|
| `--fs-body` | `17px` | 正文(iPad黄金尺寸) |
| `--fs-small` | `14px` | 次要文字 |
| `--fs-xs` | `12px` | 标签/微注 |
| `--fs-h1` | `26px` | 一级标题 |
| `--fs-h2` | `20px` | 二级标题 |
| `--fs-math` | `18.7px` | 公式(正文×1.1补偿) |

### 行高
| Token | 值 | 用途 |
|-------|-----|------|
| `--lh-body` | `1.75` | 正文行高 |
| `--lh-math` | `2.1` | 公式行高 |

## 3. 光影与质感 (Light & Texture)

### 阴影系统(左上45°自然光)
| Token | 值 | 用途 |
|-------|-----|------|
| `--shadow-sm` | `0 1px 3px rgba(44,62,80,0.04)` | 导航/微凸起 |
| `--shadow` | `0 4px 24px rgba(0,0,0,0.04)` | 卡片默认 |
| `--shadow-lg` | `0 8px 32px rgba(0,0,0,0.07)` | 卡片hover |
| `--shadow-press` | `0 2px 8px rgba(0,0,0,0.06)` | 按压态 |

### 圆角
| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-sm` | `6px` | 标签/按钮/小控件 |
| `--radius` | `12px` | 卡片 |
| `--radius-lg` | `16px` | Hero/大容器 |

## 4. 间距节奏 (Spacing)

| Token | 值 |
|-------|-----|
| `--space-xs` | `4px` |
| `--space-sm` | `8px` |
| `--space-md` | `16px` |
| `--space-lg` | `24px` |
| `--space-xl` | `36px` |
| `--space-2xl` | `48px` |

## 5. 布局 (Layout)

| Token | 值 | 用途 |
|-------|-----|------|
| `--sidebar-w` | `280px` | 侧边栏固定宽度 |
| `--nav-h` | `56px` | 导航栏高度 |
| `--content-max` | `820px` | 内容区最大宽度 |
| `--safe-top` | `env(safe-area-inset-top)` | iOS顶部安全区 |
| `--safe-bottom` | `env(safe-area-inset-bottom)` | iOS底部安全区 |

## 6. 动效 (Motion)

| Token | 值 | 用途 |
|-------|-----|------|
| `--ease` | `cubic-bezier(0.25, 0.1, 0.25, 1)` | 标准缓动 |
| `--dur` | `0.2s` | 标准时长 |

## 7. 触控热区 (Touch Targets)

- 所有可点击元素最小尺寸: **44×44pt** (iOS HIG标准)
- 导航链接: **48×48pt**
- 元素间距: **≥12pt**
- 通过 `@media (pointer: coarse)` 自动增强

## 8. 响应式断点

| 断点 | 布局 | 行为 |
|------|------|------|
| `>900px` | 双栏(侧边栏+内容) | 侧边栏固定显示 |
| `≤900px` | 单栏+底部Tab | 侧边栏折叠为抽屉 |
| `≤640px` | 单栏紧凑 | 字号缩小,网格重排 |

## 9. 公式块专项

- 背景: `--bg-inset` + 0.5%噪点纹理
- 内边距: `16px 24px`
- 圆角: `--radius-sm`
- 复制按钮: hover/focus时淡入,右上角定位
- 公式字号: `--fs-math` (18.7px = 17px × 1.1)
- 公式颜色: `--primary-deep` (#2C3E50, 对比度≥7:1)
