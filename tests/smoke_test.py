"""冒烟测试：不依赖真实大模型 API，验证数据层 / 检索层 / 链构建。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FAILED = []


def check(name):
    def deco(fn):
        try:
            fn()
            print(f"[PASS] {name}")
        except Exception as e:
            FAILED.append((name, repr(e)))
            print(f"[FAIL] {name}: {e!r}")
    return deco


@check("模块导入：config / core / twin / agents")
def _():
    import config
    import core.llm, core.prompts, core.retriever
    import twin.profile, twin.metrics, twin.records, twin.context
    import agents.consultant, agents.interviewer, agents.record_writer
    import agents.report_reader, agents.twin_analyst, agents.care_matcher
    assert config.DATA_DIR.exists()


@check("UI 模块语法检查（不启动界面）")
def _():
    import py_compile
    for f in os.listdir("ui"):
        if f.endswith(".py"):
            py_compile.compile(os.path.join("ui", f), doraise=True)
    py_compile.compile("app.py", doraise=True)


@check("数字孪生档案：写入 / 更新 / 完整度 / BMI")
def _():
    from twin.profile import ProfileStore, HealthProfile
    store = ProfileStore()
    store.update_fields(name="张三", sex="男", age=34, height_cm=175, weight_kg=82.5,
                        chronic_conditions=["高血压"])
    store.update_fields(chronic_conditions=["高血脂"], allergies=["青霉素"])  # 列表合并去重
    p = store.load()
    assert p.name == "张三" and p.age == 34
    assert set(p.chronic_conditions) == {"高血压", "高血脂"}
    assert p.allergies == ["青霉素"]
    assert abs(p.bmi() - 26.9) < 0.1, p.bmi()
    assert 0 < p.completeness() <= 1
    # 清理测试数据
    ProfileStore().save(HealthProfile())


@check("指标存储：记录 / DataFrame / 趋势摘要")
def _():
    from twin.metrics import MetricStore
    store = MetricStore()
    store.add("systolic", 135, "2026-09-01", "")
    store.add("systolic", 148, "2026-10-01", "晨起")
    store.add("sleep_hours", 6.0, "2026-10-01", "")
    df = store.dataframe()
    assert len(df) == 3
    summary = store.summary()
    assert "收缩压" in summary and "148" in summary and "↑" in summary, summary
    # 清理
    store._save_raw([])


@check("病历与报告存储")
def _():
    from twin.records import save_record, list_records, delete_record, save_report, list_reports, delete_report
    rec = save_record("### 主诉\n发热咳嗽三天", title="测试病历")
    rep = save_report("test.txt", "血常规：WBC 11.2↑", analysis="白细胞升高")
    assert list_records()[0]["id"] == rec["id"]
    assert list_reports()[0]["id"] == rep["id"]
    delete_record(rec["id"]); delete_report(rep["id"])
    assert not list_records() and not list_reports()


@check("孪生上下文构建")
def _():
    from twin.context import build_twin_context
    ctx = build_twin_context()
    assert isinstance(ctx, str) and "基础档案" in ctx and "指标趋势" in ctx


@check("知识库检索：BM25 自动降级（无 embedding 配置时）")
def _():
    from core.retriever import KnowledgeBase
    from twin.records import save_record, delete_record
    rec = save_record("患者有2型糖尿病病史五年，近期空腹血糖升高至 8.2", title="检索测试病历")
    kb = KnowledgeBase()
    docs = kb.search("血糖高 糖尿病")
    assert docs, "BM25 应能命中"
    assert any("糖尿病" in d.page_content for d in docs)
    status = kb.status()
    assert "BM25" in status, status
    print(f"       检索模式 -> {status}")
    delete_record(rec["id"])


@check("就医匹配：知识库关键词命中")
def _():
    from agents.care_matcher import keyword_match, load_departments
    deps = load_departments()
    assert len(deps) >= 25
    hits = keyword_match("头晕、血压150/95、心悸")
    names = [h["department"] for h in hits]
    assert "心血管内科" in names, names
    print(f"       命中 -> {names[:3]}")


@check("LLM 工厂：在线/离线两种模式构建（不实际调用）")
def _():
    from core.llm import get_chat_model
    import config
    old_provider, old_key = config.LLM_PROVIDER, config.ONLINE_API_KEY
    try:
        # 未配置 Key 时应给出清晰中文错误
        config.LLM_PROVIDER, config.ONLINE_API_KEY = "online", ""
        try:
            get_chat_model()
            raise AssertionError("未配置 Key 应抛出 ValueError")
        except ValueError:
            pass
        config.ONLINE_API_KEY = "sk-test"
        m2 = get_chat_model()
        assert type(m2).__name__ == "ChatOpenAI"
        config.LLM_PROVIDER = "ollama"
        m1 = get_chat_model()
        assert type(m1).__name__ == "ChatOllama"
    finally:
        config.LLM_PROVIDER, config.ONLINE_API_KEY = old_provider, old_key


@check("结构化输出降级解析 extract_json")
def _():
    from core.llm import extract_json
    assert extract_json('好的，结果如下：\n```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('前缀文字 {"b": [1,2]} 后缀') == {"b": [1, 2]}
    assert extract_json("没有json") is None


@check("链构建：LCEL 组装可执行（FakeListChatModel 模拟 LLM）")
def _():
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from agents.consultant import ConsultantChain
    from agents.interviewer import InterviewChain
    from agents.record_writer import RecordWriterChain
    from agents.report_reader import ReportReaderChain
    from agents.twin_analyst import TwinAnalystChain
    from agents.care_matcher import CareMatcherChain, CareRecommendation

    fake = FakeListChatModel(responses=["好的，这是测试回复。"] * 20)

    out = "".join(ConsultantChain(fake).stream_answer("我最近头晕", []))
    assert "测试回复" in out

    out = "".join(InterviewChain(fake).stream_reply([], "开始问诊"))
    assert "测试回复" in out

    assert "测试回复" in RecordWriterChain(fake).generate([{"role": "user", "content": "头疼"}])
    assert "测试回复" in ReportReaderChain(fake).analyze("WBC 11.2", "x.txt")
    assert "测试回复" in TwinAnalystChain(fake).assess()

    # 结构化输出：FakeList 不支持工具调用 → 走 JSON 降级路径
    fake_json = FakeListChatModel(responses=['{"urgency": "soon", "recommended_departments": [{"department": "心血管内科", "reason": "血压升高"}], "red_flags": ["胸痛"], "preparation_checklist": ["带既往报告"], "questions_to_ask": ["需要做动态血压吗"], "general_advice": "低盐饮食"}'])
    res = CareMatcherChain(fake_json).match("血压150/95 心悸")
    assert res["result"] is not None and res["result"].urgency == "soon"
    assert res["result"].recommended_departments[0].department == "心血管内科"


print("\n" + "=" * 50)
if FAILED:
    print(f"✗ {len(FAILED)} 项失败：")
    for name, err in FAILED:
        print(f"  - {name}: {err}")
    sys.exit(1)
print("✓ 全部冒烟测试通过")
