from phame.rag_utils.query_rag import run_query
from phame.rag_utils.build_rag import load_config

from phame.llm.generation_chain import generation_with_query_top_k
from argparse import ArgumentParser
import os
from langchain_openai import ChatOpenAI


def main():
    parser = ArgumentParser(prog="generate_part", description="Generate a parametric part with past work.")
    parser.add_argument('-d', '--description', type=str, help='Provide a description of the item')
    parser.add_argument('-o', '--output', type=str, help='Output filename')
    parser.add_argument('-k', '--top_k', type=int, help='Top k results for RAG', default=None)
    parser.add_argument('-m', '--model', type=str, help='Model name', default=None)
    parser.add_argument('-c', '--config', type=str, help='Config File', default=None)
    parser.add_argument('-p', "--persist_dir", type=str, default=None)
    parser.add_argument("--collection", type=str, default=None)
    args = parser.parse_args()

    # load config
    config = load_config(args.config)
    if args.top_k:
        config["retrieval"]["top_k"] = args.top_k

    if args.model:
        config["retrieval"]["llm"] = args.model

    if args.persist_dir:
        config["chroma"]["persist_dir"] = args.persist_dir

    if args.collection:
        config["chroma"]["collection"] = args.collection

    model = config['retrieval']['llm']
    top_k = config["retrieval"]["top_k"]
    persist_dir = config["chroma"]["persist_dir"]
    collection = config["chroma"]["collection"]
    output = args.output
    description = args.description

    api_key = os.environ['PORTKEY_API_KEY']
    base_url = os.environ['PORTKEY_BASE_URL']

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        # temperature=0.3,
    )


    chain = generation_with_query_top_k(llm, top_k)

    # run rag query
    res = run_query(description, config)

    chain_dict = {
        **{
            f"Description_{i}": res['metadatas'][0][i]['beginner_description']
            for i in range(top_k)
        },
        **{
            f"Code_{i}": res['metadatas'][0][i]['cad_query_code']
            for i in range(top_k)

        }
                  }

    chain_dict['Description_Part'] = description

    spec = chain.invoke(chain_dict)

    print(spec['title'],'\n')

    print(spec['rationale'],'\n')

    lines = spec['cad_code']
    print(lines)

    with open(output, "w") as fp:
        title = "## " + spec['title']
        fp.write(title + '\n')

        fp.write("## Based on \n")
        for i in range(top_k):
            text =  "## CQ/" + res['metadatas'][0][i]['id']
            fp.write(text + "\n")

        rationale = "## " + spec['rationale'].replace('\n', '\n## ')
        fp.write(rationale + '\n')


        fp.write(lines)


if __name__=="__main__":
    main()