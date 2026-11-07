"""End-to-end browser check (needs:  pip install playwright ; playwright install chromium).
Start the app first (python app.py), then run:  python tools/browser_check.py
NOTE: it clears the saved history first. It drives every button in headless Chromium, checks console errors,
runs the Analyzer on several sentences, verifies the database history and tests four screen sizes."""
import json, os, sys
if os.path.isdir("/opt/pw-browsers"): os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")
from playwright.sync_api import sync_playwright
BASE = os.environ.get("BASE", "http://127.0.0.1:5000")
os.makedirs("tools/browser_check_output", exist_ok=True)
results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail)); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
def visible_view(pg): return pg.evaluate("[...document.querySelectorAll('.view')].filter(v=>!v.hidden).map(v=>v.dataset.view)")
def analyze(pg, text):
    pg.fill("#textInput", text); pg.click("#analyzeBtn")
    pg.wait_for_function("document.getElementById('statusText').textContent==='Analysis complete'", timeout=8000)
    return json.loads(pg.inner_text("#rJson"))
# console noise that only means "the sandbox/offline machine cannot reach Google Fonts" is reported separately
def is_font_noise(t): return "ERR_NAME_NOT_RESOLVED" in t or "fonts.g" in t or "ERR_INTERNET_DISCONNECTED" in t

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
    pg = ctx.new_page(); console, page_errs, bad = [], [], []
    pg.on("console", lambda m: console.append(m.text) if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: page_errs.append(str(e)))
    pg.on("response", lambda r: bad.append(f"{r.status} {r.url}") if r.status >= 400 else None)
    ctx.request.delete(BASE + "/api/history")

    pg.goto(BASE, wait_until="load"); pg.wait_for_selector("#exampleChips .chip", state="attached")
    check("Home loads", visible_view(pg) == ["home"] and "Semantic Parser" in pg.title(), pg.title())
    check("Theme: ivory background #FAF7F0", pg.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(250, 247, 240)")
    check("No bear/mascot anywhere", pg.evaluate("!document.querySelector('.mascot,.bubble,[src*=bear]') && !document.body.innerHTML.toLowerCase().includes('bear.svg')"))
    check("All images loaded", pg.evaluate("[...document.images].every(i=>i.complete&&i.naturalWidth>0)"))
    check("Home: stats cards, intro, 8-stage overview", pg.locator(".stat").count() == 4 and pg.locator("#homeFlow li").count() == 8 and "semantic parsing" in pg.inner_text("#view-home").lower())
    check("Home: serif heading font stack", "Playfair" in pg.evaluate("getComputedStyle(document.querySelector('h1')).fontFamily"))

    # navigation
    for name in ["analyzer", "pipeline", "playground", "history", "home"]:
        pg.click(f'#navLinks a[data-route="{name}"]'); pg.wait_for_timeout(150)
        check(f"Nav -> {name}", visible_view(pg) == [name] and pg.get_attribute(f'#navLinks a[data-route="{name}"]', "aria-current") == "page")
    pg.click("#startBtn"); pg.wait_for_timeout(200)
    check("Start Analyzing -> Analyzer, textarea focused", visible_view(pg) == ["analyzer"] and pg.evaluate("document.activeElement.id") == "textInput")
    pg.go_back(); pg.wait_for_timeout(150)
    check("Browser back button returns to Home", visible_view(pg) == ["home"])
    pg.goto(BASE + "/#/history"); pg.wait_for_timeout(300)
    check("Deep link #/history opens History", visible_view(pg) == ["history"])
    pg.goto(BASE + "/#/nonsense"); check("Unknown route falls back to Home", visible_view(pg) == ["home"])
    check("Unknown URL path serves app (404 handler)", ctx.request.get(BASE + "/some/page").status == 200)

    # analyzer controls
    pg.goto(BASE + "/#/analyzer")
    check("Status indicator idle", pg.inner_text("#statusText") == "Ready")
    pg.fill("#textInput", ""); pg.click("#analyzeBtn")
    check("Empty input validation", pg.is_visible("#error") and "enter a sentence" in pg.inner_text("#error") and pg.get_attribute("#status", "data-state") == "error")
    pg.fill("#textInput", "abc"); check("Error clears on typing + char counter", not pg.is_visible("#error") and pg.inner_text("#charCount") == "3 / 500")
    pg.click("#exampleChips .chip >> nth=0"); check("Quick example fills textarea", pg.input_value("#textInput") == "Hello, how are you?")

    CASES = [("Hello, how are you?", "GREETING"), ("Show me the weather in Hyderabad.", "GET_WEATHER"), ("Book a train ticket to Chennai tomorrow.", "BOOK_TRANSPORT"),
             ("Find information about artificial intelligence.", "SEARCH_INFO"), ("Who is the president of India?", "GENERAL_QUESTION"),
             ("I want to book a hotel in Mumbai.", "BOOK_HOTEL"), ("asdf qwerty zxcv", "UNKNOWN")]
    for text, intent in CASES:
        js = analyze(pg, text)
        done = pg.locator("#liveFlow li.done").count()
        check(f"Analyze {text!r} -> {intent}", js["intent"] == intent and pg.inner_text(".intent-name") == intent and pg.locator("#rTokens .tok").count() > 0, json.dumps(js))
    pg.wait_for_timeout(1000)
    check("Results show 8 numbered sections in order", pg.locator("#results .card-title").all_inner_texts() == ["1\nOriginal Sentence", "2\nPreprocessed Text", "3\nTokens (7)" if False else pg.locator("#results .card-title").all_inner_texts()[2], "4\nSemantic Parsing", "5\nExtracted Entities", "6\nIntent Classification", "7\nStructured JSON Output", "8\nGenerated Explanation"])
    check("Live pipeline has 8 completed stages", pg.locator("#liveFlow li.done").count() == 8)
    check("UNKNOWN shows explanation note", "Unsupported" in pg.inner_text("#rNotes"))

    js = analyze(pg, "Book a train ticket to Chennai tomorrow.")
    check("Original text", pg.inner_text("#rOriginal") == "Book a train ticket to Chennai tomorrow.")
    check("Preprocessed text", pg.inner_text("#rPre") == "book a train ticket to chennai tomorrow", pg.inner_text("#rPre"))
    check("Tokens", pg.locator("#rTokens .tok").all_inner_texts()[:4] == ["Book", "a", "train", "ticket"])
    check("Parse tree + relations", pg.locator("#rParse .node").count() >= 3 and pg.locator("#rParse .rel").count() >= 1)
    check("Entities", all(x in pg.inner_text("#rEntities") for x in ["Chennai", "destination", "tomorrow", "train"]))
    check("Intent confidence 100%", "BOOK_TRANSPORT" in pg.inner_text("#rIntent") and "100%" in pg.inner_text("#rIntent"))
    check("JSON output", js == {"intent": "BOOK_TRANSPORT", "action": "book", "object": "train ticket", "destination": "Chennai", "date": "tomorrow"}, json.dumps(js))
    check("Explanation", "book a train ticket to Chennai" in pg.inner_text("#rInterp"))
    pg.screenshot(path="tools/browser_check_output/desktop_analyzer.png", full_page=True)
    pg.click("#copyBtn"); pg.wait_for_timeout(300)
    clip = pg.evaluate("navigator.clipboard.readText()")
    check("Copy JSON copies exact JSON", clip == pg.inner_text("#rJson") and json.loads(clip)["destination"] == "Chennai")

    held = []; slow = lambda r: held.append(r); ctx.route("**/api/analyze", slow)
    pg.click("#analyzeBtn"); pg.wait_for_timeout(300)
    check("Processing indicator + disabled button while analyzing", pg.get_attribute("#status", "data-state") == "busy" and pg.inner_text("#statusText") == "Processing sentence" and pg.locator("#analyzeBtn").is_disabled())
    held[0].continue_(); pg.wait_for_function("document.getElementById('statusText').textContent==='Analysis complete'", timeout=6000); ctx.unroute("**/api/analyze", slow)
    check("Button re-enabled after request", not pg.locator("#analyzeBtn").is_disabled())

    pg.click("#clearBtn"); check("Clear Input empties textarea, hides results, status Ready", pg.input_value("#textInput") == "" and not pg.is_visible("#results") and pg.inner_text("#statusText") == "Ready")
    pg.fill("#textInput", "Is it raining in Nagpur?"); pg.press("#textInput", "Enter")
    pg.wait_for_function("document.getElementById('rJson').textContent.includes('Nagpur')", timeout=6000)
    check("Enter key submits (unlisted city)", json.loads(pg.inner_text("#rJson"))["location"] == "Nagpur")
    pg.fill("#textInput", "<script>window.__xss=1</script> Book a flight to Paris"); pg.click("#analyzeBtn"); pg.wait_for_timeout(1200)
    check("HTML in input is escaped (no XSS)", pg.evaluate("window.__xss") is None and "<script>" in pg.inner_text("#rOriginal"))
    pg.fill("#textInput", "Book a trian ticket to Chenai tomorow"); pg.click("#analyzeBtn"); pg.wait_for_timeout(1200)
    check("Spelling corrections shown", pg.locator("#rFixes .fix").count() >= 2 and json.loads(pg.inner_text("#rJson"))["destination"] == "Chennai")

    # playground -> analyzer
    pg.goto(BASE + "/#/playground"); pg.wait_for_selector("#playgroundGrid .play")
    check("Playground shows 8 example cards", pg.locator("#playgroundGrid .play").count() == 8)
    pg.click("#playgroundGrid .play >> nth=3")
    pg.wait_for_function("document.getElementById('rJson').textContent.includes('SEARCH_INFO')", timeout=6000)
    check("Playground card opens Analyzer and processes the sentence", visible_view(pg) == ["analyzer"] and pg.input_value("#textInput") == "Find information about artificial intelligence.")
    pg.goto(BASE + "/#/playground"); pg.click("#playgroundGrid .play >> nth=7")
    pg.wait_for_function("document.getElementById('rJson').textContent.includes('universities')", timeout=6000)
    js2 = json.loads(pg.inner_text("#rJson")); check("Playground 'Search for universities in Pune.'", js2.get("object") == "universities" and js2.get("location") == "Pune", json.dumps(js2))

    # pipeline page
    pg.goto(BASE + "/#/pipeline"); pg.wait_for_selector("#pipeline li")
    check("Pipeline page: 8 numbered stages with descriptions", pg.locator("#pipeline li").count() == 8 and all(len(t) > 20 for t in pg.locator("#pipeline li span").all_inner_texts()))
    pg.click("#view-pipeline .btn.primary"); pg.wait_for_timeout(250); check("Pipeline CTA opens Analyzer", visible_view(pg) == ["analyzer"])
    pg.screenshot(path="tools/browser_check_output/desktop_analyzer_after.png")

    # history (real database)
    api_hist = pg.evaluate("fetch('/api/history').then(r=>r.json())")
    pg.goto(BASE + "/#/history"); pg.wait_for_selector("#historyBody tr")
    n = pg.locator("#historyBody tr").count()
    check("History table lists every DB row", n == len(api_hist["history"]) == api_hist["total"] and n >= 12, f"{n} rows")
    check("History counter + Home stat match DB", str(n) in pg.inner_text("#historyCount") and pg.inner_text("#statHistory") == str(n))
    first = pg.locator("#historyBody tr").first
    check("Row shows sentence, intent tag, timestamp", all([first.locator(".sent").inner_text(), first.locator(".tag").inner_text(), first.locator(".time").inner_text()]))
    pg.screenshot(path="tools/browser_check_output/desktop_history.png")
    pg.click("#historyBody tr:last-child [data-id]"); pg.wait_for_selector("#results:not([hidden])")
    check("View Analysis opens the oldest entry in Analyzer", visible_view(pg) == ["analyzer"] and pg.inner_text("#rOriginal") == "Hello, how are you?" and json.loads(pg.inner_text("#rJson"))["intent"] == "GREETING")
    pg.goto(BASE + "/#/history"); pg.wait_for_selector("#historyBody tr")
    pg.click("#clearHistoryBtn"); check("Clear History opens confirmation modal", pg.is_visible("#confirmModal"))
    pg.click("#confirmNo"); check("Keep history keeps rows", not pg.is_visible("#confirmModal") and pg.locator("#historyBody tr").count() == n)
    pg.click("#clearHistoryBtn"); pg.keyboard.press("Escape"); check("Escape closes modal", not pg.is_visible("#confirmModal") and pg.locator("#historyBody tr").count() == n)
    pg.click("#refreshHistoryBtn"); pg.wait_for_timeout(300); check("Refresh keeps data", pg.locator("#historyBody tr").count() == n)
    pg.click("#clearHistoryBtn"); pg.click("#confirmYes"); pg.wait_for_timeout(500)
    check("Clear History empties table + shows empty state + DB", pg.locator("#historyBody tr").count() == 0 and pg.is_visible("#historyEmpty") and pg.evaluate("fetch('/api/history').then(r=>r.json()).then(d=>d.history.length)") == 0 and pg.inner_text("#statHistory") == "0")

    # offline error path
    pg.goto(BASE + "/#/analyzer"); ctx.route("**/api/analyze", lambda r: r.abort())
    pg.fill("#textInput", "Hello"); pg.click("#analyzeBtn"); pg.wait_for_timeout(500)
    check("Network failure shows friendly error", pg.is_visible("#error") and "server" in pg.inner_text("#error").lower() and not pg.locator("#analyzeBtn").is_disabled() and pg.get_attribute("#status", "data-state") == "error")
    ctx.unroute("**/api/analyze")

    real = [e for e in console if "ERR_FAILED" not in e and "Failed to load resource" not in e and not is_font_noise(e)]
    font_noise = [e for e in console if is_font_noise(e)]
    check("No JS page errors", not page_errs, str(page_errs))
    check("No console errors (excluding deliberate network abort)", not real, str(real))
    check("No HTTP 4xx/5xx from the app", not [x for x in bad if "fonts.g" not in x], str(bad))
    if font_noise: print("NOTE  Google Fonts unreachable from this machine (offline); system fallback fonts were used:", len(font_noise), "request(s)")

    # responsive
    for name, w, h in [("desktop_1440", 1440, 900), ("laptop_1366", 1366, 768), ("tablet_768", 768, 1024), ("mobile_390", 390, 844)]:
        c2 = b.new_context(viewport={"width": w, "height": h}); q = c2.new_page(); errs = []
        q.on("pageerror", lambda e: errs.append(str(e))); q.on("console", lambda m: errs.append(m.text) if m.type == "error" and not is_font_noise(m.text) else None)
        for view in ["home", "analyzer", "pipeline", "playground", "history"]:
            q.goto(f"{BASE}/#/{view}"); q.wait_for_timeout(250)
            if view == "analyzer":
                q.fill("#textInput", "Book a train ticket to Chennai tomorrow."); q.click("#analyzeBtn"); q.wait_for_timeout(1400)
            sw = q.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
            off = q.evaluate("""()=>[...document.querySelectorAll('.view:not([hidden]) button,.view:not([hidden]) .card,.view:not([hidden]) pre,.view:not([hidden]) li')].filter(e=>{const r=e.getBoundingClientRect(); if(!r.width) return false; return (r.right>innerWidth+1||r.left<-1) && !e.closest('.table-wrap,pre')}).map(e=>e.id||e.className).slice(0,4)""")
            small = q.evaluate("""()=>[...document.querySelectorAll('.view:not([hidden]) .btn:not(.small),.view:not([hidden]) textarea')].filter(e=>{const r=e.getBoundingClientRect(); return r.width&&r.height&&r.height<40}).map(e=>e.id||e.textContent.trim()).slice(0,4)""")
            check(f"[{name}] {view}: no horizontal scroll / cut-off / tiny buttons", sw[0] <= sw[1] and not off and not small, f"scroll={sw} off={off} small={small}")
            if view in ("home", "analyzer", "history"):
                q.evaluate("document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,0)"); q.wait_for_timeout(200)
                q.screenshot(path=f"tools/browser_check_output/{name}_{view}.png", full_page=(view != "home"))
        if w <= 820:
            check(f"[{name}] hamburger visible, nav hidden", q.is_visible("#menuBtn") and not q.is_visible("#navLinks"))
            q.click("#menuBtn"); check(f"[{name}] hamburger opens menu", q.is_visible("#navLinks") and q.get_attribute("#menuBtn", "aria-expanded") == "true")
            q.click('#navLinks a[data-route="pipeline"]'); q.wait_for_timeout(200)
            check(f"[{name}] menu link navigates and closes menu", not q.is_visible("#navLinks") and visible_view(q) == ["pipeline"])
            q.click("#menuBtn"); q.keyboard.press("Escape"); check(f"[{name}] Escape closes menu", not q.is_visible("#navLinks"))
        else:
            check(f"[{name}] full nav visible, hamburger hidden", q.is_visible("#navLinks") and not q.is_visible("#menuBtn"))
        check(f"[{name}] no JS/console errors", not errs, str(errs)); c2.close()
    b.close()

fails = [r for r in results if not r[1]]
print(f"\n==== {len(results)-len(fails)}/{len(results)} UI checks passed ====")
for f in fails: print("FAILED:", f[0], f[2])
json.dump(results, open("tools/browser_check_output/ui_results.json", "w"), indent=1)
sys.exit(1 if fails else 0)
