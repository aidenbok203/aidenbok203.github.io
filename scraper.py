#!/usr/bin/env python3
"""
OCR H446/H047 Computer Science Past Paper Scraper
Outputs: assets/questions.json

Dependencies: pip install requests beautifulsoup4 pdfplumber
"""

import json
import re
import time
import random
import hashlib
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
import pdfplumber


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
BROWSER_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}
DELAY_MIN = 1.0
DELAY_MAX = 2.0
TMP_DIR = Path("tmp")
OUTPUT_PATH = Path("assets") / "questions.json"

# PMT HTML index pages (list PDFs with direct download hrefs)
PMT_BASE = "https://www.physicsandmathstutor.com"
PMT_DL_DIRS = [
    ("https://www.physicsandmathstutor.com/past-papers/a-level-computer-science/ocr-paper-1/",    1, "H446/01", "alevel"),
    ("https://www.physicsandmathstutor.com/past-papers/a-level-computer-science/ocr-paper-2/",    2, "H446/02", "alevel"),
]
PMT_AS_DL_DIRS = [
    ("https://www.physicsandmathstutor.com/past-papers/a-level-computer-science/ocr-paper-1-as/", 1, "H047/01", "aslevel"),
    ("https://www.physicsandmathstutor.com/past-papers/a-level-computer-science/ocr-paper-2-as/", 2, "H047/02", "aslevel"),
]
PMT_REFERER = "https://www.physicsandmathstutor.com/past-papers/a-level-computer-science/"

OCR_ALEVEL_PAGE = (
    "https://www.ocr.org.uk/qualifications/"
    "as-and-a-level/computer-science-h446-from-2015/assessment/"
)
OCR_ASLEVEL_PAGE = (
    "https://www.ocr.org.uk/qualifications/"
    "as-and-a-level/computer-science-as-h047-from-2015/assessment/"
)

# spec_id -> (component, display_name)
TOPICS: dict = {
    "1.1.1_processor_structure":            (1, "Processor Structure"),
    "1.1.2_types_of_processor":             (1, "Types of Processor"),
    "1.1.3_input_output_storage":           (1, "Input/Output/Storage"),
    "1.2.1_systems_software":               (1, "Systems Software"),
    "1.2.2_applications_generation":        (1, "Applications Generation"),
    "1.2.3_software_development":           (1, "Software Development"),
    "1.2.4_programming_languages":          (1, "Programming Languages"),
    "1.3.1_compression_encryption_hashing": (1, "Compression, Encryption & Hashing"),
    "1.3.2_databases":                      (1, "Databases"),
    "1.3.3_networks":                       (1, "Networks"),
    "1.3.4_web_technologies":               (1, "Web Technologies"),
    "1.4.1_data_types":                     (1, "Data Types"),
    "1.4.2_data_structures":                (1, "Data Structures"),
    "1.4.3_boolean_algebra":                (1, "Boolean Algebra"),
    "1.5.1_legislation":                    (1, "Legislation"),
    "1.5.2_moral_ethical":                  (1, "Moral & Ethical Issues"),
    "2.1.1_thinking_abstractly":            (2, "Thinking Abstractly"),
    "2.1.2_thinking_ahead":                 (2, "Thinking Ahead"),
    "2.1.3_thinking_procedurally":          (2, "Thinking Procedurally"),
    "2.1.4_thinking_logically":             (2, "Thinking Logically"),
    "2.1.5_thinking_concurrently":          (2, "Thinking Concurrently"),
    "2.2.1_programming_techniques":         (2, "Programming Techniques"),
    "2.2.2_computational_methods":          (2, "Computational Methods"),
    "2.3.1_algorithms":                     (2, "Algorithms"),
}

PMT_TOPIC_MAP: dict = {
    "processor-components":               "1.1.1_processor_structure",
    "processor-structure":                "1.1.1_processor_structure",
    "processors":                         "1.1.1_processor_structure",
    "types-of-processor":                 "1.1.2_types_of_processor",
    "input-output-and-storage":           "1.1.3_input_output_storage",
    "input-output-storage":               "1.1.3_input_output_storage",
    "storage":                            "1.1.3_input_output_storage",
    "systems-software":                   "1.2.1_systems_software",
    "applications-and-their-generation":  "1.2.2_applications_generation",
    "applications-generation":            "1.2.2_applications_generation",
    "software-development":               "1.2.3_software_development",
    "programming-languages":              "1.2.4_programming_languages",
    "compression-encryption-and-hashing": "1.3.1_compression_encryption_hashing",
    "compression-encryption-hashing":     "1.3.1_compression_encryption_hashing",
    "databases":                          "1.3.2_databases",
    "networking":                         "1.3.3_networks",
    "networks":                           "1.3.3_networks",
    "web-technologies":                   "1.3.4_web_technologies",
    "data-types":                         "1.4.1_data_types",
    "data-structures":                    "1.4.2_data_structures",
    "boolean-algebra":                    "1.4.3_boolean_algebra",
    "legislation":                        "1.5.1_legislation",
    "moral-and-ethical-issues":           "1.5.2_moral_ethical",
    "thinking-abstractly":                "2.1.1_thinking_abstractly",
    "thinking-ahead":                     "2.1.2_thinking_ahead",
    "thinking-procedurally":              "2.1.3_thinking_procedurally",
    "thinking-logically":                 "2.1.4_thinking_logically",
    "thinking-concurrently":              "2.1.5_thinking_concurrently",
    "programming-techniques":             "2.2.1_programming_techniques",
    "computational-methods":              "2.2.2_computational_methods",
    "algorithms":                         "2.3.1_algorithms",
    "searching-and-sorting":              "2.3.1_algorithms",
    "complexity":                         "2.3.1_algorithms",
}

TOPIC_KEYWORDS: dict = {
    "1.1.1_processor_structure": [
        "ALU", "CU", "control unit", "register", "PC", "program counter",
        "accumulator", "ACC", "MAR", "MDR", "CIR", "fetch", "decode", "execute",
        "FDE cycle", "pipeline", "pipelining", "Von Neumann", "Harvard",
        "clock speed", "cache", "address bus", "data bus", "control bus",
        "addressing mode", "instruction set", "op-code", "operand",
        "interrupt", "processor", "CPU", "arithmetic logic unit",
    ],
    "1.1.2_types_of_processor": [
        "CISC", "RISC", "GPU", "multicore", "parallel processing",
        "reduced instruction set", "complex instruction set",
        "co-processor", "superscalar", "vector processor",
    ],
    "1.1.3_input_output_storage": [
        "input device", "output device", "magnetic storage", "flash memory",
        "optical storage", "SSD", "HDD", "hard disk drive", "RAM", "ROM",
        "virtual storage", "cloud storage", "secondary storage", "primary storage",
    ],
    "1.2.1_systems_software": [
        "operating system", "paging", "segmentation", "virtual memory", "interrupt",
        "interrupt service routine", "ISR", "scheduling algorithm", "round robin",
        "FCFS", "MLFQ", "SJF", "SRT", "BIOS", "device driver",
        "virtual machine", "multitasking", "multi-user", "real-time OS",
    ],
    "1.2.2_applications_generation": [
        "interpreter", "compiler", "assembler", "lexical analysis", "tokenisation",
        "syntax analysis", "parsing", "code generation", "optimisation", "linker",
        "loader", "library", "open source", "closed source", "utility software",
    ],
    "1.2.3_software_development": [
        "waterfall model", "agile", "extreme programming", "spiral model",
        "RAD", "rapid application development", "software development methodology",
    ],
    "1.2.4_programming_languages": [
        "LMC", "assembly language", "mnemonic", "addressing mode",
        "immediate addressing", "direct addressing", "indirect addressing",
        "indexed addressing", "object-oriented", "class definition", "object",
        "method", "attribute", "inheritance", "encapsulation", "polymorphism",
        "programming paradigm", "procedural programming",
    ],
    "1.3.1_compression_encryption_hashing": [
        "compression", "lossy compression", "lossless compression",
        "run-length encoding", "RLE", "dictionary coding", "encryption",
        "symmetric encryption", "asymmetric encryption", "public key",
        "private key", "hash function", "hashing",
    ],
    "1.3.2_databases": [
        "relational database", "flat file database", "primary key", "foreign key",
        "secondary key", "entity relationship diagram", "ER diagram",
        "normalisation", "first normal form", "second normal form",
        "third normal form", "1NF", "2NF", "3NF", "SQL", "SELECT", "FROM",
        "WHERE", "JOIN", "INSERT INTO", "DELETE FROM", "DROP TABLE",
        "referential integrity", "ACID properties", "transaction processing",
        "record locking", "data redundancy",
    ],
    "1.3.3_networks": [
        "computer network", "TCP/IP", "TCP", "DNS", "network protocol",
        "LAN", "WAN", "packet switching", "circuit switching", "firewall",
        "proxy server", "MAC address", "router", "network switch", "hub",
        "client-server model", "peer-to-peer", "bandwidth", "network topology",
        "HTTP", "HTTPS", "FTP", "SMTP", "Wi-Fi", "Ethernet", "IP address",
        "subnet mask", "network hardware",
    ],
    "1.3.4_web_technologies": [
        "HTML", "CSS", "JavaScript", "search engine", "PageRank algorithm",
        "web indexing", "server-side processing", "client-side processing",
        "Document Object Model", "DOM", "web server",
    ],
    "1.4.1_data_types": [
        "binary number", "hexadecimal", "denary", "two's complement",
        "sign and magnitude", "floating point", "mantissa", "exponent",
        "normalisation of floating point", "ASCII", "Unicode",
        "bitwise operation", "bit shift", "logical AND", "logical OR",
        "XOR operation", "integer data type", "Boolean", "character",
        "store data in binary", "binary representation", "convert to binary",
        "convert to denary", "convert to hexadecimal", "number system",
        "overflow", "underflow", "precision",
    ],
    "1.4.2_data_structures": [
        "array", "linked list", "stack", "queue", "binary tree",
        "binary search tree", "graph", "hash table", "record", "tuple",
        "list", "node", "pointer", "push operation", "pop operation",
        "enqueue", "dequeue", "tree traversal", "breadth-first search",
        "depth-first search", "in-order traversal", "pre-order traversal",
        "post-order traversal",
    ],
    "1.4.3_boolean_algebra": [
        "Boolean algebra", "logic gate", "truth table", "AND gate", "OR gate",
        "NOT gate", "NAND gate", "NOR gate", "XOR gate", "De Morgan's law",
        "Karnaugh map", "K-map", "Boolean simplification", "D-type flip-flop",
        "half adder", "full adder", "sum of products", "product of sums",
    ],
    "1.5.1_legislation": [
        "Data Protection Act", "Computer Misuse Act", "Copyright Designs and Patents",
        "RIPA", "Regulation of Investigatory Powers Act", "legislation",
        "DPA 1998", "CMA 1990",
    ],
    "1.5.2_moral_ethical": [
        "ethical issue", "moral issue", "workforce automation", "employment",
        "artificial intelligence", "environmental impact", "censorship",
        "surveillance", "monitoring behaviour", "privacy", "software piracy",
        "offensive communications", "digital divide", "automated decision making",
    ],
    "2.1.1_thinking_abstractly": [
        "abstraction", "abstract model", "hiding detail", "level of abstraction",
        "representation of reality",
    ],
    "2.1.2_thinking_ahead": [
        "precondition", "caching", "cache", "reusable component",
        "identifying inputs", "identifying outputs",
    ],
    "2.1.3_thinking_procedurally": [
        "problem decomposition", "sub-procedure", "ordering steps",
        "identifying components of solution",
    ],
    "2.1.4_thinking_logically": [
        "decision point", "logical condition", "program flow control",
        "branching logic",
    ],
    "2.1.5_thinking_concurrently": [
        "concurrency", "concurrent processing", "parallel processing",
        "simultaneous execution", "thread",
    ],
    "2.2.1_programming_techniques": [
        "recursion", "recursive function", "base case", "iteration",
        "loop construct", "function definition", "procedure", "parameter passing",
        "local variable", "global variable", "pass by value", "pass by reference",
        "modular programming", "IDE", "logic error", "syntax error",
        "runtime error", "dry run", "trace table", "pseudocode",
        "function", "subroutine", "while loop", "for loop",
    ],
    "2.2.2_computational_methods": [
        "divide and conquer", "backtracking algorithm", "data mining",
        "heuristic approach", "performance modelling", "visualisation",
        "computational thinking",
    ],
    "2.3.1_algorithms": [
        "algorithm", "Big O notation", "time complexity", "space complexity",
        "bubble sort", "insertion sort", "merge sort", "quicksort",
        "Dijkstra's algorithm", "A* algorithm", "binary search",
        "linear search", "O(n)", "O(log n)", "O(n^2)", "O(1)",
        "sort algorithm", "search algorithm", "each pass", "show each pass",
        "sorting", "sorted", "trace through", "trace the",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Robots-safe HTTP session
# ─────────────────────────────────────────────────────────────────────────────

class RobotsSafeSession:
    """requests.Session wrapper that checks robots.txt and rate-limits."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(BROWSER_HEADERS)
        self._robots: dict = {}

    def _robots_for(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        key = f"{parsed.scheme}://{parsed.netloc}"
        if key not in self._robots:
            rp = RobotFileParser()
            try:
                # Fetch with browser UA via requests (not urllib, which uses a bot UA)
                resp = requests.get(
                    f"{key}/robots.txt", headers=BROWSER_HEADERS, timeout=10
                )
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                # 404 or other non-200 -> no rules parsed -> allow all
            except Exception:
                pass  # network error -> allow all
            self._robots[key] = rp
        return self._robots[key]

    def get(self, url: str, **kwargs) -> requests.Response:
        rp = self._robots_for(url)
        if not rp.can_fetch(BROWSER_UA, url):
            raise PermissionError(f"robots.txt disallows: {url}")
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        resp = self._session.get(url, timeout=30, **kwargs)
        resp.raise_for_status()
        return resp


# ─────────────────────────────────────────────────────────────────────────────
# Topic tagger
# ─────────────────────────────────────────────────────────────────────────────

class TopicTagger:
    """Scores question text against keyword sets; returns best-matching topic ID."""

    def tag(self, text: str, hint: str = None) -> str:
        if hint and hint in TOPICS:
            return hint
        text_lower = text.lower()
        scores: dict = {}
        for topic_id, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score:
                scores[topic_id] = score
        if not scores:
            return None
        return max(scores, key=lambda t: scores[t])


# ─────────────────────────────────────────────────────────────────────────────
# PDF question parser
# ─────────────────────────────────────────────────────────────────────────────

class PDFQuestionParser:
    """Extracts structured questions from a pdfplumber-opened PDF."""

    _RE_TOP = re.compile(r'^\s*(\d{1,2})\s{1,4}(\S)', re.MULTILINE)
    _RE_SUB_A = re.compile(r'^\s*\(([a-z])\)\s+', re.MULTILINE)
    _RE_SUB_I = re.compile(r'^\s*\(([ivxlIVXL]+)\)\s+', re.MULTILINE)
    _RE_MARKS = re.compile(r'\[(\d+)\]')
    _RE_MARKS2 = re.compile(r'\((\d+)\s*marks?\)', re.IGNORECASE)

    def _extract_marks(self, text: str) -> int:
        m = self._RE_MARKS.findall(text)
        if m:
            return int(m[-1])
        m2 = self._RE_MARKS2.findall(text)
        if m2:
            return int(m2[-1])
        return 0

    def _clean(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\s*\[\d+\]\s*$', '', text)
        return text

    def parse(self, pdf_path: Path, year: int, paper: str, level: str) -> list:
        questions: list = []
        component = 1 if "/01" in paper else 2
        tagger = TopicTagger()

        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        except Exception as e:
            print(f"  [!] pdfplumber error on {pdf_path.name}: {e}")
            return []

        top_parts = self._RE_TOP.split(full_text)
        i = 1
        q_number = 0
        while i + 2 < len(top_parts):
            q_number += 1
            num_str = top_parts[i]
            first_char = top_parts[i + 1]
            block = first_char + top_parts[i + 2]
            i += 3

            sub_parts = self._RE_SUB_A.split(block)
            if len(sub_parts) <= 1:
                text = self._clean(block)
                marks = self._extract_marks(block)
                topic = tagger.tag(text)
                q_id = re.sub(
                    r'[^a-z0-9\-]', '',
                    f"{paper.lower().replace('/', '-')}-{year}-q{num_str}"
                )
                questions.append({
                    "id": q_id,
                    "year": year,
                    "paper": paper,
                    "level": level,
                    "topic": topic or "unknown",
                    "component": component,
                    "text": text,
                    "marks": marks,
                    "sub_questions": [],
                })
            else:
                intro = self._clean(sub_parts[0])
                subs: list = []
                total_marks = 0
                j = 1
                while j + 1 < len(sub_parts):
                    sub_label = sub_parts[j]
                    sub_text_raw = sub_parts[j + 1]
                    j += 2
                    subsub_parts = self._RE_SUB_I.split(sub_text_raw)
                    if len(subsub_parts) > 1:
                        subsub_list: list = []
                        k = 1
                        while k + 1 < len(subsub_parts):
                            ss_label = subsub_parts[k]
                            ss_text = self._clean(subsub_parts[k + 1])
                            ss_marks = self._extract_marks(subsub_parts[k + 1])
                            total_marks += ss_marks
                            subsub_list.append({
                                "label": ss_label,
                                "text": ss_text,
                                "marks": ss_marks,
                                "sub_questions": [],
                            })
                            k += 2
                        sub_marks = sum(s["marks"] for s in subsub_list)
                        subs.append({
                            "label": sub_label,
                            "text": self._clean(subsub_parts[0]),
                            "marks": sub_marks,
                            "sub_questions": subsub_list,
                        })
                    else:
                        sub_text = self._clean(sub_text_raw)
                        sub_marks = self._extract_marks(sub_text_raw)
                        total_marks += sub_marks
                        subs.append({
                            "label": sub_label,
                            "text": sub_text,
                            "marks": sub_marks,
                            "sub_questions": [],
                        })

                combined = intro + " " + " ".join(s["text"] for s in subs)
                topic = tagger.tag(combined)
                q_id = re.sub(
                    r'[^a-z0-9\-]', '',
                    f"{paper.lower().replace('/', '-')}-{year}-q{num_str}"
                )
                questions.append({
                    "id": q_id,
                    "year": year,
                    "paper": paper,
                    "level": level,
                    "topic": topic or "unknown",
                    "component": component,
                    "text": intro,
                    "marks": total_marks or self._extract_marks(block),
                    "sub_questions": subs,
                })

        return questions


# ─────────────────────────────────────────────────────────────────────────────
# OCR PDF scraper
# ─────────────────────────────────────────────────────────────────────────────

class OCRPDFScraper:
    """Downloads OCR past paper PDFs and extracts questions."""

    _RE_YEAR = re.compile(r'(20\d{2})')
    _RE_PAPER = re.compile(r'(H[04][4][67][/_\-]0[12])', re.IGNORECASE)

    def __init__(self, session: RobotsSafeSession) -> None:
        self._session = session
        self._parser = PDFQuestionParser()
        TMP_DIR.mkdir(exist_ok=True)

    def _find_pdf_links(self, page_url: str) -> list:
        try:
            resp = self._session.get(page_url)
        except Exception as e:
            print(f"  [!] Failed to fetch {page_url}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        links: list = []
        seen: set = set()
        for a in soup.find_all("a", href=True):
            href: str = a["href"]
            if not href.lower().endswith(".pdf"):
                continue
            name = href.split("/")[-1].lower()
            if name in seen:
                continue
            seen.add(name)
            # Accept question papers; skip mark schemes
            is_qp = any(kw in name for kw in ("qp", "question_paper", "question-paper"))
            is_ms = any(kw in name for kw in ("mark", "_ms", "-ms", "mark_scheme"))
            if is_ms:
                continue
            if is_qp or any(kw in name for kw in ("h446", "h047")):
                links.append((urljoin(page_url, href), href.split("/")[-1]))
        return links

    def _infer_meta(self, filename: str) -> tuple:
        year_m = self._RE_YEAR.search(filename)
        year = int(year_m.group(1)) if year_m else None
        paper_m = self._RE_PAPER.search(filename.upper())
        paper = None
        if paper_m:
            paper = re.sub(r'[_\-]', '/', paper_m.group(1).upper())
            if paper.count('/') > 1:
                paper = paper[:7]
        return year, paper

    def scrape(self, page_url: str, level: str) -> list:
        print(f"[OCR] Scanning {page_url}")
        links = self._find_pdf_links(page_url)
        print(f"  Found {len(links)} potential PDFs")
        questions: list = []

        for url, filename in links:
            year, paper = self._infer_meta(filename)
            if not year or not paper:
                print(f"  [skip] Cannot infer year/paper: {filename}")
                continue
            dest = TMP_DIR / filename
            if not dest.exists():
                print(f"  [dl] {filename}")
                try:
                    resp = self._session.get(url)
                    dest.write_bytes(resp.content)
                except Exception as e:
                    print(f"  [!] Download failed: {e}")
                    continue
            else:
                print(f"  [cached] {filename}")
                time.sleep(0.1)

            qs = self._parser.parse(dest, year, paper, level)
            print(f"  -> {len(qs)} questions from {filename}")
            questions.extend(qs)

        return questions


# ─────────────────────────────────────────────────────────────────────────────
# PMT scraper
# ─────────────────────────────────────────────────────────────────────────────

class PMTPDFScraper:
    """
    Downloads past paper PDFs from pmt.physicsandmathstutor.com/download/
    (public file server, no robots restriction on downloads).
    Parses each PDF with PDFQuestionParser.
    """

    _RE_YEAR = re.compile(r'(20\d{2})')

    def __init__(self, session: RobotsSafeSession) -> None:
        self._session = session
        self._parser = PDFQuestionParser()
        TMP_DIR.mkdir(exist_ok=True)

    def _list_pdfs(self, index_url: str) -> list:
        """Scrape PMT index page; return list of (absolute_url, filename) for QPs."""
        try:
            resp = self._session.get(
                index_url, headers={"Referer": PMT_REFERER}
            )
        except Exception as e:
            print(f"  [!] Cannot fetch {index_url}: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list = []
        seen: set = set()
        for a in soup.find_all("a", href=True):
            href: str = a["href"]
            if "pmt.physicsandmathstutor.com" not in href:
                continue
            if not href.lower().endswith(".pdf"):
                continue
            # URL-decode to get clean filename
            from urllib.parse import unquote
            filename = unquote(href.split("/")[-1])
            if filename in seen:
                continue
            seen.add(filename)
            # Skip mark schemes — PMT uses " MS " in filename
            low = filename.lower()
            if any(kw in low for kw in (" ms ", "-ms-", "_ms_", " ms.", "mark scheme")):
                continue
            # Only keep question papers
            if " qp " not in low and " qp-" not in low and "qp " not in low:
                continue
            results.append((href, filename))
        return results

    def _infer_year(self, filename: str) -> int:
        m = self._RE_YEAR.search(filename)
        return int(m.group(1)) if m else 0

    def scrape(self, dirs: list) -> list:
        """dirs: list of (url, component, paper_ref, level)"""
        all_questions: list = []
        for index_url, _comp, paper_ref, level in dirs:
            print(f"[PMT] Fetching index {index_url}")
            pdfs = self._list_pdfs(index_url)
            print(f"  Found {len(pdfs)} QP PDFs")

            for pdf_url, filename in pdfs:
                year = self._infer_year(filename)
                # Use URL-safe filename for local storage
                safe_name = re.sub(r'[^\w\-. ]', '_', filename)
                dest = TMP_DIR / safe_name
                if not dest.exists():
                    print(f"  [dl] {filename}")
                    try:
                        resp = self._session.get(
                            pdf_url,
                            headers={"Referer": index_url}
                        )
                        dest.write_bytes(resp.content)
                    except Exception as e:
                        print(f"  [!] Download failed: {e}")
                        continue
                else:
                    print(f"  [cached] {filename}")
                    time.sleep(0.1)

                qs = self._parser.parse(dest, year, paper_ref, level)
                print(f"  -> {len(qs)} questions from {filename}")
                all_questions.extend(qs)

        return all_questions


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def deduplicate(questions: list) -> list:
    seen: set = set()
    unique: list = []
    for q in questions:
        key = hashlib.md5(q["text"][:120].encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(q)
    return unique


# ─────────────────────────────────────────────────────────────────────────────
# Local PDF processor  (PRIMARY mode — most reliable)
# ─────────────────────────────────────────────────────────────────────────────

LOCAL_PDF_DIR = Path("pdfs")
"""
Place question paper PDFs here before running the scraper.
Naming convention (any format is accepted — the scraper infers from content):
  Recommended: include year and paper ref in filename, e.g.
    H446_01_2023_June.pdf       -> H446/01, 2023
    H446-02-2022.pdf            -> H446/02, 2022
    June_2019_QP_Paper1.pdf     -> H446/01 (Component 1), 2019
    H047_01_2021.pdf            -> H047/01 (AS Level), 2021

Sources to download from:
  PMT (A Level): https://www.physicsandmathstutor.com/past-papers/a-level-computer-science/
  PMT (AS Level): https://www.physicsandmathstutor.com/past-papers/a-level-computer-science/
  Direct from OCR: https://www.ocr.org.uk
"""

_RE_LOCAL_YEAR  = re.compile(r'(20\d{2})')
_RE_LOCAL_PAPER = re.compile(r'(H[04][4][67])[_\-/\s]*(0[12])', re.IGNORECASE)
_PAPER_COMP_MAP = {"01": 1, "02": 2, "1": 1, "2": 2}


def process_local_pdfs() -> list:
    """Parse all PDFs in LOCAL_PDF_DIR. Returns list of question dicts."""
    if not LOCAL_PDF_DIR.exists():
        return []

    pdf_files = sorted(LOCAL_PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"  No PDFs found in {LOCAL_PDF_DIR}/")
        return []

    parser = PDFQuestionParser()
    all_questions: list = []

    for pdf_path in pdf_files:
        name = pdf_path.name

        # Infer year
        ym = _RE_LOCAL_YEAR.search(name)
        year = int(ym.group(1)) if ym else 0

        # Infer paper ref and level
        pm = _RE_LOCAL_PAPER.search(name.upper())
        if pm:
            qual   = pm.group(1).upper()   # H446 or H047
            comp_s = pm.group(2)            # 01 or 02
            paper  = f"{qual}/{comp_s}"
            level  = "aslevel" if qual == "H047" else "alevel"
        else:
            # Fall back: guess from filename keywords
            comp_s = "01"
            if any(k in name.lower() for k in ("paper-2", "paper_2", "paper 2", "comp2", "comp-2", "_02", "-02")):
                comp_s = "02"
            paper  = f"H446/{comp_s}"
            level  = "alevel"
            print(f"  [warn] Cannot infer paper ref from '{name}' — assuming {paper}")

        component = _PAPER_COMP_MAP.get(comp_s.lstrip("0") or "0", 1)
        print(f"  [parse] {name}  =>  paper={paper}  year={year}  level={level}")
        qs = parser.parse(pdf_path, year, paper, level)
        print(f"          {len(qs)} questions extracted")
        all_questions.extend(qs)

    return all_questions


def main() -> None:
    all_questions: list = []

    # ── 1. Local PDFs (primary — always run) ──────────────────────────────────
    print("\n=== Local PDFs ===")
    print(f"Scanning {LOCAL_PDF_DIR}/ ...")
    if not LOCAL_PDF_DIR.exists():
        print(f"  Folder '{LOCAL_PDF_DIR}' not found.")
        print("  Create it and place question-paper PDFs inside, then re-run.")
        print("  Download from: https://www.physicsandmathstutor.com/past-papers/a-level-computer-science/")
    else:
        local_qs = process_local_pdfs()
        all_questions.extend(local_qs)
        print(f"Local PDFs total: {len(local_qs)}")

    # ── 2. PMT web scraper (supplement — may be blocked) ─────────────────────
    print("\n=== PMT Web Scraper ===")
    try:
        session = RobotsSafeSession()
        pmt = PMTPDFScraper(session)
        pmt_qs = pmt.scrape(PMT_DL_DIRS + PMT_AS_DL_DIRS)
        all_questions.extend(pmt_qs)
        print(f"PMT web total: {len(pmt_qs)}")
    except Exception as e:
        print(f"  PMT scraper failed: {e}")

    # ── 3. OCR web scraper (supplement — may be blocked) ─────────────────────
    print("\n=== OCR Web Scraper ===")
    try:
        ocr = OCRPDFScraper(session)
        alevel_qs  = ocr.scrape(OCR_ALEVEL_PAGE,  "alevel")
        aslevel_qs = ocr.scrape(OCR_ASLEVEL_PAGE, "aslevel")
        all_questions.extend(alevel_qs)
        all_questions.extend(aslevel_qs)
        print(f"OCR web total: {len(alevel_qs + aslevel_qs)}")
    except Exception as e:
        print(f"  OCR scraper failed: {e}")

    if not all_questions:
        print("\nNo questions collected. Add PDFs to the pdfs/ folder and re-run.")
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(
            {"generated": date.today().isoformat(), "count": 0, "questions": []},
            indent=2
        ))
        return

    # ── Deduplicate ───────────────────────────────────────────────────────────
    before = len(all_questions)
    all_questions = deduplicate(all_questions)
    print(f"\nDeduplication: {before} -> {len(all_questions)}")

    # ── Filter garbage questions ──────────────────────────────────────────────
    _ARTIFACT_PHRASES = [
        "end of question paper", "turn over", "blank page",
        "do not write", "total marks", "examiner only",
    ]

    def _is_garbage(q: dict) -> bool:
        text = q.get("text", "").strip()
        marks = q.get("marks", 0)
        subs = q.get("sub_questions", [])
        sub_marks = sum(s.get("marks", 0) for s in subs)

        # Questions with real marks or sub-questions with marks: keep unless obvious artifact
        if marks > 0 or sub_marks > 0:
            tl = text.lower()
            if any(p in tl for p in _ARTIFACT_PHRASES):
                return True
            # Keep even with empty/short text (sub-questions carry content)
            return False

        # Zero marks, no useful sub-questions: apply stricter checks
        if not text or len(text) < 10:
            return True
        alpha = sum(1 for c in text if c.isalpha())
        if alpha < 6:
            return True
        tl = text.lower()
        if any(p in tl for p in _ARTIFACT_PHRASES):
            return True
        # Answer-space-only lines (mostly dots/underscores)
        non_space = text.replace(" ", "").replace(".", "").replace("_", "")
        if len(non_space) < 6:
            return True
        return False

    before_filter = len(all_questions)
    all_questions = [q for q in all_questions if not _is_garbage(q)]
    print(f"Garbage filter: {before_filter} -> {len(all_questions)} (removed {before_filter - len(all_questions)})")

    topic_counts: dict = {}
    for q in all_questions:
        topic_counts[q["topic"]] = topic_counts.get(q["topic"], 0) + 1

    print("\nPer-topic breakdown:")
    for tid, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        name = TOPICS.get(tid, (0, tid))[1]
        print(f"  {tid:50s} {count:4d}  ({name})")

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    payload = {
        "generated": date.today().isoformat(),
        "count": len(all_questions),
        "questions": all_questions,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\nWritten {len(all_questions)} questions -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
