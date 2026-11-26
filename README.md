# OpenTutor — 开源 AI 导学助手

> 受 [AskSia / Sia](https://www.asksia.ai/) 启发、从其产品形态逆向学习后，从零实现的一个**完全开源、可在自己电脑上跑**的 AI 导师。
> 核心理念与 Sia 一致：**不直接给答案，用苏格拉底式提问一步步引导学生自己想出来。**

## 为什么做这个

Sia 是面向留学生的付费 AI 辅导软件：解题对话、白板分步板书、间隔复习记忆、学习产物、备考题库、游戏化进度——这些都很有价值，但它在云端计费、闭源。OpenTutor 把这些**核心学习体验**用开源方式重做一遍，模型由你自己选：接自己的 API，或跑本地模型，数据留在自己电脑。

## 功能

- 💬 **解题对话**：苏格拉底式引导，不直接给答案；带会话历史、多学科切换
- 📋 **白板步骤**：把解答拆成可逐步揭示的板书（对应 Sia 的 board reveal）
- 🧠 **间隔复习**：SM-2 简化版，1→3→7→16→35→60 天节奏，答错自动回炉（对应 tutor_memory）
- 📚 **学习产物**：对话一键整理成笔记 / 解题过程 / 抽认卡，带版本号（对应 artifact_versions）
- 🎯 **备考题库**：SAT / ACT / AP / 通用学科示例，数据可扩展（对应 test-prep）
- ⚙️ **三种模型来源**，随时切换（对应 Sia 把模型调用放在服务端，这里交给你自己）

## 三种模型来源

| 来源 | 适合谁 | 怎么配 |
|---|---|---|
| **离线导学** | 没网、没密钥、先体验 | 默认，规则式引导，永远可用 |
| **OpenAI 兼容 API** | 有 DeepSeek / OpenAI / 中转订阅 | 设置页填 Base URL、Key、模型名；或用环境变量 |
| **本地 Ollama** | 想完全本地、不花钱调 API | 装 Ollama → `ollama pull qwen2.5` → 设置页选 Ollama |

**任何 OpenAI 兼容端点都能接**：DeepSeek(`https://api.deepseek.com/v1`)、OpenAI(`https://api.openai.com/v1`)、通义、Moonshot、本地 LM Studio、自建中转订阅……只要填对 Base URL + 模型名。

### 密钥安全
- 密钥**只存本机** `data/config.json`（已加入 `.gitignore`），或走环境变量 `OPEN_TUTOR_API_KEY`（优先级更高）。
- 前端展示一律脱敏，日志和输出中从不打印密钥。
- **不要把填了密钥的 config.json 提交或分享。**

## 快速开始

### 方式一：桌面软件（推荐，Windows）

下载 `OpenTutor.exe`，双击即可。它会开出一个**独立窗口**（没有浏览器地址栏，和普通软件一样），关掉窗口软件就退出。

- 无需安装 Python，无需输入网址。
- 你的会话和设置存在 exe 同目录的 `data/` 里，关掉重开不会丢。
- 首次运行会在 `data/edge-profile/` 建一个独立浏览器配置，不影响你日常的 Edge。

自己打包：先 `pip install pyinstaller pillow`，再双击 `build.bat`，产物在 `dist/OpenTutor.exe`。

### 方式二：源码运行（全平台）

需要 Python 3.8+（只用标准库，无需 `pip install`）。

```bash
cd open-tutor
python selftest.py      # 可选：自检
python server.py
```

浏览器打开 **http://127.0.0.1:8766** 。Windows 用户可直接双击 `start.bat`。端口被占用会自动换一个。

## 目录结构

```
open-tutor/
├── server.py           # HTTP 服务与 API 路由
├── config.py           # 配置与密钥脱敏
├── model_provider.py   # 模型适配层：API / Ollama / 离线
├── tutor.py            # 导学、白板、产物生成
├── memory.py           # 间隔复习算法
├── store.py            # SQLite 持久化
├── curriculum.py       # 内置题库与学科
├── selftest.py         # 自检（36 项）
├── paths.py            # 统一路径（源码/exe 通吃，数据落 exe 旁）
├── desktop.py          # 桌面版入口：内置服务 + Edge 独立窗口
├── make_icon.py        # 生成软件图标
├── build.bat           # 一键打包成 OpenTutor.exe
├── static/             # Web 前端（原生 HTML/CSS/JS）
├── start.py / start.bat# 源码启动脚本
├── data/               # 运行时生成：config.json、tutor.db（gitignore）
└── README.md / LICENSE
```

## 与 Sia 的对应关系

| Sia 的能力 | OpenTutor 实现 |
|---|---|
| 苏格拉底式解题对话 | `tutor.py` 系统提示 + 会话历史 |
| 白板逐步揭示（board reveal） | `/api/board` + `parse_board` |
| tutor_memory 间隔复习 | `memory.py` SM-2 |
| artifact_versions 产物版本 | `store.add_artifact` 版本号自增 |
| test-prep 考试目录 | `curriculum.py` |
| 桌宠 / 积分 / 按分钟计费 | 未复刻（开源版不需要计费与游戏化外壳） |
| 实时语音课（ASR+TTS+三轨同步） | 未复刻（最难的一层，超出轻量开源版范围） |

## 扩展

- 加题库：编辑 `curriculum.py` 的 `EXAMS` / `SAMPLE_QUESTIONS`
- 换提示词：编辑 `tutor.py` 顶部的 `SYSTEM_*` 常量
- 接新模型：只要兼容 OpenAI chat/completions 格式，直接用 openai 模式填 Base URL

## License

MIT — 随便用、随便改、随便分发。见 [LICENSE](LICENSE)。
