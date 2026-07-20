# 化知星 · AI 技能集合

> 7 个化学教学智能技能 · 参赛级 Skills 安装包
> 对齐：人教版初中化学课标 · 面向 12-15 岁学生与初中化学教师
> 适用：桂教通·教育智能体创新与应用赛道

---

## 一、技能拓扑

```
chem-dispatcher  (项目根 SKILL.md：顶层总调度 — 元问题分流 + Agent 调度 + Skill 调度)
       │
   ├── 元问题（能力咨询/使用引导）→ 直接答复
       │
   └── 具体化学教学请求 → chem-skill-router (Skill 层子调度器：6 类业务意图路由)
                              │
                              ├── qa          → 直接答复
                              ├── quiz        → chem-lianxi   (AI 智能练习题)
                              ├── experiment  → chem-shiyan   (AI 智能实验)
                              ├── profile     → chem-xueqing  (AI 学情分析)
                              ├── teaching    → chem-jiaoxue  (AI 教学业务过程)
                              └── doc         → chem-wenkuai  (AI 文档解析)
```

---

## 二、7 个 Skill 清单

| 技能 | 路径（相对项目根）| 职责 | 主要触发关键词 |
|------|---------------|------|-------------|
| chem-dispatcher | `SKILL.md`（项目根）| **顶层总调度**：元问题分流 + Agent 调度 + Skill 调度 | 化知星、能做什么、Help、初中化学 |
| chem-skill-router | `skills/chem-skill-router/SKILL.md` | **Skill 层子调度器**：6 类业务意图路由 | 化学教学、化学实验、化学出题 |
| chem-xueqing | `skills/chem-xueqing/SKILL.md` | 五维能力诊断 + 提升方案 | 学情、能力评估、薄弱点 |
| chem-lianxi | `skills/chem-lianxi/SKILL.md` | 四题型命题 + 答案解析 | 出题、命题、试卷、练习题 |
| chem-shiyan | `skills/chem-shiyan/SKILL.md` | 8 段实验操作引导 | 实验步骤、仪器组装、虚拟实验 |
| chem-jiaoxue | `skills/chem-jiaoxue/SKILL.md` | 报告批改/误差/物料/复盘 | 报告批改、教案、误差分析 |
| chem-wenkuai | `skills/chem-wenkuai/SKILL.md` | PDF/Word/图片文档解析 + 结构化问答 | 上传文档、解析 PDF、文档快答 |

---

## 三、Skills 安装包结构（参赛交付）

```
skills/                                ← Skills 安装包根目录
├── README.md                          ← 本文件（安装说明 + 依赖说明）
│
├── chem-skill-router/                  ← Skill 层子调度器（业务技能路由）
│   ├── SKILL.md
│   └── references/
│       └── 完整知识库映射.md           ← 6 库 ↔ 7 skill 路由矩阵
│
├── chem-xueqing/                      ← 学情分析技能
│   ├── SKILL.md
│   └── references/
│       └── 五维能力诊断标准.md
│
├── chem-lianxi/                       ← 出题技能
│   ├── SKILL.md
│   └── references/
│       ├── 题型模板库.md
│       ├── 考试高频考点清单.md
│       └── 化学计算专项与例题.md       ← 8 大计算题型 + 9 道经典例题
│
├── chem-shiyan/                       ← 实验引导技能
│   ├── SKILL.md
│   └── references/
│       ├── 实验仪器图文清单.md
│       └── 12必考实验速查卡.md
│
├── chem-jiaoxue/                      ← 教学业务技能
│   ├── SKILL.md
│   └── references/
│       └── 批改评分细则.md
│
└── chem-wenkuai/                      ← 文档解析技能
    └── SKILL.md                       ← 解析规则内联（无独立 references）
```

**自包含特性**：每个 chem-*/ 目录可独立复制到任意位置运行，不依赖父级目录或外部路径。所有 references均为技能专属本地资源。

---

## 四、注册到智能体平台

### 方式 A：软链接（推荐，开发期自动同步）

```powershell
# PowerShell 管理员模式运行
$src = "E:\AIProgram\化学AI虚拟实验skills\skills"
$dst = "$env:USERPROFILE\.claude\skills"

foreach ($name in @("chem-skill-router","chem-xueqing","chem-lianxi","chem-shiyan","chem-jiaoxue","chem-wenkuai")) {
    New-Item -ItemType SymbolicLink -Path "$dst\$name" -Target "$src\$name"
}

# 注：chem-dispatcher 位于项目根 SKILL.md，作为项目级入口总调度技能单独软链接
New-Item -ItemType SymbolicLink -Path "$dst\chem-dispatcher" -Target "E:\AIProgram\化学AI虚拟实验skills\SKILL.md"
```

### 方式 B：复制（参赛部署推荐，独立可移植）

```powershell
# 把整个 skills/ 目录内容复制到智能体平台技能目录
Copy-Item -Path "E:\AIProgram\化学AI虚拟实验skills\skills\chem-*" `
          -Destination "$env:USERPROFILE\.claude\skills\" -Recurse
```

注册后重启智能体平台，在对话中触发关键词即可自动调用对应 Skill。

### 方式 C：项目级注册（仅当前项目可用）

将 `skills/chem-*/` 复制到项目目录下的 `.claude/skills/`：
```powershell
Copy-Item -Path "chem-*" -Destination ".\.claude\skills\" -Recurse
```

---

## 五、依赖说明

### 5.1 运行环境

| 依赖 | 版本/要求 | 用途 |
|-----|---------|-----|
| AI 智能体平台 | 最新版 | Skills 加载器 |
| 操作系统 | Windows 10 / macOS / Linux | 跨平台支持 |
| 终端编码 | UTF-8 | 中文 + 化学符号正确显示 |

### 5.2 Skills 内部依赖

- **无外部代码依赖**：Skills 纯 Markdown 定义，不含可执行代码
- **无第三方 API 依赖**：所有逻辑由大语言模型执行
- **跨技能调用**：通过 skill name 软引用（如 `chem-lianxi`），不硬编码路径

### 5.3 知识库依赖（外部资源）

Skills 层引用 6 个化学知识库（kb-01 ~ kb-06），这些知识库**不打包进 Skills 安装包**，而是由 Dify Agent 绑定检索：

| 知识库 | 字数 | 主要服务技能 | 调用方式 |
|-------|-----|------------|---------|
| kb-01 课标必考实验库（15 实验）| 11500 | chem-shiyan / chem-jiaoxue | Dify RAG 检索 |
| kb-02 危险操作风险库（31 条）| 13858 | chem-shiyan / chem-jiaoxue | Dify RAG 检索 |
| kb-03 变量对照探究实验库（8 条）| 4876 | chem-shiyan | Dify RAG 检索 |
| kb-04 居家安全拓展实验库（8 条）| 5340 | chem-shiyan | Dify RAG 检索 |
| kb-05 安全闯关题库（52 题）| 20670 | chem-lianxi | Dify RAG 检索 |
| kb-06 初中化学考点速查（90+ 方程式 + 6 附录）| 20566 | 全部 | Dify RAG 检索 |

> 知识库源文件位于项目根 `knowledge-base/`，详见项目 README.md「知识库」章节。

---

## 六、知识库集成说明（参赛合规）

### 6.1 来源

- **kb-01/02/03/04**：团队基于人教版初中化学教材（2022 新课标）自主整理
- **kb-05**：基于教育部《中小学实验室安全规范》汇编
- **kb-06**：基于人教版教材 12 单元考点 + 中考真题方程式归纳
- 所有内容**无版权争议**，可公开用于教育教学

### 6.2 结构

每个 kb-XX 文件统一格式：
```markdown
---
id: kb-XX
title: <库标题>
version: 1.1.0
grade: 九年级
textbook: 人教版
curriculum: 2022新课标
coverage: <覆盖范围>
last_updated: YYYY-MM-DD
---

# 库标题

## 条目编号 · 条目名称
### 子标题（目的/原理/步骤/现象/安全/错误/采分点）
...
```

### 6.3 在智能体中的调用方式

1. **Dify Agent 绑定**：每个 Agent 在 Dify 平台绑定 1-2 个知识库
2. **RAG 检索**：用户提问时，Dify 按相似度检索 Top-K 分块
3. **Skills 层引用**：Skills 通过库名（如 `kb-06-初中化学考点速查`）软引用，不依赖文件路径
4. **路径解耦**：Skills 安装包可独立部署，知识库由 Dify 平台托管

---

## 七、共享约束（5 个 Skill 一致）

| 约束 | 内容 |
|------|------|
| **语言** | 简体中文为唯一输出；化学方程式/元素符号用国际标准符号 |
| **课标贴合** | 引用必须符合人教版初中化学课标；不确定标「需与教材核对」 |
| **安全红线** | 实验操作必须前置 🛡️ 安全提示；不提供可复现的危险操作步骤 |
| **方程式规范** | 必须配平 + 标注反应条件（△/点燃/催化剂/高温） |
| **隐私保护** | 不询问/记录姓名、学校；不承接非化学教学范畴的服务 |
| **分层适配** | 自动识别学困生/中等生/优等生并调整语言深度 |

---

## 八、使用示例

### 示例 1：学生问实验步骤
```
用户：「电解水实验完整步骤是什么？」
→ chem-dispatcher 识别 experiment
→ 调用 chem-shiyan
→ 输出 8 段结构化引导
```

### 示例 2：教师出练习题
```
用户：「出 5 道金属活动性选择题，九年级中等生难度」
→ chem-dispatcher 识别 quiz
→ 调用 chem-lianxi
→ 输出 5 道选择题 + 参考答案与解析
```

### 示例 3：学生要学情诊断
```
用户：「这学期实验易错点集中在哪？怎么提升？」
→ chem-dispatcher 识别 profile
→ 调用 chem-xueqing
→ 输出五维能力雷达 + 提升方案
```

### 示例 4：教师批改报告
```
用户：「帮我批改这份二氧化碳制取实验报告」
→ chem-dispatcher 识别 teaching
→ 调用 chem-jiaoxue（子任务 A：报告批改）
→ 输出多维评分 + 分项批注 + 标准答案对照
```

---

## 九、SKILL.md 内部约定

每个 SKILL.md 末尾的"关联技能/关联资源"章节统一标注：
- **上游**：哪个 dispatcher 识别的意图（子技能独有）
- **协同/下游**：其他子 skill 的调用时机
- **辅助参考**：本技能专属的 references/ 文件（相对路径，自包含）
- **知识库**：按需引用的 kb-XX 知识库（仅 dispatcher 列全 6 库）

修改 SKILL.md 后无需重新编译，重启智能体平台即可生效。

---

## 十、部署验证

注册完成后，执行以下命令验证 Skills 是否生效：

```powershell
# 1. 确认技能目录存在
ls $env:USERPROFILE\.claude\skills\chem-*

# 2. 启动智能体平台并测试触发词
claude
# 输入：「电解水实验完整步骤」→ 应自动调用 chem-shiyan
# 输入：「出 3 道金属活动性选择题」→ 应自动调用 chem-lianxi
```

如未触发，检查：
- 软链接/复制是否成功
- SKILL.md frontmatter 的 name + description 是否正确
- 智能体平台是否已重启
