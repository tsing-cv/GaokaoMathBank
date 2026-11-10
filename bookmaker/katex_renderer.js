/**
 * KaTeX 服务端公式渲染器
 * 批量渲染 LaTeX 公式为 HTML
 */

const katex = require('katex');

/**
 * 渲染单个 LaTeX 公式
 */
function renderLatex(latex, displayMode = false) {
  try {
    return katex.renderToString(latex, {
      displayMode: displayMode,
      output: 'html',
      throwOnError: false,
      errorColor: '#cc0000',
      trust: true,
      strict: false
    });
  } catch (error) {
    return `<span style="color: #cc0000;">[公式渲染失败]</span>`;
  }
}

// 命令行模式：单个公式
const input = process.argv[2];
if (input) {
  try {
    const data = JSON.parse(input);
    if (data.type === 'latex') {
      console.log(renderLatex(data.content, data.display || false));
    }
  } catch (error) {
    console.error('输入解析失败:', error.message);
    process.exit(1);
  }
}

module.exports = { renderLatex };
