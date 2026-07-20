# 化知星 · 初中化学+AI+虚拟实验智能体（Dify Skills 集）

> 面向 12-15 岁初中生与化学教师的化知星 AI 智能体集合，剥离自「初中化学+AI+虚拟实验智能体」项目的 AI 能力层，以 Dify Skills 形式独立交付。
>
> 架构对标已验证的 `zctk-skills`（1 总调度 + 5 子 Agent + 6 知识库 + Python 工具）。

---

## 目录

1. [项目简介](#一项目简介)
2. [架构总览](#二架构总览)
3. [Skills 能力矩阵（子技能层）](#三skills-能力矩阵子技能层)
4. [七大智能体（Dify YML）](#四七大智能体dify-yml)
5. [六大知识库](#五六大知识库)
6. [Python 工具脚本](#六python-工具脚本)
7. [导入 Dify 步骤](#七导入-dify-步骤)
8. [前端调用示例](#八前端调用示例)
9. [辅助参考文件](#九辅助参考文件)
10. [知识库扩充记录](#十知识库扩充记录)
11. [验证清单](#十一验证清单)（含参赛提交物文档索引）
12. [技术信息](#十二技术信息)

---

## 一、项目简介

**定位**：纯 Dify 智能体项目，无 Vue 页面、无低代码包。YML 可直接导入 Dify 或桂教通平台运行。

**覆盖能力**：
- 实验操作引导与安全规范
- 化学知识问答（分层适配：学困生/中等生/优等生）
- 智能命题出题（四题型 + DOCX）
- 学情诊断与个性化训练
- 教学业务过程（报告批改/误差分析/物料生成/预习复盘）
- **文档解析与快答（PDF/Word/TXT/图片→结构化问答）**

**核心特性**：
- 统一模型 `Doubao-Seed-1.6`（火山引擎 MaaS）
- 统一 Reranking `bge-reranker-base`（xinference）
- DOCX 输出 `stvlynn/doc` 插件
- 六大化学知识库 RAG 检索

---

## 二、架构总览

```
┌────────────────────────────────────────────────────────────────┐
│                  用户输入（自然语言化学问题 + 文档附件）          │
└──────────────────────────┬─────────────────────────────────────┘
                           ▼
              ┌────────────────────────┐
              │  agent-00 化知星总调度  │   (workflow, 轻量路由)
              │  LLM 意图识别 (temp 0.3)│
              └────────────┬───────────┘
          ┌────────────────┼────────────────────┐
          ▼                ▼                ▼   ▼   ▼
     qa/quiz         experiment/      profile/   doc
     ↓  ↓             teaching        ↓          ↓
     │  │             ↓     ↓         │          │
     ▼  ▼             │     ▼         │          ▼
┌──────────────────────────────────────────────────────────────┐
│ agent-01  agent-02  agent-03  agent-04  agent-05  agent-06   │
│ 智能助教  智能练习  智能实验  学情分析  教学业务  文档解析    │
│ (agent-   (workflow+ (work-   (work-   (workflow (agent-     │
│  chat)    DOCX)     flow+     flow+   +if-else+ chat+       │
│           出题      file)     DOCX)    DOCX)    file)        │
│ ReAct     5路由     5路由     诊断     4路由    5类文档      │
│ 5轮迭代   DOCX      Markdown   五维    多模板   PDF/Word/IMG │
└──────────────────────────────────────────────────────────────┘
          │                │                │           │
          ▼                ▼                ▼           ▼
   ┌──────────────────────────────────────────┐
   │   六大化学 RAG 知识库（kb-01 ~ kb-06）    │
   │   课标必考 / 危险操作 / 变量探究 /         │
   │   居家拓展 / 安全闯关 / 考点速查           │
   └──────────────────────────────────────────┘
```

---

## 三、Skills 能力矩阵（子技能层）

项目含 7 个 AI 技能（Skill），由 SKILL.md 定义、智能体平台加载器自动识别。架构为 **1 顶层调度 + 1 子调度 + 5 业务技能**。

### 3.1 7 个 Skill 清单

| # | 技能名 | 路径 | 职责 | 触发意图 |
|---|--------|------|------|---------:|
| 0 | **chem-dispatcher** | `SKILL.md`（项目根）| **顶层总调度**：元问题分流 + Agent 调度 + Skill 调度 | 全部入口 |
| 1 | **chem-skill-router** | `skills/chem-skill-router/SKILL.md` | **Skill 层子调度器**：6 类业务意图路由 | 具体化学教学请求 |
| 2 | **chem-shiyan** | `skills/chem-shiyan/SKILL.md` | AI 智能实验：8 段结构化引导（预习/实操/复盘/居家） | experiment |
| 3 | **chem-lianxi** | `skills/chem-lianxi/SKILL.md` | AI 智能练习题：四题型命题 + DOCX 输出 | quiz |
| 4 | **chem-jiaoxue** | `skills/chem-jiaoxue/SKILL.md` | AI 教学业务：报告批改/误差分析/物料生成/预习复盘 | teaching |
| 5 | **chem-xueqing** | `skills/chem-xueqing/SKILL.md` | AI 学情分析：五维能力雷达 + 薄弱点定位 + 专项推荐 | profile |
| 6 | **chem-wenkuai** | `skills/chem-wenkuai/SKILL.md` | AI 文档解析：PDF/Word/图片→结构化问答（5 类文档路由）| doc |

> 纯知识问答（qa）由 chem-skill-router 直接答复，无需调用业务子技能。

### 3.2 技能调用拓扑

```
用户输入（自然语言 + 可含文件附件）
       │
       ▼
 chem-dispatcher（顶层总调度 · 项目根 SKILL.md）
       │
   ├── 元问题（"化知星能做什么""有哪些技能"）→ 直接答复
   │
   └── 具体化学教学请求 → chem-skill-router（Skill 层子调度器）
                              │
                          ┌───┼───────┬───────────┬──────────┬──────────┐
                          ▼   ▼       ▼           ▼          ▼          ▼
                         qa  quiz  experiment  profile   teaching     doc
                          │   │       │           │          │          │
                          │ chem-lianxi chem-shiyan chem-xueqing chem-jiaoxue chem-wenkuai
                          │   │       │           │          │          │
                          └───┴──直接答复┴─────────┴──────────┴──────────┘
```

**调用方式**：读取对应 `SKILL.md` → 严格按其执行流程章节操作 → 输出符合其输出模板。

### 3.3 Skills 共享约束（所有技能共同遵守）

| 约束 | 内容 |
|------|------|
| **语言** | 简体中文唯一输出；化学方程式/元素符号用国际标准符号 |
| **课标贴合** | 引用必须符合人教版初中化学课标；不确定标注「需与教材核对」 |
| **安全红线** | 实验操作前置 ⚠️ 安全提示；不提供可复现的危险操作步骤 |
| **方程式规范** | 必须配平并标注反应条件（△、点燃、催化剂、高温等） |
| **分层适配** | 自动识别学生层次（学困生/中等生/优等生）调整语言深度 |
| **隐私保护** | 不询问/记录姓名、学校；学情数据自动脱敏 |

### 3.4 知识库 ↔ Skills 对应关系

6 个化学 RAG 知识库位于 `knowledge-base/`，由 Dify Agent 绑定检索；Skills 层通过引用知识库内容指导生成。详细路由矩阵见 `skills/references/完整知识库映射.md`。

| 知识库 | 主要服务技能 |
|--------|-------------|
| kb-01 课标必考实验库（15 实验）| chem-shiyan / chem-jiaoxue / chem-wenkuai |
| kb-02 危险操作风险库（31 条）| chem-shiyan / chem-jiaoxue / chem-wenkuai |
| kb-03 变量对照探究实验库（8 条）| chem-shiyan |
| kb-04 居家安全拓展实验库（8 条）| chem-shiyan |
| kb-05 安全闯关题库（52 题）| chem-lianxi |
| kb-06 初中化学考点速查（90+ 方程式 + 6 附录）| 全部 |

---

## 四、七大智能体（Dify YML）

| # | Agent | 文件 | 模式 | 知识库依赖 | 输出 |
|---|-------|------|------|-----------|------|
| 00 | 化知星·总调度 | `agent-00-化知星总调度.yml` | workflow | 无（纯路由） | Markdown 答复 |
| 01 | 智能助教 | `agent-01-智能助教.yml` | agent-chat | 6 库全绑 | Markdown 答疑 |
| 02 | AI智能练习题 | `agent-02-AI智能练习题.yml` | workflow | 5 路由（基础/变量/居家/安全/综合） | Markdown + DOCX |
| 03 | AI智能实验 | `agent-03-AI智能实验.yml` | workflow | 5 路由（同上）+ 支持校本素材文件 | Markdown 引导 |
| 04 | AI学情分析 | `agent-04-AI学情分析.yml` | workflow | 考点速查 + 课标必考 | Markdown + DOCX |
| 05 | AI教学业务过程 | `agent-05-AI教学业务过程.yml` | workflow | 4 路由（批改/误差/物料/预习）+ 支持报告文件 | Markdown + DOCX |
| 06 | **AI文档解析** | `agent-06-AI文档解析.yml` | agent-chat | kb-01/02/06 + 多模态 | Markdown 结构化摘要 |

### 智能体详解

#### agent-00 · 化知星总调度（workflow）
- **节点**：start → llm-classify（temp 0.3） → if-else 5 分支 → 5 个 LLM 子分支 → end
- **意图分类**：`qa`（答疑）/ `quiz`（出题）/ `experiment`（实验）/ `profile`（学情）/ `teaching`（教学业务）
- **特点**：轻量级路由器，不挂知识库；每个子分支输出简短指引，详细内容由专项 Agent 处理。

#### agent-01 · 智能助教（agent-chat）
- **策略**：ReAct（max 5 轮迭代）
- **知识库**：绑定全部 6 个化学知识库 + reranking
- **三种语态**：基础讲解（学困生）/ 规范讲解（中等生）/ 拓展探究（优等生）
- **四模板**：知识问答 / 实验操作 / 误差分析 / 安全解析
- **六项约束**：安全红线优先 / 课标贴合 / 分层自适应 / 完整闭环 / 隐私保护 / 单轮克制

#### agent-02 · AI智能练习题（workflow）
- **13 输入**：exp_layer / exp_topic / grade / textbook / chapter / type / level / student_level / xuanze / panduan / tiankong / jianda / bcsm
- **路由**：基础层→[01,06] / 变量层→[03,06] / 居家层→[04] / 安全层→[02,05] / 综合→[06,01]
- **流程**：start → 时间 → if-else → 5×knowledge-retrieval → 变量聚合 → code 序列化 → LLM 命题 → DOCX → code 提取链接 → end
- **输出**：`text`（Markdown 试卷） + `url`（DOCX 下载链接）

#### agent-03 · AI智能实验（workflow）
- **6 输入**：exp_layer / exp_topic / grade / scene（预习/实操/复盘/居家）/ student_level / focus
- **8 段结构**：实验目的+方程式 / 仪器试剂表 / 分步操作 / 现象与结论表 / 安全提示 / 常见错误纠正 / 考试采分点 / 巩固练习
- **特点**：场景适配（预习启发式 / 实操纠错式 / 复盘归纳式 / 居家科普式）

#### agent-04 · AI学情分析（workflow）
- **5 输入**：student_data / grade / student_level / diagnosis_focus / focus_unit
- **五维能力雷达**：基础操作 / 反应记忆 / 变量思维 / 安全意识 / 数据处理（每维 20 分，满分 100）
- **六段输出**：能力雷达 / 薄弱点定位 / 四维归因（知识+习惯+策略）/ 分层提升建议（短期+中期+长期）/ 专项训练推荐 / 学习路线图
- **输出**：`text` + `url`（DOCX 报告）

#### agent-05 · AI教学业务过程（workflow）
- **7 输入**：business_type / task_content / exp_topic / grade / student_level / bcsm / **report_file（可选 PDF/Word/图片）**
- **4 子任务路由**：
  - **实验报告批改** → 课标必考 + 危险操作 → 多维评分（原理/操作/数据/结论 各 25 分）+ 批注 + 标准答案对照（支持上传文件直接批改）
  - **误差分析** → 课标必考 → 标准数据 vs 学生数据对比 + 四维归因（器材/操作/试剂/环境）+ 标准答题模板
  - **教学物料生成** → 考点速查 + 课标必考 → 预习单/教案/任务单/安全手册
  - **预习复盘**（兜底） → 课标必考 + 考点速查 → 预习清单 + 复盘反思
- **输出**：`text` + `url`（DOCX 报告）

#### agent-06 · AI 文档解析（agent-chat）⭐ 新增
- **模式**：agent-chat + 文件上传（PDF/Word/TXT/图片/CSV/XLSX）
- **支持格式**：文字版 PDF / Word / TXT 直接解析；图片/扫描件通过多模态 LLM 识别
- **五类文档处理流程**：
  - **report（实验报告）** → 对照 kb-01 标准答案 → 标注错误点 → 协同 chem-jiaoxue 完整批改
  - **exam（试卷）** → 按题型拆解 → 标注考点（对照 kb-06）→ 协同 chem-lianxi 生成答案
  - **lesson（教案）** → 检查必考方程式 + 采分点覆盖度 → 输出补充建议
  - **profile（学情表）** → 姓名脱敏 + 五维归因 → 协同 chem-xueqing 完整诊断
  - **material（校本素材）** → 安全审核 + 入库到 kb-01/03/04 → 协同 chem-shiyan
- **隐私红线**：学生姓名/学校自动脱敏；不缓存原文
- **输出**：Markdown 结构化摘要（文件信息 / 识别类型 / 关键发现 / 下一步建议）

---

## 五、六大知识库

| # | 文件 | 字数 | 行数 | 分块 | 条目数 |
|---|------|-----:|-----:|----:|--------:|
| 01 | `kb-01-课标必考实验库.md` | 11692 | 632 | 19 | 15 实验（EXP001-EXP015）+ O2/CO2 性质验证 |
| 02 | `kb-02-危险操作风险库.md` | 13758 | 847 | 33 | 31 条（DNG001-DNG031）+ 交叉引用 |
| 03 | `kb-03-变量对照探究实验库.md` | 4869 | 256 | 11 | 8 条（VAR001-VAR008） |
| 04 | `kb-04-居家安全拓展实验库.md` | 5332 | 318 | 10 | 8 条（HOME001-HOME008） |
| 05 | `kb-05-安全闯关题库.md` | 20606 | 1339 | 55 | **52 题（Q001-Q052）** 五大板块 |
| 06 | `kb-06-初中化学考点速查.md` | 20566 | 791 | 33 | **12 单元 + 90+ 核心方程式** |
| **合计** | — | **76823** | **4183** | **161** | **—** |

详细统计运行 `python scripts/build_knowledge_base.py --stats-only` 后查看 `output/kb-stats.md`。

### 4.1 知识库统一格式

所有 6 个知识库均使用：
- **YAML frontmatter**：`id` / `title` / `version` / `grade` / `textbook` / `curriculum` / `coverage` / `last_updated`
- **条目标题格式**：`## XXX001 · 名称`（统一 `·` 分隔符）
- **标准标识符体系**：📌 考点 / ❌ 错误 / ✅ 正确 / ⚠️ 风险 / 💥 事故 / 🚑 应急 / 🔴 红线口诀 / 🚫 禁止

---

## 六、Python 工具脚本

### 5.1 环境准备

```bash
pip install -r scripts/requirements.txt
# 内容：PyYAML>=6.0
```

### 5.2 `scripts/validate_agents.py` — YML 校验

**功能**：批量校验 `agents/*.yml` 的结构与字段完整性。

**检查项**：
1. YAML 语法正确性
2. 顶层字段（app / kind=app / version）
3. app 元信息（name / mode / description）
4. workflow 结构（含 start + end + 至少 1 个 LLM；每个非 start/end 节点有入边和出边）
5. agent-chat 结构（model_config 完整 + 知识库绑定 + reranking）
6. 依赖插件完整性（volcengine_maas / xinference / stvlynn/doc）
7. 模型一致性（`Doubao-Seed-1.6` / 正确 provider）
8. dataset_id 占位符检测（命名规范 + 未替换计数）
9. 节点-连线连通性（孤立节点检测）

**用法**：

```bash
python scripts/validate_agents.py                       # 校验全部
python scripts/validate_agents.py --file agents/agent-00-化知星总调度.yml
python scripts/validate_agents.py --dir agents --strict  # 严格模式
```

**退出码**：0=通过 / 1=有错误（或严格模式下有告警）/ 2=环境错误

### 5.3 `scripts/build_knowledge_base.py` — 知识库分块 + 统计

**功能**：扫描 `knowledge-base/*.md`，按二级标题切块，输出统计与映射。

**产物**（写入 `output/`）：

| 文件 | 内容 |
|------|------|
| `knowledge-base-chunks.jsonl` | 分块 JSON Lines（每行一个分块，含 id/source/heading/line_range/content） |
| `kb-stats.json` | 原始统计数据 |
| `kb-stats.md` | 可读 Markdown 报告（含整体概览、结构特征、章节清单、扩充建议） |
| `dataset-id-mapping.md` | `REPLACE_WITH_HX_*` 占位符 ↔ 知识库文件名映射表 |

**用法**：

```bash
python scripts/build_knowledge_base.py                 # 全量分块 + 统计
python scripts/build_knowledge_base.py --stats-only    # 仅统计不分块
python scripts/build_knowledge_base.py --dry-run       # 预览不写入
python scripts/build_knowledge_base.py --chunk-size 1000
python scripts/build_knowledge_base.py --kb kb-06-初中化学考点速查.md
```

### 5.4 `scripts/replace_dataset_ids.py` — 占位符批量替换

**功能**：Dify 创建知识库后，将 `agents/*.yml` 中 `REPLACE_WITH_HX_*` 占位符批量替换为真实 dataset_id。

**用法**：

```bash
# 1. 在 Dify 中创建 6 个知识库，记录 dataset_id 到 mapping.json
# 2. 预览替换（dry-run）
python scripts/replace_dataset_ids.py --mapping mapping.json --dry-run

# 3. 执行替换（可选备份）
python scripts/replace_dataset_ids.py --mapping mapping.json --backup

# 4. 替换单个文件
python scripts/replace_dataset_ids.py --mapping mapping.json --file agents/agent-01-智能助教.yml
```

**mapping.json 格式**：
```json
{
  "REPLACE_WITH_HX_01_KEBIAO_BIKAO": "实际-dataset-id-1",
  "REPLACE_WITH_HX_02_WEIXIAN_FENGXIAN": "实际-dataset-id-2",
  ...
}
```

### 5.5 `scripts/common.py` — 公共模块

供 validate_agents.py / build_knowledge_base.py / replace_dataset_ids.py 三个脚本共用的常量与函数：
- `DATASET_ID_MAP`：6 个库的占位符映射
- `VALID_PLACEHOLDERS` / `PLACEHOLDER_PATTERN`：占位符校验
- `EXPECTED_MODEL_NAME` / `EXPECTED_MODEL_PROVIDER`：模型一致性校验
- `setup_utf8_stdio()`：强制 UTF-8 输出
- `get_project_root()`：定位项目根目录

---

## 七、导入 Dify 步骤

### 步骤 1：安装插件

登录 Dify（`agent.gjt-smart.com`）→ 插件市场，确保以下 3 个插件已安装：

- `langgenius/volcengine_maas`（火山引擎模型）
- `langgenius/xinference`（reranking 模型 bge-reranker-base）
- `stvlynn/doc`（Markdown 转 DOCX，仅 agent-02/04/05 需要）

### 步骤 2：创建 6 个知识库

进入 Dify → 知识库 → 逐个上传 `knowledge-base/*.md`，创建 6 个独立知识库。

**推荐设置**：
- 分段方式：自动
- 索引方式：高质量（推荐）
- 检索配置：多路召回 + reranking 模型 `bge-reranker-base`

### 步骤 3：获取 dataset_id

每个知识库页面 → 左侧「API」或 URL 中复制 `dataset_id`（形如 `a1b2c3d4-xxxx-...`）

### 步骤 4：替换 YML 占位符

运行 `python scripts/build_knowledge_base.py` 生成 `output/dataset-id-mapping.md`，按映射表将 `agents/*.yml` 中所有 `REPLACE_WITH_HX_*` 替换为真实 ID（共 33 处）。

**占位符分布**：
- agent-01：6 处（dataset_configs.datasets）
- agent-02：9 处（5 分支 knowledge-retrieval）
- agent-03：9 处（5 分支 knowledge-retrieval）
- agent-04：2 处（1 个 knowledge-retrieval 的 2 个 dataset）
- agent-05：7 处（4 分支 knowledge-retrieval）

### 步骤 5：校验 YML

```bash
python scripts/validate_agents.py
```

确认输出 `总计: 6 | 通过: 6 | 失败: 0`。

### 步骤 6：导入 Dify 工作室

工作室 → 创建空白应用 → 导入 DSL 文件 → 逐个上传 6 个 YML。

### 步骤 7：发布并获取 API Key

每个应用右上角「发布」→「访问 API」→ 复制 API Key（形如 `app-xxxxxxxx`）。

---

## 八、前端调用示例

### 7.1 Workflow 类 Agent（agent-00/02/03/04/05）— 阻塞模式

```javascript
// 以 agent-02 AI智能练习题 为例
const res = await fetch('https://agent.gjt-smart.com/v1/workflows/run', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer app-xxxxxx',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    inputs: {
      exp_layer: '基础层',
      exp_topic: '制取氧气',
      grade: '九年级上',
      textbook: '人教版',
      chapter: '第二单元 我们周围的空气',
      type: '随堂练习',
      level: '基础',
      student_level: '中等生',
      xuanze: '5', panduan: '3', tiankong: '3', jianda: '1',
      bcsm: '侧重加热高锰酸钾法'
    },
    response_mode: 'blocking',
    user: 'student-001'
  })
});
const data = await res.json();
// data.data.outputs.text = Markdown 试卷
// data.data.outputs.url   = DOCX 下载链接
```

### 7.2 Agent-Chat 类（agent-01）— 流式模式

```javascript
// agent-01 智能助教
const res = await fetch('https://agent.gjt-smart.com/v1/chat-messages', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer app-xxxxxx',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    inputs: {},
    query: '制取氧气时试管口为什么要略向下倾斜？',
    response_mode: 'streaming',
    user: 'student-001'
  })
});
// 流式接收 SSE 事件
```

---

## 九、辅助参考文件

除 6 个知识库外，项目还提供 11 个辅助参考文件，分两层组织。

### 8.1 全局参考 `skills/references/`（5 个）

| 文件 | 用途 |
|------|------|
| `完整知识库映射.md` | 6 库 ↔ 5 skill 路由矩阵 + 路径使用规范 |
| `化学方程式速查表.md` | 60+ 方程式按反应类型（化合/分解/置换/复分解/燃烧）编排 |
| `常见物质性质速查表.md` | 气体/固体/氧化物/酸/碱/盐/沉淀 7 类性质表 |
| `初中化学常用数据表.md` | 空气成分/气体性质/溶解度/浓度密度/pH/相对原子质量 |
| `元素周期表初中版.md` | 前 20 号 + 常见金属 + 原子团化合价 + 记忆口诀 |

### 8.2 各 Skill 专用参考（6 个）

| Skill | 文件 | 用途 |
|-------|------|------|
| chem-shiyan | `references/实验仪器图文清单.md` | 7 类 30+ 种初中常用仪器使用规范 |
| chem-shiyan | `references/12必考实验速查卡.md` | 12 张速查卡（方程式+步骤+采分点） |
| chem-lianxi | `references/题型模板库.md` | 4 大题型 17 种变体出题/答题模板 |
| chem-lianxi | `references/考试高频考点清单.md` | 必考点/常考点/轮考点 3 级分类（30 条） |
| chem-jiaoxue | `references/批改评分细则.md` | 8 个实验主题评分细则 + 50 条评语库 |
| chem-xueqing | `references/五维能力诊断标准.md` | 关键词→得分映射 + 置信度评级 |

---

## 十、知识库扩充记录

本次已基于互联网公开知识扩充四个偏薄知识库，全部达到验收标准：

| 知识库 | 扩充前 | 扩充后 | 新增条目 |
|--------|--------|--------|---------|
| `kb-01-课标必考实验库` | 5 实验 / 2873 字 | **15 实验 / 11692 字** | EXP006-EXP015 + 补全"常见错误"子标题 + EXP001/002 性质验证 |
| `kb-02-危险操作风险库` | 5 条 / 1851 字 | **31 条 / 13758 字** | DNG006-DNG031 + 3 组重复条目交叉引用 + 标题统一为"安全红线口诀" |
| `kb-03-变量对照探究实验库` | 3 条 / 1234 字 | **8 条 / 4869 字** | VAR004 催化剂用量 / VAR005 反应物浓度 / VAR006 表面积 / VAR007 pH 曲线 / VAR008 反应时间 |
| `kb-04-居家安全拓展实验库` | 3 条 / 1888 字 | **8 条 / 5332 字** | HOME004 蛋壳与白醋反应 / HOME005 自制灭火器 / HOME006 自制火山喷发 / HOME007 维生素 C 检测 / HOME008 结晶分离食盐 |
| `kb-05-安全闯关题库` | 7 题 / 2250 字 | **52 题 / 20606 字** | Q008-Q052（试剂风险 + 仪器操作 + 废液处理 + 应急处理 + 综合情景） |
| `kb-06-初中化学考点速查` | 19 方程式 / 5827 字 | **90+ 方程式 / 20566 字** | 每单元追加"核心方程式"子标题，第八/九/十/十一单元方程式由 0 补至 40+ |

**新增条目均采用与原库一致的结构**：化学方程式 / 实验步骤 / 标准现象 / 实验结论 / 📌考试采分点 / ❌常见错误（kb-01、03）；⚠️风险识别 / 💥事故推演 / ✅规范操作 / 🚑应急处理 / 🔴安全红线口诀（kb-02）；化学方程式 / 简易器材 / 实验步骤 / 标准现象 / 探究思考 / 🚫居家禁止事项（kb-04）。

> 后续如需进一步扩充，由教师团队按教学进度持续维护；建议同步更新 `output/kb-stats.md`。

---

## 十一、验证清单

| 项 | 命令 | 预期 |
|----|------|------|
| YAML 语法 | `python scripts/validate_agents.py` | **7/7 通过** |
| 占位符检测 | 同上输出 | 36 处全部识别（6 占位符命名规范） |
| 知识库分块 | `python scripts/build_knowledge_base.py` | **161 条分块** |
| 统计报告 | 查看 `output/kb-stats.md` | 6 知识库 / **76823 字** |
| 占位符映射 | 查看 `output/dataset-id-mapping.md` | 6 对映射 |
| 模型一致性 | 校验输出 | 全部 `Doubao-Seed-1.6` |
| 依赖完整性 | 校验输出 | 3 插件齐全（agent-02/04/05 含 stvlynn/doc） |
| 知识库验收 | kb-01≥12 / kb-02≥30 / kb-03≥8 / kb-04≥6 / kb-05 / kb-06 | 15/31/8/8/52/12单元 全部达标 |
| 辅助文件 | `ls skills/references/` + 各 skill 下 references/ | 全局 5 + 各 skill 共 **11 个** |
| 标题分隔符 | `grep -E "^## (EXP\|DNG\|VAR\|HOME)" knowledge-base/*.md` | 全部带 `·` |
| 方程式覆盖 | `grep -c "→" knowledge-base/kb-06-*.md` | ≥ 60 条 |
| 题库数量 | `grep -cE "^## Q[0-9]+" knowledge-base/kb-05-*.md` | ≥ 31 条（实测 52） |

### 十一(附) · 参赛提交物文档索引

> 对照附件3《教育智能体创新与应用赛道参赛作品项目包要求》，提交物文档如下：

| 附件3 条款 | 文档 | 状态 |
|-----------|------|:----:|
| 一 · 智能体访问链接 | （部署至桂教通后获取） | ⏳ |
| 二(一) · 工作流安装包 | `agents/*.yml`（7 个） | ✅ |
| 二(二) · Skills 安装包 | `skills/`（7 Skill + references） | ✅ |
| 三(一) · 功能说明 | 本 README + `需求规格说明.md` | ✅ |
| 三(二) · 场景与工作流设计 | `需求规格说明.md` 第五/六节 + `SKILL.md` 流程图 | ✅ |
| 三(三) · 能力配置说明 | **[`能力配置说明.md`](能力配置说明.md)** | ✅ |
| 三(四) · 知识库说明 | 本 README 第五节 + `skills/references/完整知识库映射.md` | ✅ |
| 四(一) · 演示视频 | （≤5min，待录制） | ⏳ |
| 四(二) · 验证报告 | **[`验证报告.md`](验证报告.md)** + **[`测试用例集.md`](测试用例集.md)** | ✅ |
| — · 提交物全面复核 | **[`提交物复核清单.md`](提交物复核清单.md)** | ✅ |

---

## 十二、技术信息

- **Dify 版本**：0.3.0（DSL schema）
- **Python**：3.9+（脚本兼容）
- **操作系统**：Windows 10 / macOS / Linux
- **编码**：全部 YML / MD / PY 强制 UTF-8（脚本内已 reconfigure stdout）

---

## 附：与 zctk-skills 对标

| 维度 | zctk-skills（参考） | 化知星 Skills（本项目） |
|------|---------------------|------------------------|
| 子 Agent 数 | 4 | **5**（多了 AI教学业务过程） |
| 知识库数 | 6 | **6** |
| 总调度模式 | workflow | workflow |
| 模型 | Doubao-Seed-1.6 | Doubao-Seed-1.6 |
| DOCX 插件 | stvlynn/doc | stvlynn/doc |
| Python 脚本 | validate + build_kb | validate + build_kb + replace_dataset_ids + common |
| 辅助参考文件 | 无 | **11 个**（全局 5 + 各 skill 共 6） |
| 意图分类 | 4 类 | **5 类**（qa/quiz/experiment/profile/teaching） |
