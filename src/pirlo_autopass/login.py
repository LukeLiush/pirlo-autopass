import asyncio
from pathlib import Path
from typing import Annotated, Any

from cloakbrowser import launch_persistent_context_async

from pirlo.core.decorators import play
from pirlo.core.models.blueprint import PlayOutput
from pirlo.core.models.parameters import Parameter
from pirlo.core.ports.play import Play
from pirlo.infrastructure.services.profile_manager import ProfileManager


class LoginOutput(PlayOutput):
    profile: str
    urls: list[str]
    success: bool = True
    error: str | None = None


@play(
    name="login",
    description="Launch a browser to authenticate and save persistent cookies.",
)
class LoginSession(Play[LoginOutput]):
    """Launch a browser to authenticate and save persistent cookies."""

    async def execute(
        self,
        profile: Annotated[
            str,
            Parameter(
                help="Name or path of the browser profile to authenticate and save"
            ),
        ] = "default",
        ttl_days: Annotated[
            int, Parameter(help="Session expiration TTL in days (default: 7)")
        ] = 7,
        urls: Annotated[
            list[str] | None,
            Parameter(
                help="List of target website URLs to open for manual authentication"
            ),
        ] = None,
        urls_file: Annotated[
            Path | None,
            Parameter(help="Path to a text file containing a list of target URLs"),
        ] = None,
        *args: Any,
        **kwargs: Any,
    ) -> LoginOutput:
        # 1. Header (Banner)
        self.ui.header(
            "Pirlo Login Manager",
            subtitle=f"Manage persistent session cookies for profile '{profile}'",
        )

        target_urls: list[str] = urls.copy() if urls else []
        if urls_file:
            if urls_file.exists():
                with open(urls_file, "r") as f:  # noqa: ASYNC230
                    target_urls.extend(
                        line.strip() for line in f.read().splitlines() if line.strip()
                    )
            else:
                instruction = f"The specified file '{urls_file}' does not exist."
                self.ui.yellow_card(
                    "URLs file not found",
                    detail=instruction,
                )
                return LoginOutput(
                    profile=profile,
                    urls=[],
                    success=False,
                    error=instruction,
                )

        # Filter out empty strings
        target_urls = [url.strip() for url in target_urls if url.strip()]

        if not target_urls:
            no_urls_msg = (
                "Please provide at least one target URL. You can:\n"
                "  1. Pass URLs directly using [bold]--urls[/bold] (e.g., --urls https://github.com)\n"
                "  2. Pass a text file with URLs using [bold]--urls-file[/bold] (e.g., --urls-file urls.txt)\n\n"
                "Example:\n"
                "  [cyan]pirlo login --profile work --urls https://github.com https://google.com[/cyan]"
            )
            self.ui.yellow_card(
                "No URLs to open",
                detail=no_urls_msg,
            )
            return LoginOutput(
                profile=profile,
                urls=[],
                success=False,
                error=no_urls_msg,
            )

        # 2. Status (Loading spinner)
        profile_path = ProfileManager.resolve_profile_path(profile)
        with self.ui.status(f"Launching browser session for profile '{profile}'..."):
            ctx = await launch_persistent_context_async(
                str(profile_path),
                headless=False,
                humanize=True,
            )
            # 3. Open the target URLs in parallel tabs
            initial_pages = ctx.pages
            tasks = []

            try:
                for i, url in enumerate(target_urls):
                    if i < len(initial_pages):
                        page = initial_pages[i]
                    else:
                        page = await ctx.new_page()
                    tasks.append(page.goto(url, wait_until="domcontentloaded"))

                await asyncio.gather(*tasks)

                # 4. Lineup (Table of targets dynamically built from target_urls)
                rows = []
                for url in target_urls:
                    domain = url.split("://")[-1].split("/")[0].replace("www.", "")
                    rows.append([domain.capitalize(), url, "Manual Login"])

                self.ui.lineup(
                    "Target Portals",
                    columns=["Portal", "URL", "Required Action"],
                    rows=rows,
                )

                # 5. VAR Check (Interactive prompt)
                await self.ui.var_check(
                    "Press [ENTER] once you are successfully logged in to save and exit"
                )

                # Save metadata
                metadata = ProfileManager.save_profile_metadata(
                    profile_input=profile,
                    urls=target_urls,
                    ttl_days=ttl_days,
                )

                # 6. Goal! (Success box)
                self.ui.goal(
                    "Session Saved Successfully!",
                    detail=(
                        f"Browser cookies saved to: {profile_path.resolve()}\n"
                        f"Profile Name: {metadata.name}\n"
                        f"Expires At: {metadata.expires_at} (TTL: {ttl_days} days)"
                    ),
                )
                return LoginOutput(
                    profile=profile,
                    urls=target_urls,
                    success=True,
                )
            finally:
                await ctx.close()


LoginPlay = LoginSession

if __name__ == "__main__":
    LoginSession.cli()
