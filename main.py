import requests
from laws_agent.clients.hg_client import HgClient
from laws_agent.parsers.html_parser import HtmlParser
from laws_agent.parsers.text_splitter import TextSplitter


URL = "https://www.evgeniiperminov.dev/"

response = requests.get(URL, timeout=10, verify=False)
print("got url", response)

parser = HtmlParser()
text = parser.parse(response.text, URL)
print("parsed", text)

splitter = TextSplitter()
chunks = splitter.split(text)
print("chunks amount", len(chunks))

hg_client = HgClient()
model = hg_client.get_model("Qwen/Qwen3-Embedding-8B")

for i, chunk in enumerate(chunks):
    print(f"--- Chunk {i + 1} ---")
    print(chunk["text"])
    if chunk["links"]:
        print("Links:", chunk["links"])
    print()
