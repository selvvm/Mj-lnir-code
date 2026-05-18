import asyncio
from client.llm_client import LLMClient

async def main():
      client = LLMClient()
      response = await client.chat_completion(
            [{"role": "user", "content": "Hello, how are you?"}],
            stream=False,
      )
      print(response)
      await client.close()

if __name__ == "__main__":
      asyncio.run(main())
