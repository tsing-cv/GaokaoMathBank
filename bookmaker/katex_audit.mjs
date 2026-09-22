// 诊断工具:strict 模式扫 latex,按未定义命令名聚合失败
import katex from 'katex';
import { readFileSync } from 'fs';
const input = JSON.parse(readFileSync(0, 'utf8'));
const undefCmds = {}, otherFails = {};
let ok = 0;
for (const item of input.items) {
  try {
    katex.renderToString(item.tex, { throwOnError: true, strict: false, trust: false });
    ok++;
  } catch (e) {
    const m = String(e.message).match(/Undefined control sequence: \\\x5Cb+/);
    if (m) {
      // 提取命令名:message 里 "\x5C̲b̲s̲{...}" 带组合下划线字符
      const raw = String(e.message).replace(/Undefined control sequence: /, '').slice(0, 40);
      const name = raw.replace(/̲/g, '').split(/[{}\s]/)[0];
      undefCmds[name] = (undefCmds[name] || 0) + 1;
    } else {
      const k = String(e.message).replace(/at position \d+:.*/s, '').slice(0, 60);
      otherFails[k] = (otherFails[k] || 0) + 1;
    }
  }
}
const s = (o) => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, 30);
console.log(JSON.stringify({ ok, undef: s(undefCmds), other: s(otherFails) }, null, 1));
