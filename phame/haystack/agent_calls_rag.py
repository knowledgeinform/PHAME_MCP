# agent_calls_rag.py
# pip install haystack-ai openai-haystack
# export OPENAI_API_KEY=...

from haystack import Pipeline, Document, component
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.builders.chat_prompt_builder import ChatPromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.builders.answer_builder import AnswerBuilder
from haystack.dataclasses import ChatMessage
from haystack.tools import PipelineTool
from haystack.components.agents import Agent
from haystack.utils import Secret
from haystack import Pipeline

import os
from getpass import getpass
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.utils import Secret
from openai import OpenAI
from datasets import load_dataset
from haystack.dataclasses import GeneratedAnswer

@component
class FirstAnswerText:
    @component.output_types(answer=str)
    def run(self, answers: list[GeneratedAnswer]):
        return {"answer": answers[0].data if answers else ""}

def build_rag_pipeline() -> Pipeline:
    
    # Initialize the document store
    document_store = InMemoryDocumentStore()

    # Fetch the data

    dataset = load_dataset("bilgeyucel/seven-wonders", split="train")
    docs = [Document(content=doc["content"], meta=doc["meta"]) for doc in dataset]

    #Initialize the Document Embedder

    doc_embedder = SentenceTransformersDocumentEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    doc_embedder.warm_up()

    # Write Dcouments to the Document Store
    docs_with_embeddings = doc_embedder.run(docs)
    document_store.write_documents(docs_with_embeddings["documents"])

    # Initialize the text embedder
    from haystack.components.embedders import SentenceTransformersTextEmbedder

    text_embedder = SentenceTransformersTextEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")

    # Initialize the Retriever 
    retriever = InMemoryEmbeddingRetriever(document_store)
    
    template = [
        ChatMessage.from_user(
            """
    Given the following information, answer the question.

    Context:
    {% for document in documents %}
        {{ document.content }}
    {% endfor %}

    Question: {{question}}
    Answer:
    """
        )
    ]
    
    prompt_builder = ChatPromptBuilder(
        template=template,
        required_variables=["question", "documents"]
        )

    # Initialize the Chat Generator
    chat_generator = OpenAIChatGenerator(
        model="openai/gpt-oss-120b",
        api_base_url=os.environ["PORTKEY_BASE_URL"],  # Portkey OpenAI-compatible URL
        api_key=Secret.from_env_var("PORTKEY_API_KEY")
        )

    # Build the pipeline
    basic_rag_pipeline = Pipeline()
    
    # Add components to your pipeline
    basic_rag_pipeline.add_component("text_embedder", text_embedder)
    basic_rag_pipeline.add_component("retriever", retriever)
    basic_rag_pipeline.add_component("prompt_builder", prompt_builder)
    basic_rag_pipeline.add_component("llm", chat_generator)
    basic_rag_pipeline.add_component("answer_builder", AnswerBuilder())
    basic_rag_pipeline.add_component("first_answer", FirstAnswerText())
    
    
    # Now, connect the components to each other
    # basic_rag_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
    # basic_rag_pipeline.connect("retriever", "prompt_builder")
    # basic_rag_pipeline.connect("prompt_builder.prompt", "llm.messages")
    # basic_rag_pipeline.connect("retriever", "answer_builder.documents")
    # basic_rag_pipeline.connect("llm.replies", "answer_builder.replies")
    # basic_rag_pipeline.connect("answer_builder.answers", "first_answer.answers")
    basic_rag_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")

    basic_rag_pipeline.connect("retriever.documents", "prompt_builder.documents")
    basic_rag_pipeline.connect("prompt_builder.prompt", "llm.messages")

    basic_rag_pipeline.connect("llm.replies", "answer_builder.replies")
    basic_rag_pipeline.connect("retriever.documents", "answer_builder.documents")

    basic_rag_pipeline.connect("answer_builder.answers", "first_answer.answers")

    return basic_rag_pipeline

def build_agent(rag_pipeline: Pipeline) -> Agent:
    rag_tool = PipelineTool(
        pipeline=rag_pipeline,
        name="rag_qa",
        description="Answer questions using the internal knowledge base via RAG.",
        input_mapping={"query": 
            [
                "text_embedder.text", 
                "prompt_builder.question", 
                "answer_builder.query"
             ]},
        output_mapping={
            "first_answer.answer": "answer",
            "retriever.documents": "documents",
            },
    )

    agent_chat_generator = OpenAIChatGenerator(
        model="openai/gpt-oss-120b",
        api_base_url=os.environ["PORTKEY_BASE_URL"],  # Portkey OpenAI-compatible URL
        api_key=Secret.from_env_var("PORTKEY_API_KEY")
        )

    agent = Agent(
        chat_generator=agent_chat_generator,
        tools=[rag_tool],
        system_prompt="Always call the rag_qa tool before answering. If the tool returns an empty answer, say you don't know.",
        exit_conditions=["text"],
    )
    agent.warm_up()
    return agent

if __name__ == "__main__":
    rag = build_rag_pipeline()
    agent = build_agent(rag)

    question = "What does Rhodes Statue look like?"
    result = agent.run(messages=[ChatMessage.from_user(question)])
    print(result["messages"][-1].text)
