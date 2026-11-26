"""自检：零网络、零密钥条件下验证全部核心逻辑。运行：python selftest.py"""
import os
import sys
import tempfile

# 用临时目录隔离测试数据
_TMP = tempfile.mkdtemp(prefix="opentutor-test-")
import store
store.DB_PATH = os.path.join(_TMP, "test.db")
import config
config.CONFIG_PATH = os.path.join(_TMP, "config.json")

import memory
import model_provider
import tutor

passed = 0
failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print("  [OK] " + name)
    else:
        failed += 1
        print("  [FAIL] " + name)


def section(t):
    print("\n== " + t + " ==")


def main():
    section("1. 离线导学引擎")
    off = model_provider.OfflineProvider()
    r = off.chat([{"role": "user", "content": "求 x^2+2x 的最小值"}])
    check("离线回复非空", bool(r))
    check("离线回复含引导步骤", "步骤" in r or "1." in r)
    check("离线不直接给答案的声明", "不直接给答案" in r)

    section("2. 配置与密钥脱敏")
    test_key = "sk-testkey1234567890"
    config.save_config({"provider": "openai", "base_url": "https://api.deepseek.com/v1",
                        "api_key": test_key, "model": "deepseek-chat"})
    cfg = config.get_config()
    check("配置写入读取", cfg["provider"] == "openai" and cfg["model"] == "deepseek-chat")
    pub = config.public_config()
    check("密钥脱敏", test_key not in pub["api_key"] and "*" in pub["api_key"])
    check("标记已设密钥", pub["api_key_set"] is True)
    os.environ["OPEN_TUTOR_API_KEY"] = "sk-envoverride"
    check("环境变量覆盖密钥", config.get_config()["api_key"] == "sk-envoverride")
    del os.environ["OPEN_TUTOR_API_KEY"]
    config.save_config({"provider": "offline"})

    section("3. 间隔复习算法")
    r1, i1 = memory.next_schedule(0, 5)
    check("首次答对间隔1天", (r1, i1) == (1, 1))
    r2, i2 = memory.next_schedule(1, 5)
    check("第二次答对间隔3天", (r2, i2) == (2, 3))
    r3, i3 = memory.next_schedule(2, 4)
    check("第三次答对间隔7天", (r3, i3) == (3, 7))
    rbad, ibad = memory.next_schedule(5, 1)
    check("答错回炉归零", (rbad, ibad) == (0, 0))
    check("到期判定-过去到期", memory.is_due("2020-01-01 00:00:00") is True)
    check("到期判定-未来未到期", memory.is_due("2099-01-01 00:00:00") is False)

    section("4. 存储层 CRUD")
    store.init()
    sid = store.create_session("测试会话", "MATH", "s-test001")
    check("建会话", sid == "s-test001")
    check("列会话", any(s["id"] == sid for s in store.list_sessions()))
    store.add_message(sid, "user", "问题1")
    store.add_message(sid, "assistant", "回答1")
    msgs = store.get_messages(sid)
    check("消息存取", len(msgs) == 2 and msgs[0]["role"] == "user")
    v = store.add_artifact(sid, "notes", "学习笔记", "内容A")
    v2 = store.add_artifact(sid, "notes", "学习笔记", "内容B")
    check("产物版本递增", v == 1 and v2 == 2)
    check("产物列表", len(store.list_artifacts(sid)) == 2)
    cid = store.add_card("什么是 p-value", "概率", "AP-STATS")
    check("建卡片", isinstance(cid, int))
    store.review_card(cid, 5, 1, 1, memory.due_date(1))
    cards = store.list_cards()
    check("复习卡更新", cards[0]["reps"] == 1 and cards[0]["interval"] == 1)
    store.bump_counter("questions", 3)
    check("进度计数", int(store.get_progress("questions")) == 3)

    section("5. 导学逻辑")
    # 回归：导学请求不得被误判成学习产物（提示词里含"解题过程/步骤"等普通词）
    normal = tutor.tutor_reply(model_provider.OfflineProvider(), [], "求 x^2 的最小值", "MATH")
    check("导学回复不是产物标题", "# 解题过程" not in normal and "# 学习笔记" not in normal)
    check("导学回复是引导步骤", "先说说" in normal and "1." in normal)
    board_test = tutor.board_steps(model_provider.OfflineProvider(), "求导得解", "题目")
    check("板书走独立分支", "【步骤1】" in board_test)
    msgs = tutor.build_messages([{"role": "user", "content": "旧问题"}], "新问题", "MATH")
    check("系统提示置顶", msgs[0]["role"] == "system" and "苏格拉底" in msgs[0]["content"])
    check("学科注入", any("MATH" in m.get("content", "") for m in msgs))
    check("历史与问题都在", msgs[-1]["content"] == "新问题" and any("旧问题" in m.get("content","") for m in msgs))
    board = "【步骤1】求导\n对 f(x) 求导得 f'(x)。\n\n【步骤2】解零点\n令 f'(x)=0。"
    steps = tutor.parse_board(board)
    check("白板步骤解析", len(steps) == 2 and steps[0]["title"] == "求导")
    fallback_steps = tutor.parse_board("普通文本没有标记")
    check("白板兜底解析", len(fallback_steps) >= 1)
    cards_text = "什么是 p-value | 原假设下的概率\nI型错误 | 弃真"
    parsed = tutor.parse_flashcards(cards_text)
    check("抽认卡解析", len(parsed) == 2 and parsed[0]["question"] == "什么是 p-value")

    section("6. Provider 工厂")
    check("offline 工厂", isinstance(model_provider.create_provider({"provider": "offline"}), model_provider.OfflineProvider))
    check("openai 工厂", isinstance(model_provider.create_provider({"provider": "openai"}), model_provider.OpenAICompatibleProvider))
    check("ollama 工厂", isinstance(model_provider.create_provider({"provider": "ollama"}), model_provider.OllamaProvider))
    ok1, _ = model_provider.test_provider({"provider": "offline"})
    check("离线自检通过", ok1 is True)

    section("7. 题库数据")
    import curriculum
    check("考试目录非空", len(curriculum.EXAMS) >= 10)
    check("示例题存在", len(curriculum.SAMPLE_QUESTIONS["MATH"]) >= 2)

    print("\n" + "=" * 40)
    print("结果: %d 通过 / %d 失败" % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
