# 高考数学题库部署指南 (Railway)

## 部署步骤

### 1. 准备 GitHub 仓库

```bash
# 如果还未推送到 GitHub
cd /Users/mac/Documents/GitHub/GaokaoMathBank
git add .
git commit -m "Add Railway deployment config"
git push origin main
```

### 2. 部署到 Railway

**方式 A: 通过网页 (推荐)**

1. 访问 https://railway.app 并使用 GitHub 登录
2. 点击 "New Project" → "Deploy from GitHub repo"
3. 选择你的 GaokaoMathBank 仓库
4. Railway 会自动检测 Dockerfile 并开始构建
5. 等待构建完成(约 5-10 分钟)

**方式 B: 通过 CLI**

```bash
# 安装 Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 在项目目录初始化
cd /Users/mac/Documents/GitHub/GaokaoMathBank
railway init

# 部署
railway up
```

### 3. 配置持久化存储

Railway 需要手动挂载数据卷来保存 SQLite 数据库:

1. 在 Railway 项目面板，点击你的服务
2. 进入 "Settings" → "Volumes"
3. 点击 "Add Volume"
4. 挂载路径填写: `/app/data`
5. 保存后服务会自动重启

### 4. 上传数据库文件

部署完成后，需要上传本地的 138MB 数据库:

**方式 A: 通过 Railway CLI**

```bash
# 上传数据库到数据卷
railway volume upload data/mathbank.db --path /app/data/mathbank.db
```

**方式 B: 通过 SCP/SFTP**

1. 在 Railway 面板获取服务的主机名
2. 使用 SCP 上传文件(需要 Railway Pro 计划)

**方式 C: 重新采集(推荐用于首次部署)**

```bash
# 通过 Railway CLI 执行命令
railway run python tools/run_collect.py --source github-gaokao-latex
railway run python tools/run_collect.py --source github-gaokaomath
```

### 5. 获取访问地址

部署成功后:

1. 在 Railway 面板点击你的服务
2. 进入 "Settings" → "Networking"
3. 点击 "Generate Domain" 生成免费子域名
4. 访问生成的 URL(如: https://gaokaomathbank.up.railway.app)

### 6. 环境变量(可选)

如果需要调整配置:

1. Railway 面板 → Variables
2. 可添加的环境变量:
   - `PORT`: 服务端口(默认 8000)
   - 其他自定义配置

## 注意事项

### 数据持久化

- SQLite 数据库存储在挂载的卷中，重启不会丢失
- 采集的新数据会自动保存到 `/app/data/`
- 建议定期备份数据卷

### 资源限制

Railway 免费版限制:
- 每月 $5 额度(约 500 小时运行时间)
- 512MB 内存
- 1GB 存储空间

对于个人使用的小题库应该足够，但如果数据量很大(>500MB)可能需要升级。

### 性能优化建议

1. **静态资源缓存**: 可以在 Railway 面板配置 CDN(需 Pro 计划)
2. **数据库索引**: 确保常用查询字段已建索引
3. **KaTeX 缓存**: 首次加载较慢，后续会快很多

### 故障排查

如果部署失败:

```bash
# 查看构建日志
railway logs

# 查看运行时日志
railway logs --deploy

# 本地测试 Docker 镜像
docker build -t gaokaomathbank .
docker run -p 8000:8000 -v ./data:/app/data gaokaomathbank
```

## 替代方案

如果 Railway 不合适，还可以考虑:

### Render (免费额度更多)
- 优点: 免费 750 小时/月
- 缺点: 需要手动配置持久化磁盘(付费功能)

### PythonAnywhere
- 优点: 专门的 Python 托管平台，配置简单
- 缺点: 免费版功能受限，无法使用自定义启动命令

### 自建 VPS (DigitalOcean/AWS)
- 优点: 完全控制，无资源限制
- 缺点: 需要自己维护服务器

## 成本估算

### Railway 方案(推荐)

- **免费版**: $5/月额度
  - 适合个人使用，数据量 < 500MB
  - 包含: 500 小时运行 + 1GB 存储
  
- **Pro 版**: $20/月起
  - 适合团队使用，数据量 > 1GB
  - 包含: 更多运行时间和存储空间

### 其他平台对比

| 平台 | 免费额度 | 存储限制 | 适合场景 |
|------|---------|---------|---------|
| Railway | $5/月 | 1GB | 个人项目 |
| Render | 750h/月 | 需付费 | 轻量应用 |
| PythonAnywhere | 有限 | 512MB | 学习测试 |
| 自建 VPS | 无 | 自定义 | 生产环境 |

## 后续维护

### 更新部署

```bash
# 本地修改代码后
git add .
git commit -m "Update description"
git push origin main
# Railway 会自动重新部署
```

### 数据备份

```bash
# 下载数据库备份
railway volume download /app/data/mathbank.db ./backup/mathbank.db

# 或定期采集最新数据
railway run python tools/run_collect.py --source github-gaokao-latex
```

### 监控

Railway 提供基础监控:
- CPU/内存使用率
- 请求日志
- 错误追踪

可在项目面板的 "Metrics" 页面查看。

## 常见问题

**Q: 为什么部署后看不到数据？**  
A: 数据库文件未上传。使用 `railway volume upload` 或重新采集。

**Q: 页面加载很慢？**  
A: KaTeX 首次渲染较慢，后续会缓存。考虑启用 CDN。

**Q: 数据库会被重置吗？**  
A: 不会，只要挂载了持久化卷。但建议定期备份。

**Q: 如何添加自定义域名？**  
A: 需要 Railway Pro 计划，在 Settings → Domains 配置。

---

**部署完成后，分享你的 Railway URL 给我，我可以帮你测试访问！**
