"""TopicScout 全流程 E2E 测试 — 从创建主题到生成总结报告。

流程：
  创建主题 → AI 对话 → 确认主题 → 触发爬取 → 等待完成 → AI 总结 → 查看结果
"""

import sys
import time
import json
import httpx

# Fix Windows GBK encoding for emoji in output
sys.stdout.reconfigure(encoding='utf-8')

API = "http://localhost:8000"
TOPIC_KEYWORD = "2026年最值得关注的开源AI项目"
TIMEOUT = 120  # LLM 调用可能较慢


def api(method: str, path: str, **kwargs) -> httpx.Response:
    client = httpx.Client(timeout=TIMEOUT)
    return client.request(method, f"{API}{path}", **kwargs)


def step(n: int, desc: str):
    print(f"\n{'='*60}")
    print(f"  步骤 {n}: {desc}")
    print(f"{'='*60}")


def main():
    results = {}

    # === Step 1: 创建主题 ===
    step(1, "创建主题")
    resp = api("POST", "/api/topics", json={"keyword": TOPIC_KEYWORD})
    assert resp.status_code == 201, f"创建主题失败: {resp.status_code}"
    data = resp.json()
    topic_id = data["topic"]["id"]
    ai_reply = data["ai_reply"]
    is_ready = data["is_ready"]
    print(f"  topic_id: {topic_id}")
    print(f"  status: {data['topic']['status']}")
    print(f"  AI 回复: {ai_reply[:200]}...")
    print(f"  is_ready: {is_ready}")
    results["create_topic"] = {"topic_id": topic_id, "ai_reply": ai_reply[:100], "is_ready": is_ready}

    # === Step 2: AI 对话 (1-3 轮) ===
    step(2, "AI 对话 — 追问细化")
    messages = [
        "我主要关注开源项目，特别是编程和AI方向的",
        "时间范围是2026年上半年，重点关注有实际生产力的项目，不是demo",
    ]
    for i, msg in enumerate(messages):
        print(f"\n  用户: {msg}")
        resp = api("POST", f"/api/topics/{topic_id}/chat", json={"content": msg})
        assert resp.status_code == 200, f"对话失败: {resp.status_code} {resp.text}"
        data = resp.json()
        print(f"  AI: {data['reply'][:150]}...")
        print(f"  is_ready: {data['is_ready']}, auto_confirmed: {data['auto_confirmed']}")
        if data["is_ready"]:
            print(f"  标题: {data['title']}")
            print(f"  描述: {data['description']}")
            break
        time.sleep(1)  # 避免频率限制

    # === Step 3: 确认主题 ===
    step(3, "确认主题")
    # 获取最新的 AI 回复中的标题描述
    resp = api("POST", f"/api/topics/{topic_id}/confirm", json={})
    assert resp.status_code == 200, f"确认失败: {resp.status_code}"
    data = resp.json()
    print(f"  标题: {data['title']}")
    print(f"  描述: {data['description']}")
    results["confirm"] = {"title": data["title"], "description": data["description"]}

    # === Step 4: 触发爬取 ===
    step(4, "触发爬取 (web + bilibili)")
    resp = api("POST", f"/api/topics/{topic_id}/crawl", json={
        "platforms": ["web", "bilibili"],
        "urls": [],
    })
    assert resp.status_code == 202, f"触发爬取失败: {resp.status_code}"
    data = resp.json()
    task_id = data["task_id"]
    version = data["version"]
    print(f"  task_id: {task_id}")
    print(f"  version: {version}")
    results["crawl_task"] = {"task_id": task_id, "version": version}

    # === Step 5: 等待爬取完成 ===
    step(5, "等待爬取完成 (轮询)")
    start = time.time()
    while True:
        resp = api("GET", f"/api/tasks/{task_id}")
        task = resp.json()
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] status={task['status']}, progress={task['progress']}%, detail={task['detail']}")
        if task["status"] in ("done", "error"):
            break
        if elapsed > 600:
            print("  超时! 爬取超过10分钟")
            break
        time.sleep(5)

    if task["status"] == "error":
        print(f"  爬取出错: {task['error_msg']}")
        results["crawl"] = {"status": "error", "error": task["error_msg"]}
    else:
        print(f"  爬取完成!")
        # 查看来源
        resp = api("GET", f"/api/topics/{topic_id}/sources")
        sources = resp.json()
        print(f"  来源总数: {sources['total']}")
        for s in sources["sources"][:5]:
            print(f"    - [{s['platform']}] {s['title'][:60]}")
        results["crawl"] = {"status": "done", "total_sources": sources["total"]}

    # === Step 6: AI 总结 ===
    step(6, "AI 全局总结")
    resp = api("POST", f"/api/topics/{topic_id}/summarize")
    assert resp.status_code == 200, f"触发总结失败: {resp.status_code}"
    summarize_task_id = resp.json()["task_id"]
    print(f"  summarize task_id: {summarize_task_id}")

    # 等待总结完成
    start = time.time()
    while True:
        resp = api("GET", f"/api/tasks/{summarize_task_id}")
        task = resp.json()
        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] status={task['status']}, progress={task['progress']}%")
        if task["status"] in ("done", "error"):
            break
        if elapsed > 120:
            print("  超时!")
            break
        time.sleep(3)

    # === Step 7: 获取总结结果 ===
    step(7, "查看总结结果")
    resp = api("GET", f"/api/topics/{topic_id}/summary")
    summary = resp.json()
    if summary:
        print(f"  总结内容 ({len(summary['content'])}字):")
        print(f"    {summary['content'][:500]}...")
        print(f"  关键洞察 ({len(summary['key_insights'])}条):")
        for insight in summary.get("key_insights", []):
            print(f"    - {insight}")
        print(f"  可靠度: {summary.get('reliability', 'N/A')}")
        results["summary"] = {
            "content_length": len(summary["content"]),
            "insights_count": len(summary.get("key_insights", [])),
            "reliability": summary.get("reliability", ""),
        }
    else:
        print("  无总结数据")
        results["summary"] = None

    # === Step 8: 查看最终主题状态 ===
    step(8, "验证最终状态")
    resp = api("GET", f"/api/topics/{topic_id}")
    topic = resp.json()
    print(f"  最终 status: {topic['status']}")
    print(f"  标题: {topic['title']}")
    print(f"  分类: {topic['categories']}")
    results["final"] = {"status": topic["status"], "categories": topic["categories"]}

    # === 生成报告 ===
    print(f"\n{'='*60}")
    print(f"  全流程测试报告")
    print(f"{'='*60}")
    print(f"  关键词: {TOPIC_KEYWORD}")
    print(f"  topic_id: {topic_id}")
    print(f"  主题确认: {results.get('confirm', {}).get('title', 'N/A')}")
    crawl_result = results.get("crawl", {})
    print(f"  爬取状态: {crawl_result.get('status', 'N/A')}")
    print(f"  来源数量: {crawl_result.get('total_sources', 0)}")
    summary_result = results.get("summary", {})
    if summary_result:
        print(f"  总结字数: {summary_result.get('content_length', 0)}")
        print(f"  关键洞察: {summary_result.get('insights_count', 0)} 条")
        print(f"  可靠度评估: {summary_result.get('reliability', 'N/A')}")
    print(f"  最终状态: {results.get('final', {}).get('status', 'N/A')}")
    print(f"  自动归类: {results.get('final', {}).get('categories', [])}")

    # 保存报告
    report_path = "tests/e2e/full_flow_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  报告已保存: {report_path}")
    print(f"{'='*60}")

    # 返回是否成功
    success = (
        crawl_result.get("status") == "done"
        and crawl_result.get("total_sources", 0) > 0
    )
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
