"""CLI using the same Markdown retriever, DeepSeek config and citations as FastAPI."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import Settings
from app.rag import KnowledgeRetriever
from app.chat import ChatService


def main():
    parser = argparse.ArgumentParser(description="本草知问 Markdown / Qwen / FAISS RAG")
    parser.add_argument("--rebuild", action="store_true", help="强制重建 Markdown 索引后退出")
    parser.add_argument("--query", help="检索一次并显示来源；不调用云模型")
    args = parser.parse_args()
    settings = Settings.from_env()
    retriever = KnowledgeRetriever(settings)
    documents = retriever.documents()
    if args.rebuild:
        print("正在加载本地嵌入模型并构建索引……", flush=True)
        count = retriever.engine.prepare(documents, force=True)
        print(f"已索引 {len(documents)} 份资料、{count} 个片段。目录：{settings.rag_persist_dir}")
        return
    if args.query:
        for passage in retriever.retrieve(args.query, documents, None):
            print(f"\n[{passage.source['name']}]\n{passage.text}")
        return
    service = ChatService(settings, retriever)
    history = []
    print("本地 RAG 已启动。输入 exit 退出；未配置 DeepSeek 时仅显示原文。")
    while True:
        question = input("\n请输入问题：").strip()
        if question.lower() in {"exit", "quit", "退出"}:
            return
        if not question:
            continue
        # Re-read on each turn so changes/deletions invalidate the index.
        documents = retriever.documents()
        if not settings.deepseek_api_key:
            for passage in retriever.retrieve(question, documents, None):
                print(passage.source["name"], passage.text, sep="\n")
            continue
        answer = service.answer(question, documents, None, history)
        print(answer["title"])
        for section in answer["sections"]:
            print(section["title"], section["content"], sep="\n")
        for index, source in enumerate(answer["sources"], 1):
            print(f"[{index}] {source['name']}\n{source['excerpt']}")
        if answer["mode"] == "generated":
            history = (history + [{"question": answer.get("resolvedQuestion", question)[:500],
                                   "answer": "\n".join(s["content"] for s in answer["sections"])[:1000]}])[-5:]


if __name__ == "__main__":
    main()
