from phame.agents.design_agents import build_solidworks_macro_agent, generate_part_with_k_past_work_and_plan
from phame.agents.design_agents import build_design_plan_agent, generate_design_plan
from phame.agents.design_agents import build_design_critic_agent, generate_design_plan_critique
from phame.agents.design_agents import build_solidworks_macro_critic_agent, generate_cad_code_critique
from argparse import ArgumentParser
import os
import json
import asyncio

def main():
    parser = ArgumentParser(prog="generate_part", description="Generate a parametric part with past work.")
    parser.add_argument('-d', '--description', type=str, help='Provide a description of the item')
    parser.add_argument('-o', '--output', type=str, help='Output filename')
    parser.add_argument('-m', '--model', type=str, help='Model name', default="Qwen/Qwen3-30B-A3B-Thinking-2507-FP8")
    args = parser.parse_args()

    description = args.description
    model = args.model
    output = args.output

    api_key = os.environ['PORTKEY_API_KEY']
    base_url = os.environ['PORTKEY_BASE_URL']

    with open('create_crank_arm.py', 'r') as fp:
        text1 = fp.readlines()
        text1 = "\n".join(text1)

    description1 = "The design is a crank arm that consists of a 0.15 units long arm with two circular components at the end."

    with open('create_bracket.py', 'r') as fp:
        text2 = fp.readlines()
        text2 = "\n".join(text2)

    description2 = "A bookshelf bracket to be affixed to the wall."

    with open('create_enclosure.py', 'r') as fp:
        text3 = fp.readlines()
        text3 = "\n".join(text3)

    description3 = "A simple box for use as an electrical enclosure."

    """
    Step 1. Design Plan
    """

    # get model
    api_key = os.environ['PORTKEY_API_KEY']
    base_url = os.environ['PORTKEY_BASE_URL']
    design_agent = build_design_plan_agent(model, api_key, base_url)

    tmp = f'Requesting initial experiment design from {model}.'
    print("".join(['/' for _ in range(len(tmp))]))
    print(tmp)
    print("".join(['/' for _ in range(len(tmp))]))

    design_description = asyncio.run(
        generate_design_plan(design_agent, description)
    )

    # Save output
    plan_output_text = json.loads(design_description.output.model_dump_json())
    with open(output + "_plan.json", "w", encoding="utf-8") as fp:
        json.dump(plan_output_text, fp, indent=4, ensure_ascii=False)

    print("Complete.\n"
          f"Initial Design:\n{plan_output_text['plan']}\n"
          f"Rationale:\n{plan_output_text['rationale']}\n")

    """
    Step 2. Critique Design
    """

    design_critic = build_design_critic_agent(model, api_key, base_url)

    tmp = f'Requesting review of design from {model}.'
    print("".join(['/' for _ in range(len(tmp))]))
    print(tmp)
    print("".join(['/' for _ in range(len(tmp))]))

    corrected_description = asyncio.run(
        generate_design_plan_critique(design_critic, description, plan_output_text)
    )

    plan_critic_output_text = json.loads(corrected_description.output.model_dump_json())
    with open(output + "_plan_corrected.json", "w", encoding="utf-8") as fp:
        json.dump(plan_critic_output_text, fp, indent=4, ensure_ascii=False)

    # Write out problems and fixes to stdout
    print("Complete.\n")
    issues = plan_critic_output_text['issues'].split('\n')
    fixes = plan_critic_output_text['fix'].split('\n')
    rationale = plan_critic_output_text['rationale'].split('\n')

    for k, i, f, r in zip(range(1, len(issues) + 1), issues, fixes, rationale):
        print(f"Identified Issue {k}:\n{i}\n"
              f"Rationale {k}:\n{r}\n"
              f"Fix {k}:\n{f}\n\n")

    """
    Step 3. PyAnsys coding of design
    """

    code_agent = build_solidworks_macro_agent(model, api_key, base_url)
    tmp = f'Requesting code of design from {model}.'
    print("".join(['/' for _ in range(len(tmp))]))
    print(tmp)
    print("".join(['/' for _ in range(len(tmp))]))

    # get text of corrected description and remove issues, fixes, and rationale
    corrected_description_json = json.loads(corrected_description.output.model_dump_json())
    corrected_description_json = {
        k: corrected_description_json[k]
        for k in corrected_description_json if k not in set(['fix', 'rationale', 'issues'])
    }

    cad_code = asyncio.run(
        generate_part_with_k_past_work_and_plan(code_agent,
                                                [description1, description2, description3],
                                                [text1, text2, text3],
                                                description,
                                                json.dumps(corrected_description_json))
    )

    # Save output
    code_output_text = json.loads(cad_code.output.model_dump_json())
    with open(output + '_code.py', "w") as fp:
        fp.write(code_output_text['cad_code'])
    print(f'Complete\n')

    """
    Step 4. Critique Code
    """

    # remove issues and rationale and fix

    code_critic = build_solidworks_macro_critic_agent(model, api_key, base_url)

    tmp = f'Requesting review of code from {model}.'
    print("".join(['/' for _ in range(len(tmp))]))
    print(tmp)
    print("".join(['/' for _ in range(len(tmp))]))

    corrected_code = asyncio.run(
        generate_cad_code_critique(
            code_critic,
            description,
            json.dumps(corrected_description_json),
            json.loads(cad_code.output.model_dump_json())['cad_code'])
    )

    # Save output
    code_output_text = json.loads(corrected_code.output.model_dump_json())
    with open(output + '_code_corrected.py', "w") as fp:
        fp.write(code_output_text['cad_code'])

    # Write out problems and fixes to stdout
    print("Complete.\n")
    issues = code_output_text['issues'].split('\n')
    fixes = code_output_text['fix'].split('\n')
    rationale = code_output_text['rationale'].split('\n')

    for k, i, f, r in zip(range(1, len(issues) + 1), issues, fixes, rationale):
        print(f"Identified Issue {k}:\n{i}\n"
              f"Rationale {k}:\n{r}\n"
              f"Fix {k}:\n{f}\n\n")





if __name__=="__main__":
    main()