from __future__ import annotations

import argparse
import json
import tarfile
from pathlib import Path

from arca.app import build_executive
from arca.assistant import CognitiveAssistant
from arca.benchmark import run
from arca.memory import MemoryStore
from arca.model import Task
from arca.native_lm import ARCALanguageModel


def model_from_args(path: str | None):
    return ARCALanguageModel.load(Path(path)) if path else None


def demo() -> None:
    task = Task("cas", {"expression": "(21 + 21) * 2"}, "Compute a verifiable result")
    print(json.dumps(build_executive().execute(task).to_dict(), indent=2, ensure_ascii=False))


def cmd_benchmark(_args) -> None:
    report = run()
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


def cmd_chat(args) -> None:
    assistant = CognitiveAssistant(args.db, model=model_from_args(args.model))
    print("ARCA cognitive agent. Type 'help' or 'exit'.")
    while True:
        try:
            text = input("arca> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if text.casefold() in {"exit", "quit", "salir"}:
            return
        print(assistant.ask(text)["answer"])


def cmd_ask(args) -> None:
    response = CognitiveAssistant(args.db, model=model_from_args(args.model)).ask(" ".join(args.prompt))
    payload = response if args.trace else {"answer": response["answer"]}
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_export(args) -> None:
    """Bundle the portable memory (SQLite + sessions) into one .arcamem file."""
    db = Path(args.db)
    if not db.exists():
        raise SystemExit(f"memory database not found: {db}")
    target = Path(args.out) if args.out else Path(f"arca-memory-{db.stem}.arcamem")
    with tarfile.open(target, "w:gz") as bundle:
        for suffix in ("", "-wal", "-shm"):
            side = Path(f"{db}{suffix}")
            if side.exists():
                bundle.add(side, arcname=side.name)
        if args.sessions and Path(args.sessions).exists():
            bundle.add(args.sessions, arcname=Path(args.sessions).name)
    print(f"exported memory to {target} ({target.stat().st_size / 1024:.1f} KB)")


def cmd_import(args) -> None:
    source = Path(args.file)
    if not source.exists():
        raise SystemExit(f"archive not found: {source}")
    dest_db = Path(args.db)
    dest_db.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source, "r:gz") as bundle:
        for member in bundle.getmembers():
            stream = bundle.extractfile(member)
            if stream is None:
                continue
            if member.name.endswith(("-wal", "-shm")):
                continue
            dest = dest_db if member.name.endswith(".db") else dest_db.parent / member.name
            dest.write_bytes(stream.read())
    stats = MemoryStore(dest_db).stats()
    print(f"imported memory into {dest_db}: {stats}")


def cmd_index(args) -> None:
    """Bulk-mine cached documents into the evidence graph (disk does the learning)."""
    from arca.graph import EvidenceGraph

    store = MemoryStore(args.db)
    graph = EvidenceGraph(store, max_triples=args.max_triples)
    report = graph.backfill(limit=args.limit)
    pruned = graph.prune_if_needed()
    print(f"indexed {report['documents']} document(s): +{report['triples_added']} triple(s); pruned={pruned}; total={store.stats().get('triples', 0)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="arca")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo").set_defaults(func=demo)
    sub.add_parser("benchmark").set_defaults(func=cmd_benchmark)

    talk = sub.add_parser("chat")
    talk.add_argument("--db", default="arca.db")
    talk.add_argument("--model")
    talk.set_defaults(func=cmd_chat)

    ask = sub.add_parser("ask")
    ask.add_argument("prompt", nargs="+")
    ask.add_argument("--db", default="arca.db")
    ask.add_argument("--model")
    ask.add_argument("--trace", action="store_true")
    ask.set_defaults(func=cmd_ask)

    exporter = sub.add_parser("export")
    exporter.add_argument("--db", default="arca.db")
    exporter.add_argument("--out")
    exporter.add_argument("--sessions")
    exporter.set_defaults(func=cmd_export)

    importer = sub.add_parser("import")
    importer.add_argument("file")
    importer.add_argument("--db", default="arca.db")
    importer.set_defaults(func=cmd_import)

    indexer = sub.add_parser("index")
    indexer.add_argument("--db", default="arca.db")
    indexer.add_argument("--limit", type=int, default=2000)
    indexer.add_argument("--max-triples", type=int, default=500_000)
    indexer.set_defaults(func=cmd_index)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
