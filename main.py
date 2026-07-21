from agent import config
from agent.graph import build_graph


def main():
    config.validate()
    graph = build_graph()
    result = graph.invoke({})

    draft = result["draft"]
    print(f"\nGenerated post: {draft.topic}")
    print(f"Words: {draft.word_count}")
    print(f"\nSaved to:")
    print(f"  {config.OUTPUT_DIR}/draft.json")
    print(f"  {config.OUTPUT_DIR}/preview.html  <- open this in a browser")


if __name__ == "__main__":
    main()
