#!/usr/bin/env python3
import argparse
import csv
import io
import os
from pathlib import Path
import stat
import sys
import tempfile


def murmur32(value):
    """BDAT MurmurHash3 x86_32, seed 0, over UTF-8 bytes."""
    data = value.encode("utf-8")
    mask = 0xFFFFFFFF
    result = 0
    full_length = len(data) // 4 * 4
    for offset in range(0, full_length, 4):
        block = int.from_bytes(data[offset : offset + 4], "little")
        block = block * 0xCC9E2D51 & mask
        block = (block << 15 | block >> 17) & mask
        block = block * 0x1B873593 & mask
        result ^= block
        result = (result << 13 | result >> 19) & mask
        result = (result * 5 + 0xE6546B64) & mask
    if full_length < len(data):
        block = int.from_bytes(data[full_length:], "little")
        block = block * 0xCC9E2D51 & mask
        block = (block << 15 | block >> 17) & mask
        result ^= block * 0x1B873593 & mask
    result ^= len(data)
    result ^= result >> 16
    result = result * 0x85EBCA6B & mask
    result ^= result >> 13
    result = result * 0xC2B2AE35 & mask
    result ^= result >> 16
    return f"{result:08X}"


def main():
    repo_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        prog="fill-hash.py",
        description="将已解明的字符串填入匹配 hash 的空行；默认查找脚本目录下两份 CSV。",
    )
    parser.add_argument("--dry-run", action="store_true", help="预览匹配结果，不写文件")
    parser.add_argument("--file", action="append", type=Path, help="只查找指定 CSV，可重复使用")
    parser.add_argument("strings", nargs="+", help="已解明的字符串，包含空格时请加引号")
    args = parser.parse_args()
    files = args.file or [
        repo_dir / "xb3_hashes.all.csv",
        repo_dir / "xbx_hashes.all.csv",
    ]
    files = list(dict.fromkeys(file.resolve() for file in files))
    candidates = {}
    for value in args.strings:
        if not value or "\n" in value or "\r" in value:
            parser.error("字符串不能为空或包含换行符")
        key = murmur32(value)
        if key in candidates and candidates[key] != value:
            parser.error(f"参数 hash 冲突：{key} 对应 {candidates[key]!r} 和 {value!r}")
        candidates[key] = value

    pending = []
    matched = set()
    conflicts = []
    # Check every target before writing so a conflict cannot cause partial fills.
    for file in files:
        original = file.read_bytes()
        lines = original.splitlines(keepends=True)
        changed = False
        for index, line in enumerate(lines):
            raw_key, separator, _ = line.partition(b",")
            key = raw_key.decode("ascii", errors="replace").upper()
            if not separator or key not in candidates:
                continue
            row = next(csv.reader([line.decode("utf-8")], strict=True))
            if len(row) != 2:
                raise ValueError(f"{file}:{index + 1} 应为两列 CSV")
            value = candidates[key]
            matched.add(key)
            location = f"{file.name}:{index + 1}"
            if row[1] == value:
                print(f"已有相同值 {location} {key},{value}")
                continue
            if row[1]:
                conflicts.append(f"{location} {key}: 已有 {row[1]!r}，输入 {value!r}")
                continue
            ending = (
                "\r\n"
                if line.endswith(b"\r\n")
                else "\n" if line.endswith(b"\n") else ""
            )
            output = io.StringIO(newline="")
            csv.writer(output, lineterminator="\n").writerow([row[0], value])
            lines[index] = (output.getvalue()[:-1] + ending).encode("utf-8")
            changed = True
            print(f"{'预览填入' if args.dry_run else '待填入'} {location} {key},{value}")
        if changed:
            pending.append((file, original, b"".join(lines)))

    for key, value in candidates.items():
        if key not in matched:
            print(f"未找到匹配行 {key},{value}")
    if conflicts:
        for conflict in conflicts:
            print(f"冲突：{conflict}", file=sys.stderr)
        print("未写入任何文件。", file=sys.stderr)
        return 1
    if not args.dry_run:
        for file, original, replacement in pending:
            # Preserve all untouched bytes and permissions; replace each file atomically.
            if file.read_bytes() != original:
                raise ValueError(f"文件在检查期间发生变化：{file}")
            descriptor, temporary = tempfile.mkstemp(
                prefix=f".{file.name}.", dir=file.parent
            )
            try:
                with os.fdopen(descriptor, "wb") as output:
                    output.write(replacement)
                    os.fchmod(output.fileno(), stat.S_IMODE(file.stat().st_mode))
                os.replace(temporary, file)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            print(f"已更新 {file}")
    return 0 if matched else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, csv.Error) as error:
        print(f"错误：{error}", file=sys.stderr)
        sys.exit(1)
