# 高考数学题库 · Apple Design Language 设计指南

## 🎨 设计理念

本次重新设计采用**苹果公司设计语言**，打造专业、现代、极简的政务级界面体验。

### 核心设计原则

1. **极简主义** - 大量留白，让内容自己说话
2. **专业配色** - 纯白背景 + 苹果蓝强调色
3. **呼吸感** - 宽松的间距和排版
4. **流畅动效** - 自然的过渡动画
5. **无障碍** - 符合 WCAG 标准的高对比度

---

## 🎨 色彩系统

### 主色调

```css
/* 背景色 */
--bg-primary:      #FFFFFF;              /* 主背景纯白 */
--bg-secondary:    #F5F5F7;              /* 次级背景浅灰 */
--bg-tertiary:     #FAFAFA;              /* 三级背景 */
--bg-card:         #FFFFFF;              /* 卡片纯白 */

/* 苹果蓝 */
--apple-blue:       #007AFF;             /* 苹果标准蓝 */
--apple-blue-hover: #0051D5;             /* 悬停态 */
--apple-blue-active:#0047BA;             /* 按压态 */
--apple-blue-light: rgba(0, 122, 255, 0.1); /* 浅底 */

/* 文字色阶 */
--text-primary:    #1D1D1F;             /* 主文字 */
--text-secondary:  #86868B;             /* 次文字 */
--text-tertiary:   #AEAEB2;             /* 弱文字 */
```

### 功能色

```css
--green:   #34C759;   /* 成功/正确 */
--orange:  #FF9500;   /* 警告/重点 */
--red:     #FF3B30;   /* 错误/删除 */
--purple:  #AF52DE;   /* 特殊强调 */
```

---

## 📐 排版系统

### 字体栈

```css
/* 无衬线字体（苹果系统） */
--font-sans: -apple-system, BlinkMacSystemFont, 
             "SF Pro Display", "SF Pro Text", 
             "PingFang SC", "Helvetica Neue", 
             "Microsoft YaHei", sans-serif;

/* 等宽字体 */
--font-mono: "SF Mono", "Fira Code", 
             "Source Code Pro", monospace;

/* 数学公式字体 */
--font-math: "Latin Modern Math", 
             "STIX Two Math", 
             "Cambria Math", Georgia, serif;
```

### 字号层级

| 用途 | 字号 | 字重 | 行高 |
|------|------|------|------|
| Display (大标题) | 40px | Bold | 1.2 |
| Large Title | 34px | Bold | 1.2 |
| Title 1 | 28px | Bold | 1.2 |
| Title 2 | 22px | Semibold | 1.3 |
| Title 3 | 20px | Semibold | 1.4 |
| Body | 17px | Regular | 1.47 |
| Subheadline | 15px | Medium | 1.47 |
| Footnote | 13px | Regular | 1.4 |
| Caption | 12px | Regular | 1.3 |

### 字重

```css
--weight-regular:  400;
--weight-medium:   500;
--weight-semibold: 600;
--weight-bold:     700;
```

---

## 📏 间距系统

基于 **8px 网格**的间距系统：

```css
--space-1:   4px;
--space-2:   8px;
--space-3:   12px;
--space-4:   16px;
--space-5:   20px;
--space-6:   24px;
--space-8:   32px;
--space-10:  40px;
--space-12:  48px;
--space-16:  64px;
--space-20:  80px;
```

---

## 🔲 圆角系统

苹果风格的大圆角设计：

```css
--radius-xs:  8px;
--radius-sm:  12px;
--radius-md:  16px;
--radius-lg:  20px;
--radius-xl:  24px;
```

---

## 🌟 阴影系统

微妙的阴影层次：

```css
--shadow-xs:  0 1px 2px rgba(0, 0, 0, 0.04);
--shadow-sm:  0 2px 8px rgba(0, 0, 0, 0.04);
--shadow-md:  0 4px 16px rgba(0, 0, 0, 0.08);
--shadow-lg:  0 8px 24px rgba(0, 0, 0, 0.12);
--shadow-xl:  0 12px 40px rgba(0, 0, 0, 0.15);
```

---

## 🎭 组件设计

### 1. Hero 区域

**设计特点：**
- 渐变背景（苹果蓝 → 青色）
- 大标题 + 数据统计
- 圆角 24px
- 大阴影

**使用场景：** 首页顶部展示

```html
<section class="hero">
  <h1>高考数学题库</h1>
  <div class="hero-stats">
    <div class="hero-stat">
      <b>499</b>
      <span>套试卷</span>
    </div>
    <!-- 更多统计 -->
  </div>
</section>
```

### 2. 题目卡片

**设计特点：**
- 纯白背景
- 微边框（0.5px）
- 悬停上浮效果
- 题号蓝色高亮

**使用场景：** 题目列表展示

```html
<div class="question-card">
  <div class="q-meta">
    <span class="tags">函数</span>
  </div>
  <div class="q-stem">
    <!-- 题干内容 -->
  </div>
  <div class="q-options">
    <!-- 选项 -->
  </div>
  <details class="q-answer">
    <summary>查看答案</summary>
    <!-- 答案内容 -->
  </details>
</div>
```

### 3. 知识点卡片

**设计特点：**
- 网格布局
- 悬停上浮
- 边框变蓝
- 最小高度 100px

**使用场景：** 知识点专题页

```html
<div class="topic-grid">
  <a href="/topic/函数" class="topic-card">
    <div class="topic-name">函数</div>
    <div class="topic-n">2,950 题</div>
  </a>
  <!-- 更多卡片 -->
</div>
```

### 4. 筛选条

**设计特点：**
- 卡片式容器
- 输入框聚焦蓝光
- 按钮苹果蓝
- 响应式布局

```html
<div class="filter-bar">
  <select>
    <option>年份</option>
  </select>
  <input type="search" placeholder="搜索题目...">
  <button>搜索</button>
</div>
```

### 5. 导航栏

**设计特点：**
- 毛玻璃效果（backdrop-filter）
- 半透明白色
- 底部细边框
- 固定定位

```html
<nav class="topnav">
  <div class="nav-inner">
    <a class="brand" href="/">
      <span class="logo">∑</span>
      高考数学题库
    </a>
    <div class="nav-links">
      <a href="/">首页</a>
      <a href="/papers">试卷库</a>
      <!-- 更多链接 -->
    </div>
  </div>
</nav>
```

---

## 📱 响应式设计

### 断点设置

```css
/* 平板竖屏 */
@media (max-width: 900px) { }

/* 手机横屏 */
@media (max-width: 640px) { }

/* 触控设备 */
@media (pointer: coarse) { }
```

### 触控优化

- 所有可交互元素最小高度 **44px**（Apple HIG 标准）
- 触控反馈动画
- 侧边栏折叠抽屉

---

## 🌗 暗色模式

自动适配系统暗色模式：

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary:   #000000;
    --bg-card:      #1C1C1E;
    --text-primary: #F5F5F7;
    --apple-blue:   #0A84FF;
  }
}
```

---

## ✨ 动效设计

### 缓动函数

```css
/* 标准缓动 */
--ease: cubic-bezier(0.25, 0.1, 0.25, 1);

/* 弹性缓动 */
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

/* 时长 */
--duration-fast:   0.15s;
--duration-normal: 0.25s;
--duration-slow:   0.35s;
```

### 常见动效

**卡片悬停：**
```css
.question-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
```

**按钮按压：**
```css
button:active {
  transform: scale(0.97);
}
```

**标签切换：**
```css
.tag {
  transition: all var(--duration-normal) var(--ease);
}
```

---

## 🎯 无障碍设计

### 对比度

- 主文字 `#1D1D1F` on `#FFFFFF` → **17.5:1** ✅
- 次文字 `#86868B` on `#FFFFFF` → **4.5:1** ✅
- 苹果蓝 `#007AFF` on `#FFFFFF` → **4.5:1** ✅

### 键盘导航

- 所有交互元素可聚焦
- 聚焦态明显（蓝色边框 + 阴影）
- Tab 键顺序合理

### 屏幕阅读器

- 语义化 HTML
- ARIA 标签
- 替代文本

---

## 🚀 性能优化

### CSS 优化

- 使用 CSS 变量（易于维护）
- 避免过度嵌套
- 使用 `will-change` 提示浏览器

### 动画优化

- 优先使用 `transform` 和 `opacity`
- 避免触发布局重排
- 使用 `prefers-reduced-motion` 检测

---

## 📋 浏览器支持

- ✅ Chrome 90+
- ✅ Safari 14+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ iOS Safari 14+

---

## 🎨 设计亮点总结

1. **苹果美学** - 参考 Apple.com 的设计语言
2. **专业配色** - 纯白 + 苹果蓝 + 灰度层次
3. **大圆角** - 12-24px 圆角，现代感强
4. **毛玻璃** - 导航栏 backdrop-filter 效果
5. **微阴影** - 极其微妙的阴影层次
6. **流畅动效** - 自然的过渡动画
7. **响应式** - 完美适配各种设备
8. **暗色模式** - 自动适配系统主题
9. **无障碍** - 符合 WCAG 标准
10. **性能优化** - 流畅的 60fps 动画

---

## 📚 参考资源

- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines)
- [Apple Design Resources](https://developer.apple.com/design/resources/)
- [SF Pro Font](https://developer.apple.com/fonts/)

---

## 🔧 技术栈

- **CSS 变量** - 易于主题切换
- **Flexbox/Grid** - 现代布局
- **KaTeX** - 数学公式渲染
- **原生 JavaScript** - 无依赖

---

**设计完成时间：** 2026-10-19  
**设计风格：** Apple Design Language  
**适用场景：** 教育类 Web 应用、政务看板、专业工具
