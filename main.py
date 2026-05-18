from __future__ import annotations

import asyncio

import click
from dotenv import load_dotenv
from prompt_toolkit.application import Application, get_app
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, TextArea
from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from client.llm_client import LLMClient
from client.response import EventType

load_dotenv()

console = Console()
_INPUT_STYLE = Style.from_dict({"frame.border": "#5fafff"})


async def read_input(history: InMemoryHistory) -> str | None:
      """Show a bordered input box; return the submitted text, or None to quit."""
      kb = KeyBindings()

      @kb.add("c-c")
      @kb.add("c-d")
      def _quit(event) -> None:
            event.app.exit(result=None)

      def _accept(buff) -> bool:
            get_app().exit(result=buff.text)
            return True

      text_area = TextArea(
            multiline=False,
            accept_handler=_accept,
            history=history,
            prompt="› ",
            wrap_lines=True,
      )
      app: Application = Application(
            layout=Layout(Frame(text_area)),
            key_bindings=kb,
            style=_INPUT_STYLE,
            full_screen=False,
      )
      return await app.run_async()


async def render_response(client: LLMClient, messages: list[dict[str, str]]) -> tuple[str, bool]:
      """Stream the assistant reply behind a spinner, then render it as markdown.

      Returns (reply_text, errored).
      """
      acc = ""
      errored = False
      error_renderable: Text | None = None

      with Live(
            Spinner("dots", text=Text(" Thinking…", style="cyan")),
            console=console,
            refresh_per_second=12,
            transient=True,
      ):
            try:
                  stream = await client.chat_completion(messages, stream=True)
                  async for event in stream:
                        if event.type is EventType.TEXT_DELTA:
                              acc += event.text_delta or ""
                        elif event.type is EventType.RATE_LIMIT:
                              errored = True
                              error_renderable = Text(f"⚠  Rate limited: {event.error}", style="yellow")
                        elif event.type is EventType.ERROR:
                              errored = True
                              error_renderable = Text(f"✗  Error: {event.error}", style="red")
            except Exception as exc:
                  errored = True
                  error_renderable = Text(f"✗  Error: {exc}", style="red")

      if errored and error_renderable is not None:
            console.print(error_renderable)
      else:
            console.print(Group(Text("✻ DeepSeek", style="bold green"), Markdown(acc)))
      return acc, errored


async def chat_loop() -> None:
      """Run an interactive multi-turn chat session against DeepSeek."""
      client = LLMClient()
      history: InMemoryHistory = InMemoryHistory()
      messages: list[dict[str, str]] = []

      console.print(Panel(
            "[bold]✻ Chat with DeepSeek[/bold]\n"
            "[dim]Type a message and press Enter · ↑↓ for history · 'exit' or Ctrl+C to quit[/dim]",
            title="DeepSeek CLI",
            title_align="left",
            box=box.ROUNDED,
            border_style="cyan",
            padding=(1, 2),
            expand=False,
      ))

      try:
            while True:
                  user_input = await read_input(history)
                  if user_input is None:
                        break
                  user_input = user_input.strip()
                  if not user_input:
                        continue
                  if user_input.lower() in {"exit", "quit"}:
                        break

                  messages.append({"role": "user", "content": user_input})
                  reply, errored = await render_response(client, messages)
                  if errored:
                        messages.pop()
                  else:
                        messages.append({"role": "assistant", "content": reply})
                  console.print()
      finally:
            await client.close()
            console.print("[dim]Goodbye![/dim]")


@click.command()
def cli() -> None:
      """Interactive DeepSeek chat in your terminal."""
      asyncio.run(chat_loop())


if __name__ == "__main__":
      cli()
