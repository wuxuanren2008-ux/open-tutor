"""导学逻辑层：复刻 Sia 的苏格拉底式解题、白板分步揭示、学习产物生成。"""
import re


SYSTEM_TUTOR = (
    "你是一位耐心的导师，正在辅导学生（多为留学生）。严格遵守：\n"
    "1. 不直接给出最终答案，用苏格拉底式提问引导学生自己推导出答案；\n"
    "2. 把解题过程拆成清晰的步骤，一步一步来，每步都让学生先想一想；\n"
    "3. 用学生能懂的例子，关键公式和概念要解释清楚；\n"
    "4. 学生答错时给提示而不是批评，答对时肯定并推进下一步；\n"
    "5. 用 Markdown 书写，公式用 $...$，列表用序号。"
)

SYSTEM_BOARD = (
    "[OPENTUTOR:BOARD]\n"
    "把下面的解答拆成白板式分步板书。每一步用形如「【步骤N】标题」开头，"
    "下面是该步的要点，简洁、适合逐步揭示。只输出步骤，不要额外寒暄。"
)

SYSTEM_ARTIFACT = {
    "notes": "把这段对话整理成一份结构清晰的学习笔记，用 Markdown，含核心概念、公式、易错点。",
    "solution": "把这段对话整理成一份标准解题过程，用 Markdown，步骤完整、可直接复习。",
    "flashcards": "根据这段对话生成抽认卡，每行一张，格式：问题 | 答案。至少 5 张。",
}


def build_messages(history, question, subject):
    """把会话历史 + 新问题组装成模型输入。"""
    msgs = [{"role": "system", "content": SYSTEM_TUTOR}]
    if subject:
        msgs.append({"role": "system", "content": "当前学科：%s" % subject})
    for item in history:
        if item.get("role") in ("user", "assistant"):
            msgs.append({"role": item["role"], "content": item.get("content", "")})
    msgs.append({"role": "user", "content": question})
    return msgs


def tutor_reply(provider, history, question, subject):
    return provider.chat(build_messages(history, question, subject))


def board_steps(provider, answer, question):
    """把一段解答转成白板分步。"""
    msgs = [
        {"role": "system", "content": SYSTEM_BOARD},
        {"role": "user", "content": "题目：%s\n\n参考解答：\n%s" % (question, answer)},
    ]
    return provider.chat(msgs)


def parse_board(text):
    """把「【步骤N】...」文本解析成步骤列表。"""
    parts = re.split(r"【步骤\s*\d+\s*】", text)
    steps = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        lines = p.splitlines()
        title = lines[0].strip() or "步骤"
        body = "\n".join(lines[1:]).strip()
        steps.append({"title": title, "body": body})
    if not steps:
        # 没按格式输出时，按空行/换行兜底切成最多 8 步
        chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if c.strip()]
        steps = [{"title": "步骤 %d" % (i + 1), "body": c} for i, c in enumerate(chunks[:8])]
    return steps


def make_artifact(provider, kind, history):
    """生成学习产物：笔记 / 解题过程 / 抽认卡。"""
    sys_prompt = "[OPENTUTOR:ARTIFACT:%s]\n" % kind + SYSTEM_ARTIFACT.get(kind, SYSTEM_ARTIFACT["notes"])
    convo = "\n\n".join(
        ("学生：" if m.get("role") == "user" else "导师：") + m.get("content", "")
        for m in history if m.get("role") in ("user", "assistant")
    )
    msgs = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": convo},
    ]
    return provider.chat(msgs)


def parse_flashcards(text):
    """解析 问题 | 答案 格式的抽认卡。"""
    cards = []
    for line in text.splitlines():
        if "|" in line:
            q, _, a = line.partition("|")
            q, a = q.strip().lstrip("-").strip(), a.strip()
            if q and a and len(cards) < 30:
                cards.append({"question": q, "answer": a})
    return cards
