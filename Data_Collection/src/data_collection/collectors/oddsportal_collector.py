from __future__ import annotations

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from src.data_collection.config.tournaments import TournamentConfig
from src.data_collection.schemas.collection import OddsRecord
from src.data_collection.utils.validation import (
    is_blocked_odds_bookmaker,
    is_plausible_1x2_odds,
)


class OddsPortalCollector:
    BASE_URL = "https://www.oddsportal.com"

    @staticmethod
    def _canonical_h2h_odds_url(href: str, *, base_url: str = BASE_URL) -> str | None:
        """One odds URL per h2h match path; OddsPortal uses varying fragment ids on hub links."""
        if "/football/h2h/" not in href:
            return None
        full = f"{base_url}{href}" if href.startswith("/") else href
        path = urlparse(full).path
        if "/football/h2h/" not in path:
            return None
        return f"{base_url}{path.rstrip('/')}#1X2;2"

    def _dedupe_h2h_odds_urls(self, hrefs: Iterable[str]) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        for href in hrefs:
            canonical = self._canonical_h2h_odds_url(href)
            if canonical and canonical not in seen:
                seen.add(canonical)
                links.append(canonical)
        return links

    def __init__(
        self,
        tournaments: Sequence[TournamentConfig],
        timeout_ms: int = 25000,
        retry_attempts: int = 3,
        max_match_pages: int | None = None,
        odds_workers: int = 2,
        output_file: Path | None = None,
    ) -> None:
        self.tournaments = tuple(tournaments)
        self.timeout_ms = timeout_ms
        self.retry_attempts = retry_attempts
        self.max_match_pages = max_match_pages
        self.odds_workers = max(1, odds_workers)
        self.output_file = output_file
        self._file_lock = threading.Lock() if output_file else None

    def collect_tournament_odds(
        self, sanity_check: bool = False, elo_match_counts: dict[str, int] | None = None
    ) -> list[OddsRecord]:
        if self.output_file:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            with self.output_file.open("w", encoding="utf-8") as f:
                f.write("[]")

        match_tasks: list[tuple[int, TournamentConfig, int, int, str]] = []
        storage_state: dict | None = None
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)

            for tournament in self.tournaments:
                self._navigate_with_retry(page, tournament.oddsportal_results_url)
                self._accept_cookies_if_present(page)

                target_matches = None
                if sanity_check:
                    target_matches = 1
                elif elo_match_counts and tournament.tournament_id in elo_match_counts:
                    target_matches = elo_match_counts[tournament.tournament_id]
                elif self.max_match_pages is not None:
                    target_matches = self.max_match_pages

                if tournament.oddsportal_hub:
                    match_urls = self._collect_hub_match_urls(page, target_matches=target_matches)
                else:
                    match_urls = self._collect_results_match_urls(page, target_matches=target_matches)
                match_urls = self._filter_group_stage_urls(match_urls, tournament)

                print(
                    (
                        f"[OddsPortal] {tournament.tournament_name}: discovered "
                        f"{len(match_urls)} match links from {tournament.oddsportal_results_url}"
                    ),
                    flush=True,
                )

                for index, match_url in enumerate(match_urls, start=1):
                    match_tasks.append((len(match_tasks), tournament, index, len(match_urls), match_url))

            storage_state = context.storage_state()
            browser.close()

        if not match_tasks:
            return []

        if self.odds_workers == 1:
            return self._flatten_task_results(self._collect_match_tasks(match_tasks, storage_state))

        worker_count = min(self.odds_workers, len(match_tasks))
        print(f"[OddsPortal] Collecting {len(match_tasks)} match pages with {worker_count} workers", flush=True)
        records_by_task: dict[int, list[OddsRecord]] = {}
        chunks = [match_tasks[offset::worker_count] for offset in range(worker_count)]
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(self._collect_match_tasks, chunk, storage_state) for chunk in chunks if chunk]
            for future in as_completed(futures):
                for task_index, records in future.result():
                    records_by_task[task_index] = records

        all_records: list[OddsRecord] = []
        for task_index in sorted(records_by_task):
            all_records.extend(records_by_task[task_index])
        return all_records

    def collect_match_urls(
        self,
        match_urls: Sequence[str],
        *,
        tournament: TournamentConfig | None = None,
    ) -> list[OddsRecord]:
        if not match_urls:
            return []

        placeholder = tournament or (self.tournaments[0] if self.tournaments else None)
        if placeholder is None:
            raise ValueError(
                "collect_match_urls requires at least one TournamentConfig "
                "(pass tournament= or initialize OddsPortalCollector with tournaments=[...])"
            )
        match_tasks = [
            (index, placeholder, index + 1, len(match_urls), url)
            for index, url in enumerate(match_urls)
        ]

        storage_state: dict | None = None
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)
            self._navigate_with_retry(page, self.BASE_URL)
            self._accept_cookies_if_present(page)
            storage_state = context.storage_state()
            browser.close()

        if self.odds_workers == 1:
            return self._flatten_task_results(self._collect_match_tasks(match_tasks, storage_state))

        worker_count = min(self.odds_workers, len(match_tasks))
        records_by_task: dict[int, list[OddsRecord]] = {}
        chunks = [match_tasks[offset::worker_count] for offset in range(worker_count)]
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(self._collect_match_tasks, chunk, storage_state) for chunk in chunks if chunk]
            for future in as_completed(futures):
                for task_index, records in future.result():
                    records_by_task[task_index] = records

        all_records: list[OddsRecord] = []
        for task_index in sorted(records_by_task):
            all_records.extend(records_by_task[task_index])
        return all_records

    def _append_records_to_file(self, records: list[OddsRecord]) -> None:
        if not self.output_file or not self._file_lock:
            return

        with self._file_lock:
            try:
                if self.output_file.exists():
                    with self.output_file.open("r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                else:
                    existing_data = []

                new_records = [record.to_dict() for record in records]
                existing_data.extend(new_records)

                with self.output_file.open("w", encoding="utf-8") as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"[OddsPortal] Warning: Failed to write incremental output: {e}", flush=True)

    def _flatten_task_results(self, task_results: list[tuple[int, list[OddsRecord]]]) -> list[OddsRecord]:
        all_records: list[OddsRecord] = []
        for _, records in sorted(task_results, key=lambda item: item[0]):
            all_records.extend(records)
        return all_records

    def _collect_match_tasks(
        self,
        match_tasks: list[tuple[int, TournamentConfig, int, int, str]],
        storage_state: dict | None,
    ) -> list[tuple[int, list[OddsRecord]]]:
        output: list[tuple[int, list[OddsRecord]]] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(storage_state=storage_state)
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)

            for task_index, tournament, index, total, match_url in match_tasks:
                records: list[OddsRecord] = []
                try:
                    print(
                        f"[OddsPortal] {tournament.tournament_name} ({index}/{total}) Loading {match_url}",
                        flush=True,
                    )
                    self._navigate_with_retry(page, match_url)
                    self._accept_cookies_if_present(page)
                    records = self._extract_1x2_odds_with_retry(page, match_url, tournament)
                    self._print_match_collection_summary(index, total, match_url, records)

                    if records and self.output_file:
                        self._append_records_to_file(records)

                    time.sleep(1.2)
                except Exception as exc:
                    print(
                        f"[OddsPortal] {tournament.tournament_name} ({index}/{total}) ERROR {match_url}: {exc}",
                        flush=True,
                    )
                output.append((task_index, records))

            browser.close()
        return output

    def _print_match_collection_summary(
        self,
        index: int,
        total: int,
        match_url: str,
        records: list[OddsRecord],
    ) -> None:
        if not records:
            print(f"[OddsPortal] ({index}/{total}) No 1X2 odds collected for {match_url}", flush=True)
            return

        first = records[0]
        bookmakers = ", ".join(record.bookmaker for record in records)
        print(
            (
                f"[OddsPortal] ({index}/{total}) {first.home_team} vs {first.away_team} "
                f"date={first.date_utc or 'unknown'} rows={len(records)} "
                f"bookmakers=[{bookmakers}]"
            ),
            flush=True,
        )

    def _navigate_with_retry(self, page: Page, url: str) -> None:
        for attempt in range(1, self.retry_attempts + 1):
            try:
                page.goto(url, wait_until="domcontentloaded")
                return
            except (PlaywrightTimeoutError, PlaywrightError):
                if attempt == self.retry_attempts:
                    raise
                time.sleep(0.75 * attempt)

    def _accept_cookies_if_present(self, page: Page) -> None:
        selectors = [
            'button:has-text("Accept")',
            'button:has-text("I agree")',
            "#onetrust-accept-btn-handler",
        ]
        for selector in selectors:
            button = page.locator(selector).first
            if button.count() > 0:
                try:
                    button.click()
                    return
                except Exception:
                    continue

    def _collect_results_match_urls(self, page: Page, target_matches: int | None = None) -> list[str]:
        all_links: list[str] = []
        seen_links: set[str] = set()
        page_num = 1
        max_pages = 25

        while page_num <= max_pages:
            print(f"[OddsPortal] Scanning page {page_num} for match links...", flush=True)
            page_links = self._collect_match_urls_from_current_page(page)

            if not page_links:
                print(f"[OddsPortal] No matches found on page {page_num}, stopping pagination", flush=True)
                break

            new_links = [link for link in page_links if link not in seen_links]
            if not new_links:
                print(f"[OddsPortal] Page {page_num}: no new match links found, stopping pagination", flush=True)
                break

            all_links.extend(new_links)
            seen_links.update(new_links)
            print(
                f"[OddsPortal] Page {page_num}: found {len(page_links)} matches, "
                f"{len(new_links)} new (total: {len(all_links)})",
                flush=True,
            )

            if target_matches and len(all_links) >= target_matches:
                all_links = all_links[:target_matches]
                print(f"[OddsPortal] Reached target of {target_matches} matches, stopping collection", flush=True)
                break

            needs_more = target_matches is not None and len(all_links) < target_matches
            page_looks_full = len(page_links) >= 50
            if needs_more and page_looks_full:
                if not self._navigate_to_next_page(page, page_num + 1):
                    print(f"[OddsPortal] Could not navigate to page {page_num + 1}, stopping pagination", flush=True)
                    break
                page_num += 1
                time.sleep(2)
            else:
                break

        target_str = f" (target: {target_matches})" if target_matches else ""
        print(f"[OddsPortal] Collected {len(all_links)} match URLs across {page_num} page(s){target_str}", flush=True)
        return all_links

    KNOCKOUT_URL_KEYWORDS = (
        "round-of-32",
        "round-of-16",
        "quarter-final",
        "quarterfinal",
        "semi-final",
        "semifinal",
        "third-place",
        "final",
        "r32",
        "r16",
    )

    def _filter_group_stage_urls(
        self, urls: list[str], tournament: TournamentConfig
    ) -> list[str]:
        if not getattr(tournament, "group_stage_only", False):
            return urls
        filtered: list[str] = []
        for url in urls:
            lower = url.lower()
            if any(keyword in lower for keyword in self.KNOCKOUT_URL_KEYWORDS):
                continue
            filtered.append(url)
        return filtered

    def _collect_hub_match_urls(self, page: Page, target_matches: int | None = None) -> list[str]:
        print("[OddsPortal] Hub: scanning for match links (single page)...", flush=True)
        links = self._collect_hub_urls_from_current_page(page)
        if target_matches:
            links = links[:target_matches]
        print(f"[OddsPortal] Hub: discovered {len(links)} unique match links", flush=True)
        return links

    def _scroll_hub_page(self, page: Page) -> None:
        try:
            page.evaluate(
                """async () => {
                  const delay = (ms) => new Promise((r) => setTimeout(r, ms));
                  let last = 0;
                  for (let i = 0; i < 24; i++) {
                    window.scrollTo(0, document.body.scrollHeight);
                    await delay(800);
                    const count = document.querySelectorAll('a[href*="/football/h2h/"]').length;
                    if (count === last && i > 3) break;
                    last = count;
                  }
                  window.scrollTo(0, 0);
                }"""
            )
        except PlaywrightError:
            pass

    def _collect_hub_urls_from_current_page(self, page: Page) -> list[str]:
        for attempt in range(1, 5):
            self._wait_for_hub_page_links(page, attempt)
            self._scroll_hub_page(page)
            hrefs = self._read_stable_hub_match_hrefs(page)
            links = self._dedupe_h2h_odds_urls(hrefs)
            if links:
                return links
            page.wait_for_timeout(2000 * attempt)
        return []

    def _read_stable_hub_match_hrefs(self, page: Page) -> list[str]:
        previous: list[str] | None = None
        latest: list[str] = []
        for _ in range(5):
            current = self._read_hub_match_hrefs(page)
            if current and current == previous:
                return current
            previous = current
            latest = current
            page.wait_for_timeout(2000)
        return latest

    def _read_hub_match_hrefs(self, page: Page) -> list[str]:
        return page.evaluate(
            """() => {
              const links = [];
              for (const anchor of document.querySelectorAll('a[href*="/football/h2h/"]')) {
                const href = anchor.getAttribute('href') || anchor.href;
                if (!href.includes('/football/h2h/')) continue;
                links.push(href);
              }
              return [...new Set(links)];
            }"""
        )

    def _wait_for_hub_page_links(self, page: Page, attempt: int) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except PlaywrightTimeoutError:
            pass
        try:
            page.wait_for_selector('a[href*="/football/h2h/"]', timeout=10000 + attempt * 5000)
        except PlaywrightTimeoutError:
            page.wait_for_timeout(2000 * attempt)

    def _collect_match_urls_from_current_page(self, page: Page) -> list[str]:
        for attempt in range(1, 5):
            self._wait_for_results_page_links(page, attempt)
            hrefs = self._read_stable_result_match_hrefs(page)
            links: list[str] = []

            for href in hrefs:
                if "/football/h2h/" not in href:
                    continue
                full = f"{self.BASE_URL}{href}" if href.startswith("/") else href
                if "#" not in full:
                    full = f"{full}#1X2;2"
                elif ":1X2;2" not in full:
                    full = f"{full}:1X2;2"
                if full not in links:
                    links.append(full)

            if links:
                return links

            print(
                f"[OddsPortal] Match links not ready on attempt {attempt}/4; waiting longer...",
                flush=True,
            )
            if attempt == 2:
                try:
                    page.reload(wait_until="domcontentloaded")
                except PlaywrightError:
                    pass
        return []

    def _read_stable_result_match_hrefs(self, page: Page) -> list[str]:
        previous: list[str] | None = None
        latest: list[str] = []
        for _ in range(5):
            current = self._read_visible_result_match_hrefs(page)
            if current and current == previous:
                return current
            previous = current
            latest = current
            page.wait_for_timeout(2000)
        return latest

    def _read_visible_result_match_hrefs(self, page: Page) -> list[str]:
        return page.evaluate(
            """() => {
              const links = [];
              for (const anchor of document.querySelectorAll('a[href*="/football/h2h/"]')) {
                const rect = anchor.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) continue;
                const text = (anchor.innerText || '').replace(/\\s+/g, ' ').trim();
                if (!/(Finished|After ET|After Pen\\.)/i.test(text)) continue;
                if (!/\\d+\\s*[^\\d\\s]\\s*\\d+/.test(text)) continue;
                links.push(anchor.getAttribute('href') || anchor.href);
              }
              return links;
            }"""
        )

    def _wait_for_results_page_links(self, page: Page, attempt: int) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except PlaywrightTimeoutError:
            pass
        try:
            page.wait_for_selector('a[href*="/football/h2h/"]', timeout=10000 + attempt * 5000)
        except PlaywrightTimeoutError:
            page.wait_for_timeout(2000 * attempt)

    def _navigate_to_next_page(self, page: Page, target_page: int) -> bool:
        try:
            page_elements = page.query_selector_all("button, a")
            for elem in page_elements:
                text = elem.inner_text().strip()
                if text == str(target_page):
                    elem.click()
                    time.sleep(5)
                    return True

            if target_page == 2:
                for elem in page_elements:
                    text = elem.inner_text().strip().lower()
                    if text in ["next", ">", "→"]:
                        elem.click()
                        time.sleep(5)
                        return True

            current_url = page.url
            if "page=" in current_url:
                new_url = re.sub(r"page=\d+", f"page={target_page}", current_url)
            else:
                separator = "&" if "?" in current_url else "?"
                new_url = f"{current_url}{separator}page={target_page}"

            if new_url != current_url:
                page.goto(new_url)
                time.sleep(5)
                return True

        except Exception as e:
            print(f"[OddsPortal] Error navigating to page {target_page}: {e}", flush=True)

        return False

    def _extract_1x2_odds_with_retry(
        self,
        page: Page,
        match_url: str,
        tournament: TournamentConfig,
    ) -> list[OddsRecord]:
        for attempt in range(1, 5):
            self._wait_for_odds_table(page, attempt)
            records = self._extract_1x2_odds(page, match_url, tournament)
            if records:
                return records

            if attempt < 4:
                print(
                    f"[OddsPortal] Retry {attempt}/3 for 1X2 odds: {match_url}",
                    flush=True,
                )
                page.wait_for_timeout(4000 * attempt)
                try:
                    if attempt == 2:
                        page.reload(wait_until="domcontentloaded")
                    elif attempt == 3:
                        self._navigate_with_retry(page, match_url)
                except PlaywrightError:
                    pass

        return []

    def _wait_for_odds_table(self, page: Page, attempt: int) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            pass
        try:
            page.wait_for_function(
                """() => {
                  const text = (document.body && document.body.innerText) || '';
                  return text.includes('Bookmakers') && text.includes('Payout') && text.includes('1X2');
                }""",
                timeout=15000 + attempt * 10000,
            )
        except PlaywrightTimeoutError:
            page.wait_for_timeout(3000 * attempt)

    def _extract_1x2_odds(self, page: Page, match_url: str, tournament: TournamentConfig) -> list[OddsRecord]:
        title = page.title()
        date_utc = self._extract_date_from_page(page)
        home_team, away_team = self._extract_teams_from_title(title)
        if not home_team or not away_team:
            return []

        extracted_rows = self._extract_1x2_rows_from_dom(page)
        if not extracted_rows:
            extracted_rows = self._extract_1x2_rows_from_visible_text(page)
        if not extracted_rows:
            return []

        snapshot = datetime.now(timezone.utc).isoformat()
        records: list[OddsRecord] = []
        for bookmaker, home_odds, draw_odds, away_odds in extracted_rows:
            if is_blocked_odds_bookmaker(bookmaker):
                continue
            if not is_plausible_1x2_odds(home_odds, draw_odds, away_odds):
                continue
            records.append(
                OddsRecord(
                    match_id=self._build_external_match_id(match_url),
                    tournament_id=tournament.tournament_id,
                    tournament_name=tournament.tournament_name,
                    competition=tournament.competition,
                    season_year=tournament.season_year,
                    bookmaker=bookmaker,
                    market="1X2",
                    home_odds=home_odds,
                    draw_odds=draw_odds,
                    away_odds=away_odds,
                    snapshot_time=snapshot,
                    source=match_url,
                    home_team=home_team,
                    away_team=away_team,
                    date_utc=date_utc,
                    collected_at=snapshot,
                )
            )
        return records

    def _extract_1x2_rows_from_dom(self, page: Page) -> list[tuple[str, float, float, float]]:
        rows = page.evaluate(
            """() => {
              function cleanLabel(raw) {
                const text = (raw || '').replace(/\\s+/g, ' ').trim();
                if (!text) return '';
                if (/^[0-9.,]+$/.test(text)) return '';
                if (/claim|bonus|welcome|deposit|package|exclusive/i.test(text)) return '';
                if (text.length > 45) return '';
                return text;
              }

              const names = {};
              for (const a of document.querySelectorAll('a[href*="bookmaker"]')) {
                let url;
                try { url = new URL(a.href, window.location.href); } catch (e) { continue; }
                const segs = url.pathname.split('/').filter(Boolean);
                if (segs.length < 2 || segs[0] !== 'bookmaker') continue;
                if (segs.includes('betslip')) continue;
                const slug = segs[1].toLowerCase();
                const img = a.querySelector('img[alt]');
                const imgLabel = img ? cleanLabel(img.alt) : '';
                const textLabel = cleanLabel(a.textContent);
                if (imgLabel) names[slug] = imgLabel;
                else if (textLabel && !names[slug]) names[slug] = textLabel;
              }
              const bySlug = new Map();
              for (const a of document.querySelectorAll('a[href*="betslip"]')) {
                const href = (a.getAttribute('href') || '').toLowerCase();
                const marker = '/bookmaker/';
                const mi = href.indexOf(marker);
                if (mi < 0) continue;
                const after = href.slice(mi + marker.length);
                const bi = after.indexOf('/betslip');
                if (bi < 0) continue;
                const slug = after.slice(0, bi);
                const t = (a.textContent || '').trim().replace(',', '.');
                const n = parseFloat(t);
                if (!isFinite(n)) continue;
                if (!bySlug.has(slug)) bySlug.set(slug, []);
                bySlug.get(slug).push(n);
              }
              const out = [];
              for (const [slug, nums] of bySlug) {
                const pick = nums.length > 3 ? nums.slice(0, 3) : nums;
                if (pick.length < 3) continue;
                const h = pick[0], d = pick[1], aw = pick[2];
                if (h < 1.01 || d < 1.01 || aw < 1.01) continue;
                if (h > 500 || d > 500 || aw > 500) continue;
                const lows = (h < 2.0) + (d < 2.0) + (aw < 2.0);
                if (lows >= 2) continue;
                const implied = (1/h) + (1/d) + (1/aw);
                if (implied < 0.95 || implied > 1.25) continue;
                const label = names[slug] || slug.replace(/-/g, ' ');
                out.push([label, h, d, aw]);
              }
              return out;
            }"""
        )
        parsed: list[tuple[str, float, float, float]] = []
        for row in rows or []:
            if len(row) != 4:
                continue
            label, h, d, aw = row[0], float(row[1]), float(row[2]), float(row[3])
            parsed.append((str(label), h, d, aw))
        return parsed

    def _extract_1x2_rows_from_visible_text(self, page: Page) -> list[tuple[str, float, float, float]]:
        body_text = page.locator("body").inner_text() or ""
        lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        start = self._find_1x2_bookmakers_table_start(lines)
        if start is None:
            return []

        rows: list[tuple[str, float, float, float]] = []
        index = start + 1
        while index < len(lines):
            line = lines[index]
            lowered = line.lower()
            if lowered in {"my coupon", "user predictions", "betting exchanges", "oddsalert"}:
                break
            if line in {"1", "X", "2", "Payout"} or lowered == "claim bonus":
                index += 1
                continue

            bookmaker = line
            index += 1
            odds: list[float] = []
            while index < len(lines) and len(odds) < 3:
                token = lines[index]
                token_lowered = token.lower()
                if token_lowered == "claim bonus":
                    index += 1
                    continue
                if self._looks_like_decimal_odds(token):
                    odds.append(float(token.replace(",", ".")))
                    index += 1
                    continue
                break

            if len(odds) == 3 and bookmaker:
                h, d, aw = odds[0], odds[1], odds[2]
                if is_plausible_1x2_odds(h, d, aw) and not is_blocked_odds_bookmaker(bookmaker):
                    rows.append((bookmaker, h, d, aw))

            while index < len(lines) and (lines[index] == "-" or lines[index].endswith("%")):
                index += 1

        return rows

    def _find_1x2_bookmakers_table_start(self, lines: list[str]) -> int | None:
        for index, line in enumerate(lines):
            if line.lower() != "bookmakers":
                continue

            window = [item.lower() for item in lines[index + 1 : index + 8]]
            has_1x2_header = "1" in window and "x" in window and "2" in window
            has_payout = "payout" in window
            if has_1x2_header and has_payout:
                return index

        return None

    def _looks_like_decimal_odds(self, token: str) -> bool:
        try:
            value = float(token.replace(",", "."))
        except ValueError:
            return False
        return 1.01 <= value <= 500

    def _extract_date_from_page(self, page: Page) -> str | None:
        body_text = page.locator("body").inner_text() or ""
        date_re = re.compile(r"\b(\d{1,2}\s+[A-Za-z]{3}\s+20\d{2})\b")
        match = date_re.search(body_text)
        if match:
            parsed = datetime.strptime(match.group(1), "%d %b %Y")
            return parsed.replace(tzinfo=timezone.utc).isoformat()
        iso_re = re.compile(r"(20\d{2}-\d{2}-\d{2})")
        match_iso = iso_re.search(body_text)
        if match_iso:
            return f"{match_iso.group(1)}T00:00:00+00:00"
        return None

    def _extract_teams_from_title(self, title: str) -> tuple[str | None, str | None]:
        title_prefix = title.split("|", maxsplit=1)[0].strip()
        if " - " in title_prefix:
            left, right = title_prefix.split(" - ", maxsplit=1)
        elif " vs " in title_prefix:
            left, right = title_prefix.split(" vs ", maxsplit=1)
        else:
            return None, None
        right_clean = right.replace("Odds, Predictions & H2H", "").strip()
        return left.strip(), right_clean

    def _build_external_match_id(self, match_url: str) -> str:
        parsed = urlparse(match_url)
        path_slug = parsed.path.rstrip("/").rsplit("/", maxsplit=1)[-1] or "match"
        fragment_slug = re.sub(r"[^a-zA-Z0-9]+", "-", parsed.fragment).strip("-")
        if fragment_slug:
            return f"odds-{path_slug}-{fragment_slug}"
        return f"odds-{path_slug}"
