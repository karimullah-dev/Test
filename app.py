import re
from flask import Flask, request, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Hidden backend target — never exposed to the client
_TARGET_ENDPOINT = "https://dbcenter.uk/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": _TARGET_ENDPOINT,
}

VALID_QUERY_RE = re.compile(r"^(?:[1-9]\d{9}|\d{11}|\d{13})$")

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Terminal</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap');

    body {
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
      background-color: #121214;
      color: #E5E5EA;
    }
    .mono {
      font-family: "SF Mono", "JetBrains Mono", Menlo, Monaco, Consolas, monospace;
    }
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: transparent;
    }
    ::-webkit-scrollbar-thumb {
      background: #2C2C2E;
      border-radius: 3px;
    }
  </style>
</head>
<body class="min-h-screen flex flex-col items-center justify-center p-4 sm:p-8">

  <div class="w-full max-w-2xl space-y-3">

    <!-- Flat Matte Search Bar -->
    <form id="searchForm" novalidate>
      <div id="inputContainer" class="flex items-center bg-[#1C1C1E] border border-[#2C2C2E] focus-within:border-[#48484A] rounded-xl px-3.5 py-2 transition-colors">
        <svg class="w-4 h-4 text-[#8E8E93] mr-3 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 103.5 10.5a7.5 7.5 0 0013.15 6.15z" />
        </svg>

        <input
          id="queryInput"
          type="text"
          inputmode="numeric"
          placeholder="3001234567 or CNIC without dashes"
          autocomplete="off"
          maxlength="13"
          class="w-full bg-transparent text-[#F2F2F7] placeholder-[#636366] text-sm sm:text-base focus:outline-none mono"
        />

        <button
          id="searchBtn"
          type="submit"
          class="ml-3 px-4 py-1.5 rounded-lg bg-[#2C2C2E] hover:bg-[#3A3A3C] text-[#F2F2F7] font-medium text-xs sm:text-sm transition-colors shrink-0"
        >
          Search
        </button>
      </div>

      <p id="errorText" class="hidden text-xs text-[#FF453A] mt-1.5 px-1 mono"></p>
    </form>

    <!-- Flat Matte Terminal Window -->
    <div class="rounded-xl overflow-hidden bg-[#1C1C1E] border border-[#2C2C2E]">
      
      <div class="flex items-center justify-between px-4 py-2.5 bg-[#242426] border-b border-[#2C2C2E] select-none">
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-[#FF453A]"></span>
          <span class="w-3 h-3 rounded-full bg-[#FFD60A]"></span>
          <span class="w-3 h-3 rounded-full bg-[#32D74B]"></span>
        </div>

        <button
          id="copyBtn"
          type="button"
          onclick="copyTerminalText()"
          class="px-2.5 py-1 rounded-md bg-[#2C2C2E] hover:bg-[#3A3A3C] text-xs text-[#EBEBF5] transition-colors mono"
        >
          Copy
        </button>
      </div>

      <div class="p-5 min-h-[320px] max-h-[480px] overflow-y-auto mono text-xs sm:text-sm leading-relaxed">
        <pre id="terminalOutput" class="whitespace-pre-wrap break-words text-[#D1D1D6]"></pre>
      </div>

    </div>

  </div>

  <script>
    const searchForm = document.getElementById("searchForm");
    const queryInput = document.getElementById("queryInput");
    const terminalOutput = document.getElementById("terminalOutput");
    const searchBtn = document.getElementById("searchBtn");
    const errorText = document.getElementById("errorText");
    const inputContainer = document.getElementById("inputContainer");

    queryInput.addEventListener("input", () => {
      queryInput.value = queryInput.value.replace(/\\D/g, "");
      errorText.classList.add("hidden");
      inputContainer.classList.remove("border-[#FF453A]");
    });

    function validateQuery(val) {
      if (!val) {
        return "Input is required.";
      }
      if (val.length === 10) {
        if (val.startsWith("0")) {
          return "10-digit phone number cannot start with 0.";
        }
        return null;
      }
      if (val.length === 11 || val.length === 13) {
        return null;
      }
      return "Enter a 10-digit phone number (without 0) or CNIC without dashes (00000000000).";
    }

    searchForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const query = queryInput.value.trim();
      const validationError = validateQuery(query);

      if (validationError) {
        errorText.textContent = validationError;
        errorText.classList.remove("hidden");
        inputContainer.classList.add("border-[#FF453A]");
        return;
      }

      searchBtn.disabled = true;
      searchBtn.textContent = "...";
      terminalOutput.textContent = "Loading...";

      try {
        const res = await fetch("/api/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ q: query })
        });
        const data = await res.json();
        terminalOutput.textContent = data.output || "No records found.";
      } catch (err) {
        terminalOutput.textContent = "Request failed.";
      } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = "Search";
      }
    });

    async function copyTerminalText() {
      const copyBtn = document.getElementById("copyBtn");
      const text = terminalOutput.innerText.trim();
      if (!text) return;
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied";
      setTimeout(() => (copyBtn.textContent = "Copy"), 1500);
    }
  </script>
</body>
</html>
"""

def perform_search(query: str) -> str:
    output_lines = []
    with requests.Session() as s:
        s.headers.update(HEADERS)

        get_resp = s.get(_TARGET_ENDPOINT, timeout=30)
        get_resp.raise_for_status()

        soup = BeautifulSoup(get_resp.text, "html.parser")
        csrf_input = soup.find("input", {"name": "csrf"})
        if not csrf_input or not csrf_input.get("value"):
            return "Unable to initialize session."

        token = csrf_input["value"]

        post_resp = s.post(_TARGET_ENDPOINT, data={"q": query, "csrf": token}, timeout=30)
        post_resp.raise_for_status()

        result_soup = BeautifulSoup(post_resp.text, "html.parser")

        for junk in result_soup.select("div.text-justify, p.alert, script, style, footer, nav, form"):
            junk.decompose()

        # Check raw card text to see if records are redacted with asterisks or require sharing
        full_page_text = result_soup.get_text()
        if "***************" in full_page_text or "Share to whatsapp" in full_page_text or "Your search query is private" in full_page_text:
            return "This number seems to be newly registered and not available in my database."

        status_p = result_soup.select_one("p.text-muted.text-center.mb-2.font-size-10.show-after-5")
        if status_p:
            direct_text = "".join(status_p.find_all(string=True, recursive=False)).strip()
            if direct_text:
                output_lines.append(f"Status: {direct_text}\n")

        cards = result_soup.select("div.card")
        if not cards:
            return "This number seems to be newly registered and not available in my database."

        for idx, card in enumerate(cards, 1):
            for nested_card in card.select("div.card"):
                nested_card.extract()

            lines = [line.strip() for line in card.stripped_strings if line.strip()]
            if not lines:
                continue

            output_lines.append(f"--- Record {idx} ---")
            i = 0
            while i < len(lines):
                if lines[i].upper() in {"FULL NAME", "PHONE #", "CNIC #", "ADDRESS"} and i + 1 < len(lines):
                    output_lines.append(f"{lines[i].title():<10}: {lines[i+1]}")
                    i += 2
                else:
                    output_lines.append(lines[i])
                    i += 1
            output_lines.append("")

    result_str = "\n".join(output_lines).strip()
    if not result_str or "***************" in result_str:
        return "This number seems to be newly registered and not available in my database."

    return result_str

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json(silent=True) or {}
    query = str(data.get("q", "")).strip()

    if not VALID_QUERY_RE.match(query):
        return jsonify({
            "output": "Invalid format. Enter a 10-digit number (without leading 0) or CNIC without dashes."
        }), 400

    try:
        result = perform_search(query)
        return jsonify({"output": result})
    except Exception:
        return jsonify({"output": "Service unavailable."}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)