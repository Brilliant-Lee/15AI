"""
RAG Demo — 本地 Embedding + Rerank 全流程演示
=============================================

流程：
  文档分块 → Embedding(Bi-encoder) → FAISS建索引
  → 向量检索Top-K → Rerank(Cross-encoder) → LLM生成回答

模型（首次运行自动下载到 ./models/ 目录）：
  Embedding : all-MiniLM-L6-v2         ~22MB
  Rerank    : cross-encoder/ms-marco-MiniLM-L-6-v2  ~84MB
  LLM       : Claude Haiku（需要 .env 中配置 ANTHROPIC_API_KEY）
"""

import os
import re
import sys
import numpy as np
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent          # rag_demo/
MODEL_DIR  = SCRIPT_DIR / "models"          # rag_demo/models/
KB_FILE    = SCRIPT_DIR / "rag_knowledge.md"

MODEL_DIR.mkdir(exist_ok=True)

# ── 测试 Query（可改成你想问的任何问题）────────────────────────
QUERY = "天猫渠道的客单价和毛利情况怎么样？"
TOP_K_RETRIEVE = 10   # 向量检索召回数量
TOP_K_RERANK   = 3    # Rerank 后保留数量


# ══════════════════════════════════════════════════════════════
# Step 1：读取知识库并分块
# ══════════════════════════════════════════════════════════════
def load_and_chunk(filepath: Path) -> list[dict]:
    """
    按 Markdown 二级标题（## ）切分文档，每个段落作为一个 chunk。
    实际项目中可按字符数固定窗口切分，或用 langchain TextSplitter。
    """
    text = filepath.read_text(encoding="utf-8")

    # 用 "## " 分割段落，保留标题
    sections = re.split(r"\n(?=## )", text.strip())

    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        # 提取标题和正文
        lines = section.split("\n", 1)
        title = lines[0].lstrip("#").strip()
        body  = lines[1].strip() if len(lines) > 1 else ""
        chunks.append({
            "id"   : i,
            "title": title,
            "text" : section,          # 完整文本（含标题），送给模型
            "body" : body,             # 正文部分，用于展示
        })
    return chunks


# ══════════════════════════════════════════════════════════════
# Step 2 & 3：加载 Embedding 模型，对所有 chunks 编码
# ══════════════════════════════════════════════════════════════
def build_embeddings(chunks: list[dict]):
    """
    Bi-encoder 原理：
      - 文档和 Query 分别独立编码成向量
      - 相似度 = 两向量的余弦相似度（内积，归一化后等价）
      - 优点：文档向量可离线预计算，检索速度 O(1)（FAISS近似检索）
      - 缺点：无法捕捉 Query 和文档的细粒度交互，精度有上限
    """
    from sentence_transformers import SentenceTransformer

    print(f"  加载 Embedding 模型 → {MODEL_DIR}")
    embedder = SentenceTransformer(
        "all-MiniLM-L6-v2",
        cache_folder=str(MODEL_DIR),
    )

    texts = [c["text"] for c in chunks]
    print(f"  对 {len(texts)} 个 chunks 做 Embedding...")
    embeddings = embedder.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    print(f"\n  向量维度: {embeddings.shape}  → (chunk数量, 向量维度)")
    print(f"  第 0 个 chunk 前 8 个维度: {embeddings[0][:8].round(4)}")
    print("  （每个数字代表文本在该语义维度上的强度，人类无法直接解读）")

    return embedder, embeddings


# ══════════════════════════════════════════════════════════════
# Step 4：FAISS 建索引
# ══════════════════════════════════════════════════════════════
def build_faiss_index(embeddings: np.ndarray):
    """
    FAISS IndexFlatIP：精确内积检索（Inner Product）。
    先对向量做 L2 归一化，内积即等于余弦相似度（值域 [-1, 1]）。
    生产场景可换用 IndexIVFFlat 做近似检索，百万级数据仍快。
    """
    import faiss

    dim = embeddings.shape[1]          # 384
    emb = embeddings.copy().astype("float32")
    faiss.normalize_L2(emb)            # 归一化：向量模长 → 1

    index = faiss.IndexFlatIP(dim)
    index.add(emb)

    print(f"  索引已建立，共 {index.ntotal} 个向量，维度 {dim}")
    return index, emb


# ══════════════════════════════════════════════════════════════
# Step 5：向量检索（Retrieve Top-K）
# ══════════════════════════════════════════════════════════════
def retrieve(query: str, embedder, index, chunks: list[dict], top_k: int):
    """
    Query → Embedding → 归一化 → FAISS.search → 返回 Top-K chunks
    """
    import faiss

    q_emb = embedder.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(q_emb)

    scores, indices = index.search(q_emb, top_k)   # shape: (1, top_k)

    results = []
    for rank, (idx, score) in enumerate(zip(indices[0], scores[0]), 1):
        results.append({
            "rank"  : rank,
            "score" : float(score),
            "chunk" : chunks[idx],
        })
    return results


# ══════════════════════════════════════════════════════════════
# Step 6：Rerank（Cross-encoder）
# ══════════════════════════════════════════════════════════════
def rerank(query: str, candidates: list[dict], top_k: int):
    """
    Cross-encoder 原理：
      - Query 和候选文档拼接后一起送入模型，模型直接输出相关性分数
      - 优点：能捕捉 Query 与文档的细粒度交互，精度显著高于 Bi-encoder
      - 缺点：每次查询都要对所有候选文档重新推理，复杂度 O(n)，不适合全量检索
      - 实践：先用 Bi-encoder 从全量文档召回 Top-50，再用 Cross-encoder 精排 Top-3
    """
    from sentence_transformers import CrossEncoder

    print(f"  加载 Rerank 模型 → {MODEL_DIR}")
    reranker = CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        cache_folder=str(MODEL_DIR),
    )

    pairs  = [(query, c["chunk"]["text"]) for c in candidates]
    scores = reranker.predict(pairs)   # 原始 logit，越高越相关

    # 将分数附加到 candidates 并重新排序
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)

    reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
    return reranked[:top_k]


# ══════════════════════════════════════════════════════════════
# Step 7：调用 Claude Haiku 生成最终回答（可选）
# ══════════════════════════════════════════════════════════════
def generate_answer(query: str, top_chunks: list[dict]) -> str | None:
    """
    将 Top-K chunks 拼成上下文，让 Claude Haiku 根据上下文回答问题。
    如果没有 ANTHROPIC_API_KEY，跳过此步。
    """
    # 加载 .env（从项目根目录，即 rag_demo 的父目录）
    env_path = SCRIPT_DIR.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("  （未检测到 ANTHROPIC_API_KEY，跳过 LLM 生成步骤）")
        return None

    import anthropic

    context = "\n\n---\n\n".join(
        f"[{i+1}] {c['chunk']['title']}\n{c['chunk']['body']}"
        for i, c in enumerate(top_chunks)
    )

    prompt = f"""你是一个电商业务分析助手。请根据以下知识库内容回答用户问题。
只使用知识库中的信息，不要凭空推测。如果知识库中没有相关信息，请明确说明。

【知识库内容】
{context}

【用户问题】
{query}"""

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ══════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════
def main():
    SEP = "=" * 60

    # ── Step 1：分块 ──────────────────────────────────────────
    print(f"\n{SEP}")
    print("Step 1：读取知识库并分块")
    print(SEP)
    chunks = load_and_chunk(KB_FILE)
    print(f"  知识库文件: {KB_FILE.name}")
    print(f"  共切分为 {len(chunks)} 个 chunks")
    for c in chunks:
        print(f"  [{c['id']:2d}] {c['title'][:30]}  ({len(c['text'])} 字)")

    # ── Step 2 & 3：Embedding ─────────────────────────────────
    print(f"\n{SEP}")
    print("Step 2 & 3：Embedding（Bi-encoder，all-MiniLM-L6-v2）")
    print(SEP)
    embedder, embeddings = build_embeddings(chunks)

    # ── Step 4：FAISS 建索引 ──────────────────────────────────
    print(f"\n{SEP}")
    print("Step 4：FAISS 建索引（IndexFlatIP + L2归一化）")
    print(SEP)
    index, normed_embs = build_faiss_index(embeddings)

    # ── Step 5：向量检索 ──────────────────────────────────────
    print(f"\n{SEP}")
    print(f"Step 5：向量检索 Top-{TOP_K_RETRIEVE}")
    print(SEP)
    print(f"  Query: 「{QUERY}」\n")
    retrieved = retrieve(QUERY, embedder, index, chunks, TOP_K_RETRIEVE)
    for r in retrieved:
        print(f"  #{r['rank']:2d}  score={r['score']:.4f}  [{r['chunk']['title']}]")

    # ── Step 6：Rerank ────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"Step 6：Rerank（Cross-encoder）→ 精排取 Top-{TOP_K_RERANK}")
    print(SEP)
    reranked = rerank(QUERY, retrieved, TOP_K_RERANK)

    print(f"\n  Rerank 后 Top-{TOP_K_RERANK}（括号内为检索阶段原始排名）：")
    for i, r in enumerate(reranked, 1):
        print(f"  #{i}  rerank_score={r['rerank_score']:.4f}  "
              f"（检索排名 #{r['rank']}）  [{r['chunk']['title']}]")

    print("\n  ┌─ Rerank 价值说明 ───────────────────────────────────────┐")
    print("  │ 向量检索靠语义相似度，擅长广度召回；                    │")
    print("  │ Cross-encoder 联合建模 Query+文档，精排效果更准。        │")
    print("  │ 两阶段组合：召回快（O(logn)）+ 精排准（O(top_k)）       │")
    print("  └─────────────────────────────────────────────────────────┘")

    print(f"\n  最终送入 LLM 的上下文（Top-{TOP_K_RERANK}）：")
    for i, r in enumerate(reranked, 1):
        print(f"\n  [{i}] {r['chunk']['title']}")
        print(f"  {r['chunk']['body'][:100]}...")

    # ── Step 7：LLM 生成回答 ──────────────────────────────────
    print(f"\n{SEP}")
    print("Step 7：LLM 生成回答（Claude Haiku）")
    print(SEP)
    answer = generate_answer(QUERY, reranked)
    if answer:
        print(f"\n  Query: 「{QUERY}」\n")
        print("  ── 回答 ──────────────────────────────────────────────────")
        print(f"  {answer}")
        print("  ─────────────────────────────────────────────────────────")

    print(f"\n{SEP}")
    print("RAG Demo 完成！")
    print(SEP)
    print("""
  整体流程回顾：
    文档分块  →  Embedding(Bi-encoder)  →  FAISS索引
        ↓
    Query Embedding  →  向量检索 Top-10（毫秒级）
        ↓
    Cross-encoder Rerank  →  精排 Top-3（百毫秒级）
        ↓
    LLM 根据 Top-3 上下文生成回答
""")


if __name__ == "__main__":
    main()
