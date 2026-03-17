#!/usr/bin/env python3
"""
OSL Pipeline — .isom Deployment Script

Validates, normalizes, and deploys .isom files from /incoming/ to
/library/by-domain/[domain]/corpus/.

Part of the Structural Extraction Engine for the Open Structure Library.
"""

import hashlib
import os
import re
import shutil
import sys
import unicodedata

INCOMING_DIR = os.path.join(os.path.dirname(__file__), "..", "incoming")
LIBRARY_DIR = os.path.join(os.path.dirname(__file__), "..", "library", "by-domain")

REQUIRED_YAML_FIELDS = ["source_id", "domain", "year", "title"]
VALID_NODE_TYPES = {"Agent", "Event", "Resource", "Intentional Moment"}
NODE_TYPE_PATTERN = re.compile(r"\(.*?:(Type):.*?\)")


def parse_isom(filepath):
    """Parse a .isom file into YAML header dict and DSL body string."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        return None, content

    end = content.find("---", 3)
    if end == -1:
        return None, content

    yaml_section = content[3:end].strip()
    body = content[end + 3:].strip()

    header = {}
    for line in yaml_section.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            header[key.strip()] = value.strip().strip('"').strip("'")

    return header, body


def validate_yaml_header(header, filepath):
    """Check that all required YAML fields are present."""
    if header is None:
        return [f"{filepath}: YAMLヘッダーが見つかりません。"]

    errors = []
    for field in REQUIRED_YAML_FIELDS:
        if field not in header or not header[field]:
            errors.append(
                f"{filepath}: 必須フィールド '{field}' が欠落しています。"
            )
    return errors


def validate_node_types(body, filepath):
    """Validate that DSL node types are within the allowed set."""
    errors = []
    matches = NODE_TYPE_PATTERN.findall(body)
    if not matches:
        return errors

    # Extract actual type values from matches like (NodeName:Type:Agent)
    type_value_pattern = re.compile(r"\(([^)]*?):Type:([^)]*?)\)")
    for match in type_value_pattern.finditer(body):
        node_type = match.group(2).strip()
        if node_type not in VALID_NODE_TYPES:
            errors.append(
                f"{filepath}: 無効なノード型 '{node_type}' が検出されました。"
                f" 許可される型: {', '.join(sorted(VALID_NODE_TYPES))}"
            )
    return errors


def generate_short_hash(source_id, length=8):
    """Generate a short hash from source_id."""
    digest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
    return digest[:length]


def slugify(text):
    """Convert text to lowercase hyphenated slug."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text


def make_short_title(title, max_words=3):
    """Create a short title slug from the first few words."""
    words = re.sub(r"[^\w\s]", "", title).split()
    short = "-".join(words[:max_words])
    return slugify(short)


def check_duplicate(domain_dir, source_id):
    """Check if a file with the same source_id already exists in the target."""
    if not os.path.isdir(domain_dir):
        return False

    for fname in os.listdir(domain_dir):
        if not fname.endswith(".isom"):
            continue
        fpath = os.path.join(domain_dir, fname)
        header, _ = parse_isom(fpath)
        if header and header.get("source_id") == source_id:
            return True
    return False


def deploy_file(filepath):
    """Validate, normalize, and deploy a single .isom file."""
    basename = os.path.basename(filepath)
    print(f"[OSL Pipeline] 処理中: {basename}")

    header, body = parse_isom(filepath)

    # Validation
    errors = []
    errors.extend(validate_yaml_header(header, basename))
    errors.extend(validate_node_types(body, basename))

    if errors:
        return errors

    # Build normalized filename
    source_id = header["source_id"]
    year = header["year"]
    title = header["title"]
    domain = header["domain"]

    short_hash = generate_short_hash(source_id)
    short_title = make_short_title(title)
    new_filename = f"{year}-{short_hash}-{short_title}.isom"

    # Build target directory
    domain_slug = slugify(domain)
    target_dir = os.path.join(LIBRARY_DIR, domain_slug, "corpus")
    os.makedirs(target_dir, exist_ok=True)

    # Duplicate check
    if check_duplicate(target_dir, source_id):
        return [
            f"{basename}: 重複エラー — source_id '{source_id}' は"
            f" 既に {domain_slug}/corpus/ に存在します。"
        ]

    # Move file
    target_path = os.path.join(target_dir, new_filename)
    shutil.copy2(filepath, target_path)
    os.remove(filepath)

    print(f"[OSL Pipeline] 配置完了: {domain_slug}/corpus/{new_filename}")
    return []


def main():
    incoming = os.path.abspath(INCOMING_DIR)
    if not os.path.isdir(incoming):
        print("[OSL Pipeline] incoming/ ディレクトリが見つかりません。")
        sys.exit(1)

    isom_files = sorted(
        f for f in os.listdir(incoming) if f.endswith(".isom")
    )

    if not isom_files:
        print("[OSL Pipeline] 処理対象の .isom ファイルがありません。")
        sys.exit(0)

    all_errors = []
    processed = 0

    for fname in isom_files:
        fpath = os.path.join(incoming, fname)
        errors = deploy_file(fpath)
        if errors:
            all_errors.extend(errors)
        else:
            processed += 1

    print(f"\n[OSL Pipeline] 結果: {processed} 件成功, {len(all_errors)} 件エラー")

    if all_errors:
        print("\n--- バリデーションエラー ---")
        for err in all_errors:
            print(f"  ✗ {err}")
        sys.exit(1)

    print("[OSL Pipeline] すべてのファイルが正常に配置されました。")
    sys.exit(0)


if __name__ == "__main__":
    main()
