"""内置题库与备考目录（复刻 Sia 的 test-prep 概念，示例数据可自行扩展）。"""

EXAMS = [
    {"code": "SAT", "name": "SAT", "category": "college-us", "score": "400-1600"},
    {"code": "ACT", "name": "ACT", "category": "college-us", "score": "1-36"},
    {"code": "AP-CALC-AB", "name": "AP Calculus AB", "category": "ap", "score": "1-5"},
    {"code": "AP-CALC-BC", "name": "AP Calculus BC", "category": "ap", "score": "1-5"},
    {"code": "AP-STATS", "name": "AP Statistics", "category": "ap", "score": "1-5"},
    {"code": "AP-PHYS1", "name": "AP Physics 1", "category": "ap", "score": "1-5"},
    {"code": "AP-CHEM", "name": "AP Chemistry", "category": "ap", "score": "1-5"},
    {"code": "AP-PSYCH", "name": "AP Psychology", "category": "ap", "score": "1-5"},
    {"code": "MATH", "name": "通用数学", "category": "general", "score": "-"},
    {"code": "ENGLISH", "name": "学术英语写作", "category": "general", "score": "-"},
]

SAMPLE_QUESTIONS = {
    "MATH": [
        {"q": "求函数 f(x)=x³-3x 的极值点。", "a": "f'(x)=3x²-3=3(x-1)(x+1)，驻点 x=±1。x=-1 为极大值点(f=2)，x=1 为极小值点(f=-2)。"},
        {"q": "计算 lim(x→0) sin(x)/x。", "a": "该极限为 1，可用夹逼定理或洛必达法则得到。"},
    ],
    "AP-STATS": [
        {"q": "什么是 p-value？", "a": "在原假设成立的前提下，观察到当前样本结果或更极端结果的概率。"},
        {"q": "I 型错误和 II 型错误分别是什么？", "a": "I 型错误=弃真（原假设为真却拒绝）；II 型错误=取伪（原假设为假却未拒绝）。"},
    ],
    "ENGLISH": [
        {"q": "什么是 thesis statement？", "a": "论文中一句话概括核心论点，通常出现在引言末尾，全文围绕它展开。"},
    ],
}

SUBJECTS = sorted(set([e["name"] for e in EXAMS] + ["物理", "计算机科学", "经济学"]))
