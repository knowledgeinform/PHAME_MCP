import os
from argparse import ArgumentParser
# from phame.rag_utils.build_rag import load_config
import json
import asyncio

from phame.llm.analysis_agents import build_analysis_plan_agent, generate_analysis_plan
from phame.llm.analysis_agents import build_analysis_code_agent, generate_analysis_code
from phame.llm.analysis_agents import build_analysis_plan_critic_agent, generate_analysis_plan_critique
from phame.llm.analysis_agents import build_analysis_code_critic_agent, generate_analysis_code_critique

def main():
    parser = ArgumentParser(prog="generate_part", description="Generate a parametric part with past work.")
    parser.add_argument('-d', '--description', type=str, help='Provide a description of the item')
    parser.add_argument('-o', '--output', type=str, help='Output filename')
    parser.add_argument('-j', '--design_output', type=str, help='Output filename')
    parser.add_argument('--code', type=str, help='CAD Code filename')
    parser.add_argument('-m', '--model', type=str, help='Model name', default=None)
    parser.add_argument('-c', '--config', type=str, help='Config File', default=None)
    args = parser.parse_args()

    model = args.model
    description = args.description
    output_file = args.output
    output_json = args.design_output
    code_path = args.code

    # load config
    # config = load_config(args.config)



    """
    Step 1. Make initial experiment design
    """

    # get model
    api_key = os.environ['PORTKEY_API_KEY']
    base_url = os.environ['PORTKEY_BASE_URL']
    design_agent = build_analysis_plan_agent(model, api_key, base_url)

    with open(code_path, 'r') as fp:
        code = fp.readlines()
        code = "".join(code)

    tmp = f'Requesting initial experiment design from {model}.'
    print("".join(['/' for _ in range(len(tmp))]))
    print(tmp)
    print("".join(['/' for _ in range(len(tmp))]))

    analysis_description = asyncio.run(
        generate_analysis_plan(design_agent, code, description)
    )

    # Save output
    plan_output_text = json.loads(analysis_description.output.model_dump_json())
    with open(output_json, "w", encoding="utf-8") as fp:
        json.dump(plan_output_text, fp, indent=4, ensure_ascii=False)

    print("Complete.\n"
           f"Initial Design:\n{plan_output_text['analysis_design']}\n"
           f"Rationale:\n{plan_output_text['rationale']}\n")

    """
    Step 2. Critique Design
    """

    design_critic = build_analysis_plan_critic_agent(model, api_key, base_url)

    tmp = f'Requesting review of design from {model}.'
    print("".join(['/' for _ in range(len(tmp))]))
    print(tmp)
    print("".join(['/' for _ in range(len(tmp))]))

    corrected_description = asyncio.run(
        generate_analysis_plan_critique(design_critic, code, description, plan_output_text)
    )

    plan_critic_output_text = json.loads(corrected_description.output.model_dump_json())
    with open(output_json[:-5] + "_corrected.json", "w", encoding="utf-8") as fp:
        json.dump(plan_critic_output_text, fp, indent=4, ensure_ascii=False)

    # Write out problems and fixes to stdout
    print("Complete.\n")
    issues = plan_critic_output_text['issues'].split('\n')
    fixes = plan_critic_output_text['fix'].split('\n')
    rationale = plan_critic_output_text['rationale'].split('\n')

    for k,i,f,r in zip(range(1,len(issues)+1),issues, fixes, rationale):
        print(f"Identified Issue {k}:\n{i}\n"
           f"Rationale {k}:\n{r}\n"
           f"Fix {k}:\n{f}\n\n")

    """
    Step 3. PyAnsys coding of design
    """

    fem_agent = build_analysis_code_agent(model, api_key, base_url)
    tmp = f'Requesting code of design from {model}.'
    print("".join(['/' for _ in range(len(tmp))]))
    print(tmp)
    print("".join(['/' for _ in range(len(tmp))]))

    # get text of corrected description and remove issues, fixes, and rationale
    corrected_description_json = json.loads(corrected_description.output.model_dump_json())
    corrected_description_json = {
        k:corrected_description_json[k]
        for k in corrected_description_json if k not in set(['fix', 'rationale', 'issues'])
    }

    analysis_code = asyncio.run(
        generate_analysis_code(fem_agent, code, description, code_path, json.dumps(corrected_description_json))
    )

    # Save output
    code_output_text = json.loads(analysis_code.output.model_dump_json())
    with open(output_file, "w") as fp:
        fp.write(code_output_text['analysis_code'])
    print(f'Complete\n')

    """
    Step 4. Critique Code
    """

    # remove issues and rationale and fix

    code_critic = build_analysis_code_critic_agent(model, api_key, base_url)

    tmp = f'Requesting review of code from {model}.'
    print("".join(['/' for _ in range(len(tmp))]))
    print(tmp)
    print("".join(['/' for _ in range(len(tmp))]))

    corrected_code = asyncio.run(
        generate_analysis_code_critique(code_critic, code, description, code_path, corrected_description.output,
                                        json.loads(analysis_code.output.model_dump_json())['analysis_code'])
    )

    # Save output
    code_output_text = json.loads(corrected_code.output.model_dump_json())
    with open(output_file[:-3] + 'corrected.py', "w") as fp:
        fp.write(code_output_text['analysis_code'])

    # Write out problems and fixes to stdout
    print("Complete.\n")
    issues = code_output_text['issues'].split('\n')
    fixes = code_output_text['fix'].split('\n')
    rationale = code_output_text['rationale'].split('\n')

    for k,i,f,r in zip(range(1,len(issues)+1),issues, fixes, rationale):
        print(f"Identified Issue {k}:\n{i}\n"
           f"Rationale {k}:\n{r}\n"
           f"Fix {k}:\n{f}\n\n")


if __name__=="__main__":
    main()

