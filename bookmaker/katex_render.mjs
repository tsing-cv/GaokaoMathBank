// KaTeX 批量渲染:stdin JSON → stdout JSON
// 输入: {"items": [{"tex": "...", "display": true|false}, ...]}
// 输出: {"0": "<span...html...>" | null, ...}  (null=渲染失败)
import katex from 'katex';
import { readFileSync } from 'fs';

let input;
try {
  input = JSON.parse(readFileSync(0, 'utf8'));
} catch (e) {
  process.stderr.write(`bad input JSON: ${e}`);
  process.exit(1);
}
const out = {};
for (const [i, item] of input.items.entries()) {
  try {
    out[i] = katex.renderToString(item.tex, {
      displayMode: !!item.display,
      // 只输出视觉层:weasyprint 不认 katex.css 的 clip 隐藏,MathML
      // 无障碍层会与 HTML 层文字叠印(前端网页由 KaTeX CDN 自带完整输出)
      output: 'html',
      // 未知命令渲染为红色文字而非抛错(语法级错误仍会 null 走降级)
      throwOnError: false,
      strict: false,
      trust: false,
    });
  } catch (e) {
    out[i] = null;
  }
}
process.stdout.write(JSON.stringify(out));
