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

from agent.agent import Agent
from agent.events import AgentEventType
from agent.session import Session
from config.config import Config

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


async def render_response(agent: Agent, user_input: str) -> None:
      """Stream the agent's reply behind a spinner, then render it as markdown."""
      reply = ""
      error_renderable: Text | None = None

      with Live(
            Spinner("dots", text=Text(" Thinking…", style="cyan")),
            console=console,
            refresh_per_second=12,
            transient=True,
      ) as live:
            async def approve(confirmation) -> bool:
                  """Pause the spinner, ask the user to allow a tool, then resume."""
                  live.stop()
                  console.print(Text(f"⚠  {confirmation.tool_name} wants to run:", style="yellow"))
                  console.print(Text(f"   {confirmation.params}", style="dim"))
                  answer = await asyncio.to_thread(console.input, "   Allow? [y/N] ")
                  live.start()
                  return answer.strip().lower() in ("y", "yes")

            agent.approval_callback = approve
            try:
                  async for event in agent.run(user_input):
                        if event.type is AgentEventType.TEXT_DELTA:
                              reply += event.data.get("text", "")
                        elif event.type is AgentEventType.TEXT_COMPLETE:
                              reply = event.data.get("text", reply)
                        elif event.type is AgentEventType.CONTEXT_PRUNED:
                              console.print(Text(
                                    f"  …pruned {event.data['dropped']} old message(s) to fit context",
                                    style="dim",
                              ))
                        elif event.type is AgentEventType.TOOL_START:
                              name = event.data.get("name", "")
                              args = (event.data.get("arguments") or "").strip()
                              if len(args) > 80:
                                    args = args[:77] + "…"
                              console.print(Text(f"  → {name} {args}", style="cyan"))
                        elif event.type is AgentEventType.TOOL_RESULT:
                              name = event.data.get("name", "")
                              if event.data.get("success"):
                                    console.print(Text(f"  ✓ {name}", style="green"))
                              else:
                                    console.print(Text(f"  ✗ {name}: {event.data.get('error')}", style="red"))
                        elif event.type is AgentEventType.AGENT_ERROR:
                              kind = event.data.get("kind", "unknown")
                              color = "yellow" if kind in ("rate_limit", "network") else "red"
                              error_renderable = Text(
                                    f"✗  [{kind}] {event.data.get('error')}", style=color
                              )
            except Exception as exc:
                  error_renderable = Text(f"✗  Error: {exc}", style="red")

      if error_renderable is not None:
            console.print(error_renderable)
      else:
            console.print(Group(Text("✻ DeepSeek", style="bold green"), Markdown(reply)))


async def chat_loop() -> None:
      """Run an interactive multi-turn chat session through the Agent."""
      agent = Agent(Session(Config()))
      history: InMemoryHistory = InMemoryHistory()

      console.print(Panel(
            "[bold]✻ Mjolnir coding agent[/bold]\n"
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
                  await render_response(agent, user_input)
                  console.print()
      finally:
            await agent.close()
            console.print("[dim]Goodbye![/dim]")


@click.command()
def cli() -> None:
      """Interactive DeepSeek chat in your terminal."""
      asyncio.run(chat_loop())


if __name__ == "__main__":
      cli()
