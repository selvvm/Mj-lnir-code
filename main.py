import asyncio
from dotenv import load_dotenv
from client.llm_client import LLMClient
from client.response import EventType

load_dotenv()

async def main():
      client = LLMClient()
      stream = await client.chat_completion(
            [{"role": "user", "content": "Hello, how are you?"}],
            stream=True,
      )
      async for event in stream:
            if event.type is EventType.TEXT_DELTA:
                  print(event.text_delta, end="", flush=True)
            elif event.type is EventType.MESSAGE_COMPLETE:
                  print()
                  print("--- done ---")
                  print("finish_reason:", event.finish_reason)
                  print("usage:", event.usage)
            elif event.type is EventType.RATE_LIMIT:
                  print("Rate limited:", event.error)
            elif event.type is EventType.ERROR:
                  print("Error:", event.error)
      await client.close()

if __name__ == "__main__":
      asyncio.run(main())
