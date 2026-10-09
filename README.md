# xeno-bdat-hash

独立保存 XB3 / XBX 的 BDAT hash 映射，CSV 每行格式为 `8位十六进制HASH,字符串`。

## 填入已解明的字符串

需要 Python 3，无需安装第三方库。

```bash
./fill-hash.py 'BTL_Arts_Combine'
./fill-hash.py '字符串一' '字符串二'
```

脚本按 UTF-8 字节计算 MurmurHash3 x86_32（seed 为 0），默认查找脚本所在目录的 `xb3_hashes.all.csv` 和 `xbx_hashes.all.csv`。从其他目录运行脚本也可以。

- 找到匹配 hash 且字符串为空：填入字符串。
- 已有相同字符串：跳过。
- 已有不同字符串，或输入的多个字符串 hash 冲突：报错，本次不写入任何文件。
- 没有匹配行：显示 hash，不新增行。全部未匹配时退出码为 1。

先预览，或只处理指定文件：

```bash
./fill-hash.py --dry-run 'BTL_Arts_Combine'
./fill-hash.py --file xb3_hashes.all.csv 'BTL_Arts_Combine'
```

`--file` 可以重复使用，其相对路径基于执行命令时的工作目录。字符串区分大小写，空格不会被裁剪；包含空格、逗号或引号时应使用 shell 引号，CSV 字段会自动转义。不支持空字符串或换行符。字符串以 `-` 开头时，在参数前添加 `--`。
