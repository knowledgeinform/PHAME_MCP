from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import NumberedListOutputParser, JsonOutputParser, CommaSeparatedListOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
from typing import Literal, get_args

from phame.llm.basemodels import DesignCode

parser = JsonOutputParser(pydantic_object=DesignCode)

def generate_part_with_past_work(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a senior mechanical engineer producing SolidWorks Macro Python Code.\n"
         "Requirements:\n"
         "- Prefer simple, robust geometry.\n"
         "- Keep rationale brief (<=3 bullets). No step-by-step reasoning.\n"
         "- Include holes for fasteners if needed."
         "- Code must include a line enabling updating graphics."
         "- Output must be a valid JSON"),
        ("human",
         "Example part:\n"
         "{Description_1}\n{CAD1}\n\n"
         "TASK: Produce a CAD design for {Description_2} and output JSON only.\n\n"
         "JSON schema instructions:\n{format_instructions}"
        ),
    ]).partial(format_instructions=parser.get_format_instructions())

    output_parser = JsonOutputParser()

    chain = prompt | llm | output_parser

    return chain


def generation_with_query_top_k(llm, k):
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a senior mechanical engineer producing CADQuery code.\n"
         "Requirements:\n"
         "- Prefer simple, robust geometry.\n"
         "- Keep rationale brief (<=3 bullets). No step-by-step reasoning.\n"
         "- Include holes for fasteners if needed."
         "- Code must include a line for exporting the model to an stl file."
         "- Output must be a valid JSON"),
        ("human",
         "Example part:\n"
        + "".join([f"{{Description_{i}}}\n{{Code_{i}}}\n\n" for i in range(k)])
        + "TASK: Produce a CAD design for {Description_Part} and output JSON only.\n\n"
        + "JSON schema instructions:\n{format_instructions}"),
    ]).partial(format_instructions=parser.get_format_instructions())

    output_parser = JsonOutputParser()

    chain = prompt | llm | output_parser

    return chain


def generation_with_query_revision(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a senior mechanical engineer producing SolidWorks Macro Python Code.\n"
         "You are task with taking CAD designs and improving them based on a list of issues.\n"
         "Requirements:\n"
         "- Prefer simple, robust geometry.\n"
         "- Keep rationale brief (<=3 bullets). No step-by-step reasoning.\n"
         "- Include holes for fasteners if needed."
         "- Code must include a line enabling updating graphics."
         "- Output must be a valid JSON"),
        ("human",
         "This is the description of the design you need to fix:\n {Description}\n"
         "Here is the code for this design:\n {Code}\n"
         "Here is the list of issues: \n {Issues} \n"
         "Please fix the code such that these issues are resolved and output JSON only.\n\n"
         "JSON schema instructions:\n{format_instructions}"),
    ]).partial(format_instructions=parser.get_format_instructions())

    output_parser = JsonOutputParser()

    chain = prompt | llm | output_parser

    return chain