# A股选股器

每日盘前/竞价/收盘自动运行短线战法选股（支持手动触发）。

- 后端：FastAPI + SQLAlchemy + akshare
- 前端：原生 HTML/CSS/JS
- 数据源：东方财富（akshare）

## 部署到 Render.com（推荐）

Render 支持 Python Web 服务长期运行，有免费额度。

### 一键部署

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### 手动部署步骤

1. **上传代码到 GitHub**

```bash
cd /path/to/stock-picker
git init
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_USER/stock-picker.git
git push -u origin main
```

2. **在 Render 创建 Web Service**

   - 登录 https://dashboard.render.com
   - 点击 **New +** → **Web Service**
   - 连接你的 GitHub 仓库
   - 选择 **Python** 运行时
   - 项目已自带 `render.yaml`，Render 会自动识别
   - 或手动配置：
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
     - **Plan**: Starter（免费额度足够）
   
3. **添加持久化磁盘**

   - 在 Render 后台，进入你的 Web Service
   - 点击 **Disks** → **Add Disk**
   - 挂载路径: `/data`
   - 大小: 1GB（免费额度内）
   - 环境变量 `DATABASE_URL` 会自动设置为 `sqlite+aiosqlite:////data/stock_picker.db`

4. **初始化数据**

   部署完成后首次需要运行选股：
   - 访问 `https://你的应用名.onrender.com`
   - 点击 **⚡ 手动选股** 按钮，等待完成
   - 或者在你本机运行
     ```bash
     python3 scripts/backfill_sectors.py
     ```
     然后把生成的 `data/stock_picker.db` 上传到 Render 的磁盘

5. **定时选股**

   部署后每天 7:00 / 9:25 / 15:30 会自动运行选股策略。

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接 | `sqlite+aiosqlite:///data/stock_picker.db` |
| `PORT` | 服务端口（Render 自动设置） | `8000` |

## 本地运行

```bash
cd /path/to/stock-picker
pip install -r requirements.txt
python3 main.py
```

打开 http://127.0.0.1:8000

## 回填行业/概念标签

```bash
python3 scripts/backfill_sectors.py
```
