"""
Coda API Helper for Claude Code
================================
회의록 읽기·분석 / Wiki 참조 / 테이블 읽기·쓰기 / 페이지 생성·업데이트
Usage: python3 coda_helper.py [command] [options]
"""

import os, sys, json, time, requests

API_TOKEN = os.environ.get("CODA_API_TOKEN", "")
BASE_URL  = "https://coda.io/apis/v1"
HEADERS   = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}

def check_token():
    if not API_TOKEN:
        print("❌ CODA_API_TOKEN 환경변수 없음\n   export CODA_API_TOKEN='your_token'")
        sys.exit(1)

# ── 1. 문서 목록 ──────────────────────────
def list_docs():
    check_token()
    r = requests.get(f"{BASE_URL}/docs", headers=HEADERS); r.raise_for_status()
    docs = r.json().get("items", [])
    print(f"\n📚 문서 목록 ({len(docs)}개)\n" + "-"*60)
    for d in docs:
        print(f"  ID: {d['id']:<20}  이름: {d['name']}")
    return docs

# ── 2. 페이지 목록 ────────────────────────
def list_pages(doc_id):
    check_token()
    r = requests.get(f"{BASE_URL}/docs/{doc_id}/pages", headers=HEADERS); r.raise_for_status()
    pages = r.json().get("items", [])
    print(f"\n📄 페이지 목록 ({len(pages)}개)\n" + "-"*60)
    for p in pages:
        indent = "    ↳ " if p.get("parent") else "  "
        print(f"{indent}ID: {p['id']:<20}  이름: {p['name']}")
    return pages

# ── 3. 페이지 내용 읽기 ───────────────────
def read_page(doc_id, page_id, output_file=None):
    check_token()
    r = requests.get(f"{BASE_URL}/docs/{doc_id}/pages/{page_id}", headers=HEADERS)
    r.raise_for_status()
    content = json.dumps(r.json(), ensure_ascii=False, indent=2)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f: f.write(content)
        print(f"✅ 저장: {output_file}")
    else:
        print(content)
    return content

# ── 4. 테이블 목록 ────────────────────────
def list_tables(doc_id):
    check_token()
    r = requests.get(f"{BASE_URL}/docs/{doc_id}/tables", headers=HEADERS); r.raise_for_status()
    tables = r.json().get("items", [])
    print(f"\n📊 테이블 목록 ({len(tables)}개)\n" + "-"*60)
    for t in tables:
        print(f"  ID: {t['id']:<25}  이름: {t['name']}  (행: {t.get('rowCount','?')})")
    return tables

# ── 5. 테이블 데이터 읽기 ─────────────────
def read_table(doc_id, table_id, limit=100, output_file=None):
    check_token()
    r = requests.get(f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows",
                     headers=HEADERS, params={"limit": limit}); r.raise_for_status()
    rows = r.json().get("items", [])
    cr = requests.get(f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/columns", headers=HEADERS)
    columns = {c["id"]: c["name"] for c in cr.json().get("items", [])}
    result = []
    for row in rows:
        rd = {"_id": row["id"]}
        for cid, val in row.get("values", {}).items():
            rd[columns.get(cid, cid)] = val
        result.append(rd)
    print(f"✅ {len(result)}개 행 읽기 완료")
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"📁 저장: {output_file}")
    else:
        print(json.dumps(result[:5], ensure_ascii=False, indent=2))
        if len(result) > 5: print(f"  ... 외 {len(result)-5}개 행")
    return result

# ── 6. 테이블 행 추가 ─────────────────────
def add_row(doc_id, table_id, data):
    check_token()
    cr = requests.get(f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/columns", headers=HEADERS)
    col_map = {c["name"]: c["id"] for c in cr.json().get("items", [])}
    cells = [{"column": col_map[k], "value": v} for k, v in data.items() if k in col_map]
    r = requests.post(f"{BASE_URL}/docs/{doc_id}/tables/{table_id}/rows",
                      headers=HEADERS, json={"rows": [{"cells": cells}]}); r.raise_for_status()
    print(f"✅ 행 추가 완료"); return r.json()

# ── 7. 페이지 생성 ────────────────────────
def create_page(doc_id, title, content="", parent_id=None):
    check_token()
    payload = {"name": title, "contentFormat": "markdown", "content": content}
    if parent_id: payload["parentPageId"] = parent_id
    r = requests.post(f"{BASE_URL}/docs/{doc_id}/pages", headers=HEADERS, json=payload)
    r.raise_for_status()
    p = r.json()
    print(f"✅ 페이지 생성!\n   ID: {p.get('id')}\n   이름: {p.get('name')}\n   URL: {p.get('browserLink','')}")
    return p

# ── 8. 페이지 업데이트 ────────────────────
def update_page(doc_id, page_id, new_title=None, new_content=None):
    check_token()
    if new_title:
        r = requests.put(f"{BASE_URL}/docs/{doc_id}/pages/{page_id}",
                         headers=HEADERS, json={"name": new_title}); r.raise_for_status()
        print("✅ 제목 업데이트 완료")
    if new_content:
        r = requests.post(f"{BASE_URL}/docs/{doc_id}/pages/{page_id}/content",
                          headers=HEADERS, json={"content": new_content, "contentFormat": "markdown"})
        print(f"✅ 내용 업데이트 완료" if r.status_code in [200,202] else f"⚠️ {r.status_code}: {r.text[:100]}")

# ── 9. 키워드 검색 ────────────────────────
def search(doc_id, keyword):
    check_token()
    pages = list_pages(doc_id)
    matched = [p for p in pages if keyword.lower() in p["name"].lower()]
    print(f"\n🔍 '{keyword}' 검색 결과: {len(matched)}개")
    for p in matched: print(f"  → {p['name']} (ID: {p['id']})")
    return matched

# ── CLI ───────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "help":
        print("""
Coda Helper 사용법
==================
python3 coda_helper.py list-docs
python3 coda_helper.py list-pages   <doc_id>
python3 coda_helper.py list-tables  <doc_id>
python3 coda_helper.py read-page    <doc_id> <page_id> [output.json]
python3 coda_helper.py read-table   <doc_id> <table_id> [output.json]
python3 coda_helper.py add-row      <doc_id> <table_id> '{"컬럼":"값"}'
python3 coda_helper.py create-page  <doc_id> "제목" "마크다운 내용" [parent_id]
python3 coda_helper.py update-page  <doc_id> <page_id> "새제목" "추가내용"
python3 coda_helper.py search       <doc_id> "키워드"
        """)
    elif args[0] == "list-docs":   list_docs()
    elif args[0] == "list-pages"  and len(args)>=2: list_pages(args[1])
    elif args[0] == "list-tables" and len(args)>=2: list_tables(args[1])
    elif args[0] == "read-page"   and len(args)>=3: read_page(args[1], args[2], args[3] if len(args)>3 else None)
    elif args[0] == "read-table"  and len(args)>=3: read_table(args[1], args[2], output_file=args[3] if len(args)>3 else None)
    elif args[0] == "add-row"     and len(args)>=4: add_row(args[1], args[2], json.loads(args[3]))
    elif args[0] == "create-page" and len(args)>=3: create_page(args[1], args[2], args[3] if len(args)>3 else "", args[4] if len(args)>4 else None)
    elif args[0] == "update-page" and len(args)>=3: update_page(args[1], args[2], args[3] if len(args)>3 else None, args[4] if len(args)>4 else None)
    elif args[0] == "search"      and len(args)>=3: search(args[1], args[2])
    else: print("❌ 알 수 없는 명령어. 'python3 coda_helper.py help' 참조")
