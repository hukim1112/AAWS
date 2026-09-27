---
name: dynamic_content_diagnosis
description: Troubleshooting decision tree for 0-count selector matches, dynamic hydration delays, iframes, shadow DOM, lazy loading, and virtual DOM escalation.
---

# 🔍 Dynamic Content Diagnosis & Selector Troubleshooting Playbook

When `verify_selectors` returns **0 items** or extraction yields empty fields, **do not repeatedly guess CSS selectors blindly**. Follow this systematic decision tree to identify the root cause and apply the correct mitigation.

---

## 1. Quick Decision Tree

```
[Selector returns 0 items]
       │
       ├─► 1. Is the element rendered by Client-Side JS?
       │     └─► YES ➔ Add explicit locator wait: `page.wait_for_selector(selector, timeout=10000)`
       │
       ├─► 2. Is the element inside an <iframe>?
       │     └─► YES ➔ Switch context: `page.frame_locator('iframe#id').locator(...)`
       │
       ├─► 3. Is the element encapsulated in a Shadow DOM?
       │     └─► YES ➔ Use Playwright piercing locator: `page.locator('parent-tag >> .child-class')`
       │
       ├─► 4. Is the element lazy-loaded upon scrolling?
       │     └─► YES ➔ Scroll viewport into view before querying
       │
       └─► 5. Does the DOM unmount previous items on scroll (Virtualized DOM)?
             └─► YES ➔ STOP DOM PARSING. Escalate to `api_reverse_engineering.md`
```

---

## 2. Diagnosis & Solutions

### Case 1: Hydration & Rendering Delay
- **Symptom**: The HTML skeleton contains the container, but items are empty or populated only after network requests complete.
- **Solution**:
  ```python
  # Wait for the actual target element rather than relying on arbitrary sleep
  page.wait_for_selector(".product-item", state="attached", timeout=10000)
  ```

### Case 2: Isolated `<iframe>` Context
- **Symptom**: Inspecting the section reveals an `<iframe>` tag (common in payment gateways, embedded search results, blogs).
- **Solution**:
  ```python
  # Locate inside the iframe context
  iframe = page.frame_locator("iframe#search-result-frame")
  items = iframe.locator(".result-item").all_text_contents()
  ```

### Case 3: Shadow DOM Encapsulation
- **Symptom**: Standard `document.querySelector` fails, but the node exists under `#shadow-root (open)`.
- **Solution**:
  Playwright automatically pierces open Shadow DOMs with standard CSS locators. If using BeautifulSoup or raw Selenium, switch to Playwright or query via JS:
  ```python
  # Playwright locators automatically pierce open shadow roots
  element = page.locator("custom-component >> .inner-field")
  ```

### Case 4: Viewport Lazy-Loading (Images / Content)
- **Symptom**: Selectors find containers, but images or text are stored in `data-src` or not loaded until visible.
- **Solution**:
  ```python
  # Scroll incrementally down the page
  page.evaluate("""
      window.scrollBy(0, window.innerHeight);
  """)
  page.wait_for_timeout(1000)
  ```

### Case 5: Virtualized DOM (Virtual Scroll)
- **Symptom**: When scrolling down, DOM nodes above are unmounted/destroyed to conserve browser memory (e.g., only 10 `div`s exist at any moment regardless of 1,000 items).
- **Critical Action**: **Do not attempt to scrape via DOM accumulation buffers.**
- **Escalation**: Switch immediately to `api_reverse_engineering.md` to sniff the pagination/infinite-scroll JSON API.

---

## 3. Checklist
- [ ] If 0 items are returned, check for `iframe` or dynamic loading before changing selectors.
- [ ] If virtualized scrolling is detected, cease DOM extraction and capture network API endpoints directly.
