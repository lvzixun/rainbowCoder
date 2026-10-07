"""One-time, idempotent migration of the original blog Markdown."""
import json
import re
import subprocess
from pathlib import Path

METADATA = {
    'aoi': ('AOI：从事件通知到快照差异', '重新思考 AOI 的更新方式，用快照与差异计算减少重复通知和性能开销。', ['游戏服务端', '性能优化']),
    'clang_plugin_of_sublime': ('Sublime Text 的 Clang 补全插件', '为 Sublime Text 实现 Clang 自动补全，从 libclang 接口到插件的实践记录。', ['编译器', '工具']),
    'collision': ('基于四叉树的碰撞检查', '用四叉树重构碰撞检测，记录对象管理、查询裁剪和实现中的优化细节。', ['游戏服务端', '性能优化']),
    'elf': ('获取 static 函数名称', '从 Lua 调用栈和火焰图出发，通过 ELF 符号表查找 static 函数的名称。', ['工具', 'Lua']),
    'helloWorld': ('Hello world', 'To the very best time. My friends. ;)', ['随笔']),
    'lua_5_3_5_gc': ('Lua 5.3.5 GC 实现', '阅读 Lua 垃圾回收源码，梳理三色标记、增量回收、弱引用与各阶段的实现。', ['Lua', 'GC']),
    'lua_5_4_2_stacksize': ('Lua 5.4.2 stacksize 产生的 bug', '一次元方法返回 nil 的排查：追踪 Lua 栈大小调整与尾调用之间的问题。', ['Lua']),
    'lua_5_4_gc': ('Lua 5.4 GC 实现', '从对象年龄、链表组织到分代回收流程，记录 Lua 5.4 垃圾回收的变化。', ['Lua', 'GC']),
    'rainbowcoder': ('rainbowCoder 的诞生', '第一次搭起自己的 Markdown 博客，记录写作和发布流程背后的折腾与乐趣。', ['随笔']),
    'rainbowcoder_rss': ('给博客添加 RSS', '用 Lua 为手写博客生成 RSS，探索订阅源的格式和工作方式。', ['工具', '随笔']),
    'regex': ('正则表达式的实现', '从语法树、NFA 到 DFA，实现一个正则引擎，并重新思考不同执行方式的取舍。', ['编译器']),
    'sproto_jit': ('为 sproto 添加 JIT', '尝试用 DynASM 为 sproto 协议解析生成机器码，记录实现思路与性能表现。', ['Lua', '性能优化']),
    'zxml': ('Zero-copy 的 XML 解析器', '从 Excel XML 导表的性能问题出发，尝试实现一个零拷贝的 XML 解析器。', ['工具', '性能优化']),
}

for path in sorted(Path('post').glob('*.md')):
    source = path.read_text()
    if source.startswith('---\n'):
        continue
    title, description, tags = METADATA[path.stem]
    dates = subprocess.check_output(['git', 'log', '--follow', '--format=%aI', '--', str(path)], text=True).splitlines()
    published, updated = dates[-1][:10], dates[0][:10]
    meta = ['---', f'title: {json.dumps(title, ensure_ascii=False)}', f'date: {published}']
    if updated != published:
        meta.append(f'updated: {updated}')
    meta.extend([f'description: {json.dumps(description, ensure_ascii=False)}', f'tags: {json.dumps(tags, ensure_ascii=False)}', '---', ''])
    source = re.sub(r'^\s*#+\s+[^\n]*\n', '', source, count=1).lstrip('\n')
    source = re.sub(r'^(\s*(?:~{3,}|`{3,}))\.(c|lua|diff)\s*$', r'\1\2', source, flags=re.M)
    source = re.sub(r'\((?:https?://)?(?:www\.)?rainbowcoder\.com([^\s)]*)\)', lambda m: '(' + (m[1] or '/') + ')', source)
    path.write_text('\n'.join(meta) + '\n' + source)
    print(f'Migrated {path}: {published}')

# The old title was usually H2, so its sections started at H3/H4.
# Promote only real Markdown headings, preserving code fences and code content.
for path in sorted(Path('post').glob('*.md')):
    lines = path.read_text().splitlines(keepends=True)
    indices = []
    fence = None
    for index, line in enumerate(lines):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            if fence is None:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = None
            continue
        if fence is None:
            heading = re.match(r'^(#{2,6})\s+', line)
            if heading:
                indices.append((index, len(heading[1])))
    if indices:
        shift = min(depth for _, depth in indices) - 2
        if shift > 0:
            for index, _ in indices:
                lines[index] = lines[index][shift:]
            path.write_text(''.join(lines))
