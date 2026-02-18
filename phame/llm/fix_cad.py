from phame.rag_utils.query_rag import run_query
from phame.rag_utils.build_rag import load_config

from phame.llm.generation_chain import generation_with_query_revision
from argparse import ArgumentParser
import os
from langchain_openai import ChatOpenAI


def main():
    parser = ArgumentParser(prog="generate_part", description="Generate a parametric part with past work.")
    parser.add_argument('-d', '--description', type=str, help='Provide a description of the item')
    parser.add_argument('-o', '--output', type=str, help='Output filename')
    parser.add_argument('-i', '--issues', type=str, help='Output filename')
    parser.add_argument('--code', type=str, help='Output filename')
    parser.add_argument('-m', '--model', type=str, help='Model name', default=None)
    parser.add_argument('-c', '--config', type=str, help='Config File', default=None)
    args = parser.parse_args()

    # load config
    config = load_config(args.config)

    if args.model:
        config["retrieval"]["llm"] = args.model

    model = config['retrieval']['llm']
    top_k = config["retrieval"]["top_k"]
    output = args.output
    description = args.description
    issues = args.issues
    code_name = args.code

    api_key = os.environ['PORTKEY_API_KEY']
    base_url = os.environ['PORTKEY_BASE_URL']

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        # temperature=0.3,
    )


    chain = generation_with_query_revision(llm)

    with open(code_name) as fp:
        code = fp.readlines()

    chain_dict = {'Description': description,
                  'Code': "".join(code),
                  "Issues":issues}


    spec = chain.invoke(chain_dict)

    print(spec['title'],'\n')

    print(spec['rationale'],'\n')

    lines = spec['cad_code']
    print(lines)

    with open(output, "w") as fp:
        title = "## " + spec['title']
        fp.write(title + '\n')

        rationale = "## " + spec['rationale'].replace('\n', '\n## ')
        fp.write(rationale + '\n')


        fp.write(lines)


if __name__=="__main__":
    main()