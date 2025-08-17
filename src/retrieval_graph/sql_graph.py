"""SQL Agent Graph for database interactions.

This module defines a SQL agent graph that can:
1. Fetch available tables from the database
2. Decide which tables are relevant to the question
3. Fetch schemas for the relevant tables
4. Generate a query based on the question and schema information
5. Double-check the query for common mistakes using an LLM
6. Execute the query and return the results
7. Correct mistakes surfaced by the database engine until the query is successful
8. Formulate a response based on the results
"""

from typing import Literal, Optional, Sequence, Annotated
from dataclasses import dataclass, field
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.chat_models import init_chat_model

from retrieval_graph.utils import load_chat_model


@dataclass(kw_only=True)
class SQLInputState:
    """Input state for SQL agent - only contains messages."""
    messages: Annotated[Sequence[BaseMessage], add_messages]


@dataclass(kw_only=True)
class SQLState(SQLInputState):
    """State for SQL agent graph."""
    tables: list[str] = field(default_factory=list)
    """List of available tables in the database."""
    
    schemas: dict[str, str] = field(default_factory=dict)
    """Schema information for relevant tables."""
    
    current_query: Optional[str] = field(default=None)
    """Current SQL query being processed."""
    
    query_results: Optional[str] = field(default=None)
    """Results from the last executed query."""
    
    error_message: Optional[str] = field(default=None)
    """Error message from failed query execution."""


class SQLAgentGraph:
    """SQL Agent Graph for database interactions."""
    
    def __init__(self, db: SQLDatabase, llm=None):
        """Initialize the SQL agent graph.
        
        Args:
            db: SQLDatabase instance to interact with
            llm: Language model for query generation and checking
        """
        self.db = db
        self.llm = llm or init_chat_model("openai:gpt-4")
        self.toolkit = SQLDatabaseToolkit(db=db, llm=self.llm)
        self.tools = self.toolkit.get_tools()
        
        # Create tool nodes
        self.list_tables_tool = next(tool for tool in self.tools if tool.name == "sql_db_list_tables")
        self.schema_tool = next(tool for tool in self.tools if tool.name == "sql_db_schema")
        self.query_tool = next(tool for tool in self.tools if tool.name == "sql_db_query")
        self.query_checker_tool = next(tool for tool in self.tools if tool.name == "sql_db_query_checker")
        
        self.schema_node = ToolNode([self.schema_tool], name="get_schema")
        self.query_node = ToolNode([self.query_tool], name="run_query")
        self.query_checker_node = ToolNode([self.query_checker_tool], name="check_query")
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _list_tables(self, state: SQLState) -> dict:
        """List all available tables in the database."""
        tool_call = {
            "name": "sql_db_list_tables",
            "args": {},
            "id": "list_tables_call",
            "type": "tool_call",
        }
        tool_call_message = AIMessage(content="", tool_calls=[tool_call])
        
        tool_message = self.list_tables_tool.invoke(tool_call)
        response = AIMessage(f"Available tables: {tool_message.content}")
        
        tables = [table.strip() for table in tool_message.content.split(",")]
        
        return {
            "messages": [tool_call_message, tool_message, response],
            "tables": tables
        }
    
    def _call_get_schema(self, state: SQLState) -> dict:
        """Generate a tool call to get schema for relevant tables."""
        # Use LLM to determine which tables are relevant
        llm_with_tools = self.llm.bind_tools([self.schema_tool], tool_choice="any")
        response = llm_with_tools.invoke(state.messages)
        
        return {"messages": [response]}
    
    def _generate_query(self, state: SQLState) -> dict:
        """Generate a SQL query based on the question and schema information."""
        system_prompt = f"""
        You are an agent designed to interact with a SQL database.
        Given an input question, create a syntactically correct {self.db.dialect} query to run,
        then look at the results of the query and return the answer. Unless the user
        specifies a specific number of examples they wish to obtain, always limit your
        query to at most 5 results.

        You can order the results by a relevant column to return the most interesting
        examples in the database. Never query for all the columns from a specific table,
        only ask for the relevant columns given the question.

        DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
        
        Available tables: {', '.join(state.tables)}
        Schema information: {state.schemas}
        """
        
        system_message = HumanMessage(content=system_prompt)
        llm_with_tools = self.llm.bind_tools([self.query_tool])
        response = llm_with_tools.invoke([system_message] + list(state.messages))
        
        return {"messages": [response]}
    
    def _check_query(self, state: SQLState) -> dict:
        """Double-check the SQL query for common mistakes."""
        if not state.messages[-1].tool_calls:
            return {"messages": [state.messages[-1]]}
        
        tool_call = state.messages[-1].tool_calls[0]
        query = tool_call["args"]["query"]
        
        system_prompt = f"""
        You are a SQL expert with a strong attention to detail.
        Double check the {self.db.dialect} query for common mistakes, including:
        - Using NOT IN with NULL values
        - Using UNION when UNION ALL should have been used
        - Using BETWEEN for exclusive ranges
        - Data type mismatch in predicates
        - Properly quoting identifiers
        - Using the correct number of arguments for functions
        - Casting to the correct data type
        - Using the proper columns for joins

        If there are any of the above mistakes, rewrite the query. If there are no mistakes,
        just reproduce the original query.

        You will call the appropriate tool to execute the query after running this check.
        """
        
        system_message = HumanMessage(content=system_prompt)
        user_message = HumanMessage(content=f"Check this query: {query}")
        llm_with_tools = self.llm.bind_tools([self.query_tool], tool_choice="any")
        response = llm_with_tools.invoke([system_message, user_message])
        
        if response.tool_calls:
            response.id = state.messages[-1].id
        
        return {"messages": [response]}
    
    def _should_continue(self, state: SQLState) -> Literal[END, "check_query"]:
        """Determine if we should continue to query checking or end."""
        messages = state.messages
        last_message = messages[-1]
        if not last_message.tool_calls:
            return END
        else:
            return "check_query"
    
    def _build_graph(self) -> StateGraph:
        """Build the SQL agent graph."""
        builder = StateGraph(SQLState)
        
        # Add nodes
        builder.add_node("list_tables", self._list_tables)
        builder.add_node("call_get_schema", self._call_get_schema)
        builder.add_node("get_schema", self.schema_node)
        builder.add_node("generate_query", self._generate_query)
        builder.add_node("check_query", self._check_query)
        builder.add_node("run_query", self.query_node)
        
        # Add edges
        builder.add_edge(START, "list_tables")
        builder.add_edge("list_tables", "call_get_schema")
        builder.add_edge("call_get_schema", "get_schema")
        builder.add_edge("get_schema", "generate_query")
        builder.add_conditional_edges(
            "generate_query",
            self._should_continue,
        )
        builder.add_edge("check_query", "run_query")
        builder.add_edge("run_query", "generate_query")
        
        return builder.compile()
    
    def invoke(self, question: str, config: Optional[RunnableConfig] = None):
        """Invoke the SQL agent with a question."""
        initial_message = HumanMessage(content=question)
        return self.graph.invoke(
            {"messages": [initial_message]},
            config=config
        )
    
    def stream(self, question: str, config: Optional[RunnableConfig] = None):
        """Stream the SQL agent execution with a question."""
        initial_message = HumanMessage(content=question)
        return self.graph.stream(
            {"messages": [initial_message]},
            config=config
        )



def setup_database():
    """Set up the SQLite database connection."""

    # # Download the sample database
    # download_chinook_database()
    db = SQLDatabase.from_uri("sqlite:///Chinook.db")
    
    print(f"Database dialect: {db.dialect}")
    print(f"Available tables: {db.get_usable_table_names()}")
    
    return db

    
db = setup_database()
# Initialize the language model
llm = load_chat_model("openai/gpt-4o-mini")
sql_agent_graph = SQLAgentGraph(db, llm).graph 
sql_agent_graph.name = "SQLAgentGraph"