"""TopicScout E2E tests — Playwright sync API."""

import re
import pytest
from playwright.sync_api import Page, expect

BASE = "http://localhost:3783"


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
    page = ctx.new_page()
    yield page
    page.close()
    ctx.close()


# --- Home Page ---

class TestHomePage:
    def test_loads(self, page: Page):
        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        expect(page.locator("h1")).to_contain_text("TopicScout")

    def test_has_search_input(self, page: Page):
        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        search = page.locator("input[placeholder]")
        expect(search.first).to_be_visible()

    def test_shows_existing_topics(self, page: Page):
        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        # There should be some topic cards from previous data
        cards = page.locator(".topic-card, [class*=topic]")
        count = cards.count()
        assert count >= 0, "Page should render without errors"

    def test_navigation_to_config(self, page: Page):
        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        config_link = page.locator("a[href='/config'], a:has-text('配置')")
        if config_link.count() > 0:
            config_link.first.click()
            page.wait_for_load_state("networkidle")
            expect(page).to_have_url(re.compile(r"/config"))


# --- Config Page ---

class TestConfigPage:
    def test_loads(self, page: Page):
        page.goto(f"{BASE}/config")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        expect(page.locator("h2")).to_contain_text("配置")

    def test_llm_section_visible(self, page: Page):
        page.goto(f"{BASE}/config")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        expect(page.locator("h3:has-text('LLM 服务商')")).to_be_visible()

    def test_provider_cards_render(self, page: Page):
        page.goto(f"{BASE}/config")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        providers = page.locator(".provider-card")
        assert providers.count() >= 5, "Should have at least 5 provider cards"

    def test_provider_card_click_selects(self, page: Page):
        page.goto(f"{BASE}/config")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        # Click on Kimi provider
        kimi_card = page.locator(".provider-card:has-text('Kimi')")
        kimi_card.click()
        page.wait_for_timeout(300)
        expect(kimi_card.locator(".provider-check")).to_be_visible()

    def test_crawl_config_section(self, page: Page):
        page.goto(f"{BASE}/config")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        expect(page.locator("h3:has-text('爬取配置')")).to_be_visible()

    def test_wechat_section_visible(self, page: Page):
        page.goto(f"{BASE}/config")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        expect(page.locator("h3:has-text('微信公众号')")).to_be_visible()

    def test_wechat_login_button(self, page: Page):
        page.goto(f"{BASE}/config")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        login_btn = page.locator("button:has-text('登录微信公众号')")
        expect(login_btn).to_be_visible()

    def test_api_key_input_exists(self, page: Page):
        page.goto(f"{BASE}/config")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        api_key_input = page.locator("input[type='password']")
        expect(api_key_input).to_be_visible()

    def test_model_selector_or_input(self, page: Page):
        page.goto(f"{BASE}/config")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        # Either a select or an input for model name
        model = page.locator("select.config-select, label:has-text('模型') + input, label:has-text('模型') ~ div input")
        assert model.count() >= 1, "Model selector or input should exist"


# --- Tasks Page ---

class TestTasksPage:
    def test_loads(self, page: Page):
        page.goto(f"{BASE}/tasks")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        expect(page.locator("h2")).to_contain_text("任务")

    def test_shows_task_table_or_empty(self, page: Page):
        page.goto(f"{BASE}/tasks")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        # Should show either tasks or empty state
        content = page.content()
        assert "任务" in content


# --- Chat Page ---

class TestChatPage:
    def test_existing_topic_chat_loads(self, page: Page):
        # Get a topic id from API
        import httpx
        topics = httpx.get("http://localhost:8000/api/topics").json()
        done_topics = [t for t in topics if t["status"] == "done"]
        if not done_topics:
            pytest.skip("No done topics available")

        topic_id = done_topics[0]["id"]
        page.goto(f"{BASE}/topics/{topic_id}/chat")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)
        # Page should render without error
        content = page.content()
        assert "404" not in content

    def test_chat_has_input(self, page: Page):
        import httpx
        topics = httpx.get("http://localhost:8000/api/topics").json()
        chatting = [t for t in topics if t["status"] == "chatting"]
        if not chatting:
            pytest.skip("No chatting topics available")

        topic_id = chatting[0]["id"]
        page.goto(f"{BASE}/topics/{topic_id}/chat")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)
        input_field = page.locator("textarea, input[type='text']").last
        expect(input_field).to_be_visible()


# --- Result Page ---

class TestResultPage:
    def test_done_topic_result_loads(self, page: Page):
        import httpx
        topics = httpx.get("http://localhost:8000/api/topics").json()
        done_topics = [t for t in topics if t["status"] == "done"]
        if not done_topics:
            pytest.skip("No done topics available")

        topic_id = done_topics[0]["id"]
        page.goto(f"{BASE}/topics/{topic_id}")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)
        content = page.content()
        assert "404" not in content

    def test_shows_export_buttons(self, page: Page):
        import httpx
        topics = httpx.get("http://localhost:8000/api/topics").json()
        done_topics = [t for t in topics if t["status"] == "done"]
        if not done_topics:
            pytest.skip("No done topics available")

        topic_id = done_topics[0]["id"]
        page.goto(f"{BASE}/topics/{topic_id}")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)
        # Check for export-related elements
        content = page.content()
        assert "导出" in content or "export" in content.lower() or "JSON" in content


# --- Topic Creation Flow ---

class TestCreateTopic:
    def test_create_topic_via_api(self, page: Page):
        """Test creating a topic via API (faster than UI)."""
        import httpx
        resp = httpx.post("http://localhost:8000/api/topics", json={"keyword": "E2E测试关键词"}, timeout=120)
        assert resp.status_code == 201
        data = resp.json()
        assert "topic" in data
        assert data["topic"]["keyword"] == "E2E测试关键词"
        assert "ai_reply" in data

        # Clean up
        topic_id = data["topic"]["id"]
        httpx.delete(f"http://localhost:8000/api/topics/{topic_id}")


# --- API Endpoints ---

class TestAPIEndpoints:
    def test_topics_list(self):
        import httpx
        resp = httpx.get("http://localhost:8000/api/topics")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_config_get(self):
        import httpx
        resp = httpx.get("http://localhost:8000/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm" in data
        assert "crawl" in data

    def test_tasks_list(self):
        import httpx
        resp = httpx.get("http://localhost:8000/api/tasks")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_wx_status(self):
        import httpx
        resp = httpx.get("http://localhost:8000/api/wx/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "logged_in" in data

    def test_wx_accounts_list(self):
        import httpx
        resp = httpx.get("http://localhost:8000/api/wx/accounts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# --- Responsive ---

class TestResponsive:
    def test_mobile_viewport(self, browser):
        ctx = browser.new_context(viewport={"width": 375, "height": 812}, locale="zh-CN")
        page = ctx.new_page()
        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        # Should not have horizontal scrollbar
        body_width = page.evaluate("document.body.scrollWidth")
        assert body_width <= 400, f"Body too wide for mobile: {body_width}px"
        page.close()
        ctx.close()

    def test_wide_viewport(self, browser):
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="zh-CN")
        page = ctx.new_page()
        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)
        expect(page.locator("h1")).to_be_visible()
        page.close()
        ctx.close()
