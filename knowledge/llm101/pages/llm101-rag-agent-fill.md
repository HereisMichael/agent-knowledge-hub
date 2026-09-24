---
source_id: llm101-rag-agent-fill
corpus: llm101
type: exercise
topic: fill-in
source_commit: e139bb64be3d8cdbb409c8282ea0b81747084bc9
---

# RAG 与 Agent 填空

## 练习 1: 文本分块策略（Level 2）

### 背景

RAG 第一步是将长文档切分成适合 embedding 的 chunk。chunk 太大引入噪声，太小丢失上下文。本题实现固定大小分块（带 overlap）和按 Markdown 标题的语义分块。

### 任务

```python
import re
from typing import List

def fixed_size_chunk(text: str, chunk_size: int = 200, overlap: int = 50) -> List[str]:
    """固定大小分块，相邻 chunk 有 overlap 个字符重叠。"""
    assert overlap < chunk_size
    chunks = []
    # ===== 填空 1: 计算滑动窗口步长 =====
    step = _____  # 提示: chunk_size - overlap

    # ===== 填空 2: 滑动窗口遍历 =====
    for start in _____:  # 提示: range(0, len(text), step)
        chunk = text[start:start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def semantic_chunk_by_heading(text: str) -> List[dict]:
    """按 Markdown 标题（## / ###）切分，返回 [{"heading": ..., "content": ...}]"""
    chunks = []
    # ===== 填空 3: 按标题行切分，保留分隔符 =====
    parts = re.split(r'(^#{2,3}\s+.+)$', text, flags=_____) # 提示: re.MULTILINE

    current_heading = "(无标题)"
    current_parts = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # ===== 填空 4: 判断是否是标题行 =====
        if re.match(r'_____', part):  # 提示: ^#{2,3}\s+
            if current_parts:
                chunks.append({"heading": current_heading,
                                "content": "\n".join(current_parts)})
                current_parts = []
            current_heading = part
        else:
            current_parts.append(part)
    if current_parts:
        chunks.append({"heading": current_heading,
                        "content": "\n".join(current_parts)})
    return chunks
```

### 提示

- 步长 = `chunk_size - overlap`，保证尾部和下一 chunk 头部重叠 `overlap` 字符
- `re.split` 加捕获组 `()` 保留分隔符，`re.MULTILINE` 让 `^` 匹配每行开头


---

## 练习 2: 余弦相似度与向量检索（Level 2）

### 背景

给定 query embedding 和 document embeddings，用余弦相似度检索 top-k 文档：$\text{sim}(a,b) = \frac{a \cdot b}{\|a\| \|b\|}$

### 任务

```python
import math
from typing import List, Tuple

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算余弦相似度"""
    # ===== 填空 1: 点积 =====
    dot = _____   # 提示: sum(x*y for x,y in zip(a,b))
    # ===== 填空 2: L2 范数 =====
    na = _____    # 提示: math.sqrt(sum(x**2 for x in a))
    nb = math.sqrt(sum(x**2 for x in b))
    if na == 0 or nb == 0:
        return 0.0
    # ===== 填空 3: 余弦相似度 =====
    return _____  # 提示: dot / (na * nb)


def topk_retrieval(query_emb, doc_embs, doc_texts, k=3):
    """检索 top-k 最相似文档，返回 [(index, score, text), ...]"""
    scores = []
    for i, emb in enumerate(doc_embs):
        # ===== 填空 4: 计算相似度 =====
        sim = _____  # 提示: cosine_similarity(query_emb, emb)
        scores.append((i, sim, doc_texts[i]))
    # ===== 填空 5: 按相似度降序取 top-k =====
    scores.sort(key=lambda x: _____, reverse=True)  # 提示: x[1]
    return scores[:k]


class SimpleInvertedIndex:
    """倒排索引，用于向量检索前的粗筛"""
    def __init__(self):
        self.index = {}  # word -> set of doc_ids

    def add_document(self, doc_id: int, text: str):
        for word in text.lower().split():
            # ===== 填空 6: 建立倒排映射 =====
            if word not in self.index:
                self.index[word] = _____  # 提示: set()
            _____  # 提示: self.index[word].add(doc_id)

    def search(self, query: str) -> List[int]:
        # ===== 填空 7: 合并匹配文档集合 =====
        result = _____  # 提示: set()
        for w in query.lower().split():
            if w in self.index:
                result = _____  # 提示: result | self.index[w]
        return sorted(result)
```

### 提示

- 余弦相似度范围 [-1, 1]，注意零向量边界
- 倒排索引在向量检索前做粗筛可大幅减少计算量


---

## 练习 3: RAG Pipeline 端到端（Level 3）

### 背景

完整 RAG 流程：分块 -> embedding -> 检索 -> prompt 组装 -> 生成。本题将前两练的组件串联成 pipeline，用 mock LLM 替代 API。

### 任务

```python
import random, math
from typing import List, Dict

def mock_embedding(text: str, dim: int = 32) -> List[float]:
    """用哈希生成伪 embedding，相同文本返回相同向量"""
    random.seed(hash(text) % (2**31))
    return [random.gauss(0, 1) for _ in range(dim)]

def mock_llm(prompt: str) -> str:
    if "[上下文]" in prompt:
        s = prompt.index("[上下文]") + 6
        e = prompt.index("[问题]") if "[问题]" in prompt else len(prompt)
        return f"根据资料，{prompt[s:e].strip()[:80]}..."
    return "无法回答。"

class SimpleRAG:
    def __init__(self, chunk_size=200, overlap=50, top_k=3,
                 max_context_length=500):
        self.chunk_size, self.overlap = chunk_size, overlap
        self.top_k = top_k
        self.max_context_length = max_context_length
        self.chunks, self.embeddings, self.sources = [], [], []

    def add_document(self, text: str, source: str = "unknown"):
        step = self.chunk_size - self.overlap
        for start in range(0, len(text), step):
            chunk = text[start:start + self.chunk_size]
            if chunk.strip():
                self.chunks.append(chunk)
                self.embeddings.append(mock_embedding(chunk))
                self.sources.append(source)

    def retrieve(self, query: str) -> List[Dict]:
        qe = mock_embedding(query)
        scored = []
        for i, emb in enumerate(self.embeddings):
            dot = sum(a*b for a,b in zip(qe, emb))
            na = math.sqrt(sum(a**2 for a in qe))
            nb = math.sqrt(sum(b**2 for b in emb))
            sim = dot/(na*nb) if na and nb else 0
            scored.append({"index": i, "score": sim,
                           "text": self.chunks[i], "source": self.sources[i]})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:self.top_k]

    def build_prompt(self, query: str, retrieved: List[Dict]) -> str:
        ctx_parts, total = [], 0
        for item in retrieved:
            # ===== 填空 1: 添加来源标注 =====
            piece = f"[来源: {_____}]\n{item['text']}"  # 提示: item["source"]
            # ===== 填空 2: max_context_length 截断 =====
            if total + len(piece) > _____:  # 提示: self.max_context_length
                break
            ctx_parts.append(piece)
            total += len(piece)
        context = "\n\n".join(ctx_parts)
        # ===== 填空 3: 组装 prompt =====
        prompt = _____
        # 提示: f"请根据上下文回答。\n\n[上下文]\n{context}\n\n[问题]\n{query}"
        return prompt

    def query(self, question: str) -> Dict:
        retrieved = self.retrieve(question)
        prompt = self.build_prompt(question, retrieved)
        return {"answer": mock_llm(prompt), "sources": [r["source"] for r in retrieved],
                "prompt": prompt}
```

### 提示

- 来源标注让用户追溯答案出处，是 RAG 的关键特性
- `max_context_length` 防止超出 LLM 上下文窗口


---

## 练习 4: ReAct Agent 循环（Level 2-3）

### 背景

ReAct = Reason + Act，Agent 在 Thought -> Action -> Observation 循环中解决问题，直到输出 Final Answer。

### 任务

```python
import re
from typing import Dict, Callable

# 三个 mock 工具
def calculator(expr: str) -> str:
    try:
        return str(eval(expr))  # 生产环境应用 ast.literal_eval
    except Exception as e:
        return f"错误: {e}"

def search(query: str) -> str:
    db = {"中国人口": "约 14.1 亿", "地球月球距离": "约 384400 公里"}
    for k, v in db.items():
        if k in query:
            return v
    return f"未找到 '{query}' 的结果"

def get_weather(city: str) -> str:
    db = {"北京": "晴 25度", "上海": "多云 22度", "深圳": "小雨 28度"}
    return db.get(city, f"无 {city} 天气数据")

# Mock LLM: 预设多步 ReAct 输出
def mock_react_llm(history: str, step: int) -> str:
    if step == 0:
        return ("Thought: 先查天气。\n"
                "Action: get_weather\nAction Input: 北京")
    elif step == 1:
        return ("Thought: 天气已知，算数学题。\n"
                "Action: calculator\nAction Input: 25 * 3 + 10")
    else:
        return ("Thought: 信息齐全。\n"
                "Final Answer: 北京晴天 25 度，25*3+10=85。")


class ReActAgent:
    def __init__(self, tools: Dict[str, Callable], max_steps: int = 10):
        self.tools = tools
        self.max_steps = max_steps

    def parse_action(self, llm_output: str) -> dict:
        # ===== 填空 1: 检测 Final Answer =====
        if _____ in llm_output:  # 提示: "Final Answer:"
            ans = llm_output.split("Final Answer:")[-1].strip()
            return {"type": "final_answer", "answer": ans}

        # ===== 填空 2: 解析 Action / Action Input =====
        a = re.search(r'Action:\s*(.+)', llm_output)
        ai = re.search(r'Action Input:\s*(.+)', llm_output)
        if a and ai:
            return {"type": "action",
                    "action": _____,        # 提示: a.group(1).strip()
                    "action_input": _____}   # 提示: ai.group(1).strip()
        return {"type": "error"}

    def execute_tool(self, action: str, action_input: str) -> str:
        # ===== 填空 3: 调用对应工具 =====
        if action in _____:  # 提示: self.tools
            return _____     # 提示: self.tools[action](action_input)
        return f"未知工具: {action}"

    def run(self, question: str) -> dict:
        history = f"Question: {question}\n"
        steps = []
        for step in range(self.max_steps):
            out = mock_react_llm(history, step)
            parsed = self.parse_action(out)

            # ===== 填空 4: 终止条件 =====
            if parsed["type"] == "final_answer":
                steps.append({"step": step, "output": out})
                return {"answer": _____,  # 提示: parsed["answer"]
                        "steps": steps, "num_steps": step + 1}

            if parsed["type"] == "action":
                obs = self.execute_tool(parsed["action"], parsed["action_input"])
                steps.append({"step": step, "action": parsed["action"],
                              "input": parsed["action_input"], "observation": obs})
                # ===== 填空 5: 追加到 history =====
                history += f"\n{out}\nObservation: {_____}\n"  # 提示: obs

        return {"answer": "达到最大步数", "steps": steps,
                "num_steps": self.max_steps}
```

### 提示

- `Final Answer:` 是终止信号，检测到立即返回
- history 累积保证后续步骤能看到之前的推理链
- 正则 `r'Action:\s*(.+)'` 可灵活匹配不同格式


---

## 练习 5: 结构化 Tool Calling（Level 3）

### 背景

现代 LLM 支持结构化 function calling / tool_use，比 ReAct 文本解析更可靠。核心：用 JSON Schema 定义工具 -> LLM 返回 tool_calls JSON -> 解析并调用 -> 多轮交互。

### 任务

```python
import json, inspect
from typing import Callable, Dict, List, get_type_hints

TYPE_MAP = {int: "integer", float: "number", str: "string",
            bool: "boolean", list: "array", dict: "object"}

def function_to_tool_schema(func: Callable) -> dict:
    """将 Python 函数自动转换为 JSON Schema 格式的 tool 定义"""
    # ===== 填空 1: 提取函数名和描述 =====
    name = _____  # 提示: func.__name__
    desc = (func.__doc__ or "").strip().split("\n")[0]

    sig = inspect.signature(func)
    hints = get_type_hints(func)
    properties, required = {}, []
    for pname, param in sig.parameters.items():
        ptype = hints.get(pname, str)
        properties[pname] = {"type": TYPE_MAP.get(ptype, "string"),
                             "description": f"参数 {pname}"}
        # ===== 填空 2: 无默认值则加入 required =====
        if param.default is _____:  # 提示: inspect.Parameter.empty
            required.append(pname)

    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": properties,
                        "required": required}}}


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.schemas: List[dict] = []

    def register(self, func: Callable):
        self.tools[func.__name__] = func
        self.schemas.append(function_to_tool_schema(func))
        return func

    def execute_tool_call(self, tool_call: dict) -> dict:
        cid = tool_call["id"]
        fname = tool_call["function"]["name"]
        # ===== 填空 3: 解析 arguments =====
        args = _____  # 提示: json.loads(tool_call["function"]["arguments"])
        if fname not in self.tools:
            return {"id": cid, "error": f"未知工具: {fname}"}
        # ===== 填空 4: 调用函数 =====
        func = _____  # 提示: self.tools[fname]
        try:
            return {"id": cid, "result": str(_____)}  # 提示: func(**args)
        except Exception as e:
            return {"id": cid, "error": str(e)}


# Mock LLM: 模拟多轮 tool calling
def mock_tc_llm(messages, schemas, step):
    if step == 0:
        return {"role": "assistant", "content": None, "tool_calls": [
            {"id": "c1", "function": {"name": "get_population",
             "arguments": json.dumps({"country": "中国"})}},
            {"id": "c2", "function": {"name": "get_area",
             "arguments": json.dumps({"country": "中国"})}}]}
    elif step == 1:
        return {"role": "assistant", "content": None, "tool_calls": [
            {"id": "c3", "function": {"name": "compute_density",
             "arguments": json.dumps({"population": 1410000000,
                                       "area_km2": 9600000})}}]}
    return {"role": "assistant", "tool_calls": [],
            "content": "中国人口约 14.1 亿，面积约 960 万 km2，密度约 146.88 人/km2。"}


def run_tool_calling_loop(question: str, registry: ToolRegistry,
                          max_rounds: int = 5) -> dict:
    messages = [{"role": "user", "content": question}]
    all_results = []

    for step in range(max_rounds):
        resp = mock_tc_llm(messages, registry.schemas, step)
        messages.append(resp)
        tc = resp.get("tool_calls", [])

        # ===== 填空 5: 无 tool_calls 则返回最终回答 =====
        if not _____:  # 提示: tc (空列表为 falsy)
            return {"answer": resp["content"],
                    "tool_calls_made": all_results, "num_rounds": step + 1}

        # ===== 填空 6: 执行所有 tool calls =====
        for t in tc:
            res = _____  # 提示: registry.execute_tool_call(t)
            all_results.append(res)
            # ===== 填空 7: 工具结果追加到消息历史 =====
            messages.append({"role": "tool",
                             "tool_call_id": _____,  # 提示: t["id"]
                             "content": json.dumps(res, ensure_ascii=False)})

    return {"answer": "达到最大轮数", "tool_calls_made": all_results,
            "num_rounds": max_rounds}
```

### 提示

- `inspect.Parameter.empty` 表示参数无默认值
- `json.loads` 将 JSON 字符串解析为 dict，`func(**args)` 解包为关键字参数
- 每个 tool result 必须带 `tool_call_id` 与对应请求关联


---

## 参考来源

[docs/exercises/rag-agent-fill.md](https://github.com/boots-coder/LLM-101-CN/blob/e139bb64be3d8cdbb409c8282ea0b81747084bc9/docs/exercises/rag-agent-fill.md)
