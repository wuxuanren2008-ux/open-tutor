"""模型适配层：OpenAI 兼容 API / Ollama 本地 / 离线规则引擎。

统一接口 provider.chat(messages, **kwargs) -> str。
任何 OpenAI 兼容端点（DeepSeek、OpenAI、通义、本地中转订阅、LM Studio）都能用 openai 模式填 base_url 接入。
密钥不打印、不落日志；异常信息经清洗后返回。
"""
import json
import urllib.error
import urllib.request


def _post_json(url, payload, headers=None, timeout=60):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _safe_error(err):
    text = str(err)
    # 避免把可能含 key 的 URL/头回显
    if "HTTP Error" in text:
        return "HTTP " + text.split("HTTP Error")[-1].strip().split(":")[0]
    return text[:160]


class OpenAICompatibleProvider:
    def __init__(self, base_url, api_key, model, temperature=0.7, timeout=60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def chat(self, messages, **kwargs):
        url = self.base_url + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "stream": False,
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        try:
            resp = _post_json(url, payload, headers, self.timeout)
            return resp["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            return "[调用失败] HTTP %s，请检查 base_url / 模型名 / 密钥。" % e.code
        except Exception as e:
            return "[调用失败] %s" % _safe_error(e)


class OllamaProvider:
    def __init__(self, base_url, model, temperature=0.7, timeout=120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def chat(self, messages, **kwargs):
        url = self.base_url + "/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": kwargs.get("temperature", self.temperature)},
        }
        try:
            resp = _post_json(url, payload, None, self.timeout)
            return resp.get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            return "[本地模型失败] HTTP %s，确认 Ollama 已启动且模型已拉取。" % e.code
        except Exception as e:
            return "[本地模型失败] %s" % _safe_error(e)


def _last_user(messages):
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


class OfflineProvider:
    """无网络、无密钥时的规则引擎。导学/笔记/抽认卡/板书全部可用，保证软件始终能演示完整流程。"""

    def chat(self, messages, **kwargs):
        sys_text = " ".join(m.get("content", "") for m in messages if m.get("role") == "system")

        # 学习产物请求：从拼接的对话里抽出学生问题
        if "抽认卡" in sys_text or "生成抽认卡" in sys_text:
            convo = _last_user(messages)
            questions = [seg.split("导师：")[0].strip() for seg in convo.split("学生：")[1:]]
            questions = [q for q in questions if q][:8]
            if not questions:
                questions = ["示例问题：离线模式演示"]
            return "\n".join("%s | （离线模式：请自行填写答案，接入 API 后自动生成）" % q[:80]
                             for q in questions)

        if "学习笔记" in sys_text or "解题过程" in sys_text:
            convo = _last_user(messages)
            questions = [seg.split("导师：")[0].strip() for seg in convo.split("学生：")[1:]]
            questions = [q for q in questions if q][:8]
            body = "\n".join("%d. %s" % (i + 1, q[:80]) for i, q in enumerate(questions))
            heading = "解题过程" if "解题过程" in sys_text else "学习笔记"
            return ("# %s（离线模式）\n\n## 涉及问题\n%s\n\n"
                    "## 待补充\n接入 API 或本地模型后，这里会自动生成完整讲解、公式与易错点。"
                    % (heading, body or "- 暂无对话内容"))

        if "白板" in sys_text or "板书" in sys_text or "步骤" in sys_text:
            convo = _last_user(messages)
            answer = convo.split("参考解答：")[-1].strip() if "参考解答：" in convo else convo
            blocks = [b.strip() for b in answer.split("\n") if b.strip()][:8] or ["先理解题意"]
            return "\n\n".join("【步骤%d】%s\n离线模式：接入模型后自动细化。" % (i + 1, b[:40])
                               for i, b in enumerate(blocks))

        q = _last_user(messages).strip()
        if not q:
            return "同学你好，把你的问题发给我，我会一步步带你理清。"
        subject = ""
        for m in messages:
            if m.get("role") == "system" and "学科" in m.get("content", ""):
                subject = "（%s）" % m.get("content", "").split("学科")[-1].strip()[:20]
        return (
            "我先不直接给答案，咱们一起把它拆开。%s\n\n"
            "1. 你问的是「%s」——先说说你自己目前的理解是什么？\n"
            "2. 题目给了哪些已知条件？要求的是什么？分别列出来。\n"
            "3. 想一想哪条定义、公式或定理和它有关，哪怕是猜测也写出来。\n"
            "4. 试着把问题换一种说法讲给我听，很多时候讲着讲着思路就来了。\n\n"
            "你现在先回答第 1 步，我再带你往下走。\n\n"
            "（当前为离线导学模式。在「设置」里接上 API 或本地 Ollama，就能得到真正的 AI 解答。）"
            % (subject, q[:60])
        )


def create_provider(cfg):
    kind = cfg.get("provider", "offline")
    if kind == "openai":
        return OpenAICompatibleProvider(
            cfg.get("base_url", "https://api.deepseek.com/v1"),
            cfg.get("api_key", ""),
            cfg.get("model", "deepseek-chat"),
            cfg.get("temperature", 0.7),
            cfg.get("timeout", 60),
        )
    if kind == "ollama":
        return OllamaProvider(
            cfg.get("ollama_base_url", "http://127.0.0.1:11434"),
            cfg.get("ollama_model", "qwen2.5"),
            cfg.get("temperature", 0.7),
            cfg.get("timeout", 120),
        )
    return OfflineProvider()


def test_provider(cfg):
    """连通性自检：返回 (是否成功, 说明)。不泄露密钥。"""
    from config import get_config
    p = create_provider(cfg)
    if isinstance(p, OfflineProvider):
        return True, "离线模式可用，无需连接"
    probe = [
        {"role": "system", "content": "只回复 OK 两个字母。"},
        {"role": "user", "content": "测试连接"},
    ]
    reply = p.chat(probe, temperature=0)
    ok = not reply.startswith("[调用失败]") and not reply.startswith("[本地模型失败]")
    label = cfg.get("model") if cfg.get("provider") == "openai" else cfg.get("ollama_model")
    return ok, ("连接成功，模型 %s 已响应：%s" % (label, reply[:40])) if ok else reply
