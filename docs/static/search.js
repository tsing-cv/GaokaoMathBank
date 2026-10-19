/**
 * 高考数学题库 - 客户端搜索功能
 * 用于 GitHub Pages 静态网站的全文搜索
 */

class QuestionSearch {
  constructor() {
    this.questions = [];
    this.searchIndex = [];
    this.init();
  }

  /**
   * 初始化搜索
   */
  async init() {
    try {
      // 加载题目数据
      const response = await fetch('/GaokaoMathBank/data/questions.json');
      this.questions = await response.json();

      // 构建搜索索引
      this.buildSearchIndex();

      console.log(`✅ 搜索已初始化: ${this.questions.length} 道题目`);
    } catch (error) {
      console.error('❌ 搜索初始化失败:', error);
    }
  }

  /**
   * 构建搜索索引
   */
  buildSearchIndex() {
    this.searchIndex = this.questions.map(q => ({
      id: q.id,
      // 提取题干文本
      stemText: this.extractText(q.stem),
      // 提取答案文本
      answerText: this.extractText(q.answer),
      // 知识点
      tags: q.knowledge_tags || [],
      // 元数据
      year: q.year,
      province: q.province,
      qtype: q.qtype,
      paper_name: q.paper_name
    }));
  }

  /**
   * 从分段 JSON 中提取纯文本
   */
  extractText(segments) {
    if (!segments || !Array.isArray(segments)) return '';
    return segments
      .filter(seg => seg.t === 'text' || seg.t === 'latex')
      .map(seg => seg.c || '')
      .join(' ');
  }

  /**
   * 搜索题目
   * @param {string} query - 搜索关键词
   * @param {Object} filters - 筛选条件
   * @returns {Array} 搜索结果
   */
  search(query, filters = {}) {
    if (!query && Object.keys(filters).length === 0) {
      return this.questions;
    }

    const queryLower = query.toLowerCase();
    const queryTerms = queryLower.split(/\s+/).filter(t => t.length >= 2);

    let results = this.searchIndex.filter(item => {
      // 关键词匹配
      let matches = true;
      if (queryTerms.length > 0) {
        matches = queryTerms.some(term =>
          item.stemText.toLowerCase().includes(term) ||
          item.answerText.toLowerCase().includes(term) ||
          item.tags.some(tag => tag.toLowerCase().includes(term)) ||
          item.paper_name.toLowerCase().includes(term)
        );
      }

      // 筛选条件
      if (filters.year && item.year !== parseInt(filters.year)) {
        matches = false;
      }
      if (filters.province && item.province !== filters.province) {
        matches = false;
      }
      if (filters.qtype && item.qtype !== filters.qtype) {
        matches = false;
      }
      if (filters.tag && !item.tags.includes(filters.tag)) {
        matches = false;
      }

      return matches;
    });

    // 按相关性排序
    if (queryTerms.length > 0) {
      results.sort((a, b) => {
        const aScore = this.calculateScore(a, queryTerms);
        const bScore = this.calculateScore(b, queryTerms);
        return bScore - aScore;
      });
    }

    // 返回完整题目数据
    return results.map(r => this.questions.find(q => q.id === r.id));
  }

  /**
   * 计算相关性分数
   */
  calculateScore(item, queryTerms) {
    let score = 0;

    queryTerms.forEach(term => {
      // 题干匹配权重最高
      if (item.stemText.toLowerCase().includes(term)) {
        score += 10;
      }
      // 知识点匹配
      if (item.tags.some(tag => tag.toLowerCase().includes(term))) {
        score += 5;
      }
      // 答案匹配
      if (item.answerText.toLowerCase().includes(term)) {
        score += 3;
      }
      // 试卷名匹配
      if (item.paper_name.toLowerCase().includes(term)) {
        score += 2;
      }
    });

    return score;
  }

  /**
   * 高亮关键词
   */
  highlightText(text, query) {
    if (!query || query.trim() === '') return text;

    const terms = query.split(/\s+/).filter(t => t.length >= 2);
    let result = text;

    terms.forEach(term => {
      const regex = new RegExp(`(${term})`, 'gi');
      result = result.replace(regex, '<mark>$1</mark>');
    });

    return result;
  }
}

// 导出到全局
window.QuestionSearch = QuestionSearch;
