import os
from openai import OpenAI
import json
from dotenv import load_dotenv
from gradio_client import Client
import gradio as gr

load_dotenv()

openai_client = OpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY")
)

uplink_client = Client("aldigobbler/uplink-mcp")

MODEL = "Qwen/Qwen2.5-72B-Instruct-fast"

def search_web(q, num=5, start=1, site=None, date_restrict=None):
    """Search the web using the Uplink search endpoint"""
    try:
        print(f"Searching web for query: {q} with num={num}, start={start}, site={site}, date_restrict={date_restrict}")
        result = uplink_client.predict(
            q=q,
            num=num,
            start=start,
            site=site,
            date_restrict=date_restrict,
            api_name="/search_endpoint"
        )
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

def search_news(q, num=5):
    """Search news using the Uplink news endpoint"""
    try:
        print(f"Searching news for query: {q} with num={num}")
        result = uplink_client.predict(
            q=q,
            num=num,
            api_name="/search_news_endpoint"
        )
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

def scrape_url(url):
    """Scrape content from a URL using the Uplink scrape endpoint"""
    try:
        print(f"Scraping URL: {url}")
        result = uplink_client.predict(
            url=url,
            api_name="/scrape_endpoint"
        )
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the internet for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "num": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 5)",
                        "default": 5
                    },
                    "start": {
                        "type": "integer", 
                        "description": "Starting index for results (default 1)",
                        "default": 1
                    },
                    "site": {
                        "type": "string",
                        "description": "Restrict search to specific site (optional)",
                    },
                    "date_restrict": {
                        "type": "string",
                        "description": "Date restriction: 'd1' (past day), 'w1' (past week), 'm1' (past month)",
                        "enum": ["d1", "w1", "m1"]
                    }
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Search for recent news articles",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "News search query",
                    },
                    "num": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 5)",
                        "default": 5
                    }
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_url",
            "description": "Scrape content from a specific URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to scrape content from",
                    }
                },
                "required": ["url"],
            },
        },
    }
]

available_functions = {
    "search_web": search_web,
    "search_news": search_news,
    "scrape_url": scrape_url,
}

def execute_tool_call(tool_call):
    """Execute a single tool call and return the result"""
    function_name = tool_call.function.name
    function_to_call = available_functions[function_name]
    function_args = json.loads(tool_call.function.arguments)
    
    if function_name == "search_web":
        return function_to_call(
            q=function_args.get("q"),
            num=function_args.get("num", 5),
            start=function_args.get("start", 1),
            site=function_args.get("site"),
            date_restrict=function_args.get("date_restrict")
        )
    elif function_name == "search_news":
        return function_to_call(
            q=function_args.get("q"),
            num=function_args.get("num", 5)
        )
    elif function_name == "scrape_url":
        return function_to_call(url=function_args.get("url"))

def submit_message(message, history):
    """Wrapper function to handle message submission and clear textbox"""
    if not message.strip():
        return "", history
    
    # start the chat and yield results
    for result in chat(message, history):
        yield result
    
def clear_textbox():
    """Clear the textbox after submitting"""
    return ""

def chat(message, history):
    """Main chat function with streaming response"""
    # gradio to openai
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant with access to web search, news search and web scraping tools. Use these tools to help answer user questions comprehensively. Be concise but thorough in your responses. There is NO LaTeX support. You can use markdown, and please link URLs as references.",
        }
    ]
    
    for msg in history:
        if msg["role"] in ["user", "assistant"]:
            messages.append(msg)
    
    messages.append({"role": "user", "content": message})
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    
    max_iterations = 10
    iteration = 0
    
    try:
        while iteration < max_iterations:
            iteration += 1
            
            response = openai_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=True,
                tools=tools,
                tool_choice="auto",
                max_completion_tokens=4096
            )
            
            tool_calls = []
            current_content = ""
            
            for chunk in response:
                try:
                    if chunk.choices[0].delta.content:
                        current_content += chunk.choices[0].delta.content
                        history[-1]["content"] = current_content
                        yield "", history
                    
                    if chunk.choices[0].delta.tool_calls:
                        for tool_call in chunk.choices[0].delta.tool_calls:
                            if len(tool_calls) <= tool_call.index:
                                tool_calls.extend([None] * (tool_call.index + 1 - len(tool_calls)))
                            
                            if tool_calls[tool_call.index] is None:
                                tool_calls[tool_call.index] = {
                                    "id": tool_call.id,
                                    "function": {"name": tool_call.function.name, "arguments": ""}
                                }
                            
                            if tool_call.function.arguments:
                                tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
                
                except GeneratorExit:
                    if current_content:
                        history[-1]["content"] = current_content + "\n\n⚠️ **Generation was cancelled**"
                    else:
                        history[-1]["content"] = "⚠️ **Generation was cancelled**"
                    return "", history
                except Exception as e:
                    history[-1]["content"] = f"❌ **Error during generation**: {str(e)}"
                    return "", history
            
            # we're done
            if not any(tool_calls):
                messages.append({"role": "assistant", "content": current_content})
                break
            
            # add current tool calls to messages
            messages.append({
                "role": "assistant", 
                "content": current_content,
                "tool_calls": [{"id": tc["id"], "type": "function", "function": tc["function"]} for tc in tool_calls if tc]
            })
            
            # execute tool calls and show progress
            for i, tool_call_data in enumerate(tool_calls):
                if not tool_call_data:
                    continue
                    
                try:
                    class MockToolCall:
                        def __init__(self, data):
                            self.id = data["id"]
                            self.function = type('Function', (), {
                                'name': data["function"]["name"],
                                'arguments': data["function"]["arguments"]
                            })()
                    
                    tool_call = MockToolCall(tool_call_data)
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    tool_message = f"Using **{function_name}** with: {json.dumps(function_args, indent=2)}"
                    history.append({"role": "assistant", "content": tool_message, "metadata": {"title": f"🛠️ Tool: {function_name}"}})
                    yield "", history
                    
                    function_response = execute_tool_call(tool_call)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
                    
                except GeneratorExit:
                    history.append({"role": "assistant", "content": "**Tool execution was cancelled**"})
                    return "", history
                except Exception as e:
                    error_msg = f"❌ **Error executing {function_name}**: {str(e)}"
                    history.append({"role": "assistant", "content": error_msg})
                    yield "", history
                    continue
            
            history = [msg for msg in history if not (msg.get("metadata") and "Tool:" in msg.get("metadata", {}).get("title", ""))]
    
    except GeneratorExit:
        if history and history[-1]["role"] == "assistant":
            if not history[-1]["content"]:
                history[-1]["content"] = "**Generation was cancelled**"
            else:
                history[-1]["content"] += "\n\n**Generation was cancelled**"
        return "", history
    except Exception as e:
        error_message = f"**Unexpected error**: {str(e)}"
        if history and history[-1]["role"] == "assistant":
            history[-1]["content"] = error_message
        else:
            history.append({"role": "assistant", "content": error_message})
        return "", history
    
    return "", history

def create_demo():
    with gr.Blocks(
        title="Uplink Demo",
    ) as demo:
        gr.Markdown(
            """
            # Uplink Demo
            **Powered by Qwen 2.5 and Uplink Search**
            
            Uplink is an MCP server that has the following tools:
            - 🔍 **Web search** (Google-like results)
            - 📰 **News search** (Latest articles)
            - 🌐 **Web scraping** (Extract content from URLs)

            Github repository: [cappuch/uplink-mcp-hackathon](https://github.com/cappuch/uplink-mcp-hackathon)
            """
        )
        
        chatbot = gr.Chatbot(
            type="messages",
            height=600,
            show_copy_button=True,
            show_share_button=True,
            avatar_images=("👤", "🤖"),
            bubble_full_width=False,
        )
        
        msg = gr.Textbox(
            placeholder="Ask me anything! I can search the web, calculate, and more...",
            lines=2,
            max_lines=10,
            show_label=False,
            submit_btn="Send"
        )
        
        with gr.Row():
            submit_btn = gr.Button("💬 Send", variant="primary", scale=2)
            stop_btn = gr.Button("⏹️ Stop", variant="stop", scale=1)
            clear_btn = gr.ClearButton([msg, chatbot], value="🗑️ Clear Chat", scale=1)
            
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 💡 Example Queries:")
                gr.Examples(
                    examples=[
                        "What is 25 * 4 + 10?",
                        "Search for the latest news about artificial intelligence",
                        "How many seconds would it take for a leopard at full speed to run through Pont des Arts?",
                        "Find information about the Eiffel Tower and calculate how long it would take to walk around its base at 3 mph",
                        "What's the weather like in Tokyo today?",
                        "Scrape the content from https://www.example.com",
                        "Calculate the compound interest on $1000 at 5% for 10 years"
                    ],
                    inputs=msg,
                    label="Click on any example to try it:"
                )
        
        submit_event = msg.submit(
            submit_message,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
            show_progress="minimal",
            api_name="chat_submit"
        )
        
        click_event = submit_btn.click(
            submit_message,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot],
            show_progress="minimal",
            api_name="chat_click"
        )
        
        stop_btn.click(
            None,
            None,
            None,
            cancels=[submit_event, click_event],
            api_name="stop_generation"
        )
        
        gr.Markdown(
            """
            ---
            <div align="center">
            <sub>Tools: Web Search • News Search • Web Scraping</sub><br>
            <sub>ßPowered by Qwen 2.5-72B-Instruct via Nebius AI</sub><br>
            <sub>💡 Tip: Click the "Stop" button to cancel generation at any time</sub>
            </div>
            """
        )
    
    return demo

if __name__ == "__main__":
    demo = create_demo()
    demo.launch()