"""MindMapAgent — Collaborative brainstorming with AI-powered mindmaps."""

import flet as ft

from llm import PROVIDERS, analyse_ideas, configure, is_configured, validate_key
from mindmap import render_mindmap_html
from session import (
    SessionStatus,
    add_idea,
    create_session,
    get_session,
)


async def main(page: ft.Page):
    page.title = "MindMapAgent"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    # ── Per-user state ──────────────────────────────────────────────
    state = {"session_id": None, "name": None, "is_moderator": False}

    # ── Live UI refs (set when entering session room) ──────────────
    ui = {"ideas_list": None, "participants": None, "status": None}

    # ── Helpers ─────────────────────────────────────────────────────
    def snack(msg, error=False):
        page.snack_bar = ft.SnackBar(
            ft.Text(msg, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_600 if error else ft.Colors.BLUE_GREY_700,
        )
        page.snack_bar.open = True
        page.update()

    def _idea_tile(author: str, text: str):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(author, weight=ft.FontWeight.BOLD, size=13, color=ft.Colors.BLUE_700),
                    ft.Text(text, expand=True, size=14),
                ],
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=8,
            bgcolor=ft.Colors.BLUE_50,
            margin=ft.Margin.only(bottom=4),
        )

    # ── PubSub handler ──────────────────────────────────────────────
    def on_session_msg(topic: str, msg: dict):
        t = msg.get("type")
        if t == "idea" and ui["ideas_list"]:
            ui["ideas_list"].controls.append(_idea_tile(msg["author"], msg["text"]))
        elif t == "participants" and ui["participants"]:
            ui["participants"].value = f"{msg['count']} participant(s)"
        elif t == "status" and ui["status"]:
            ui["status"].value = msg["text"]
        elif t == "mindmap_ready":
            show_mindmap_page(msg["session_id"])
            return  # show_mindmap_page calls page.update()
        page.update()

    # ── Landing page ────────────────────────────────────────────────
    def show_landing():
        page.pubsub.unsubscribe_all()
        state.update(session_id=None, name=None, is_moderator=False)
        ui.update(ideas_list=None, participants=None, status=None)

        # ── API key configuration ──
        provider_options = [ft.DropdownOption(key=p, text=p) for p in PROVIDERS]
        provider_dd = ft.Dropdown(
            label="AI Provider",
            options=provider_options,
            value="Gemini",
            width=200,
        )
        key_field = ft.TextField(
            label="API Key",
            password=True,
            can_reveal_password=True,
            expand=True,
        )
        key_status = ft.Text("", size=12)

        def _update_key_status(ok: bool, msg: str):
            if ok:
                key_status.value = msg
                key_status.color = ft.Colors.GREEN_700
            else:
                key_status.value = msg
                key_status.color = ft.Colors.RED_600

        async def on_save_key(e):
            provider = provider_dd.value
            key = key_field.value.strip()
            if not key:
                _update_key_status(False, "Please enter an API key.")
                page.update()
                return
            _update_key_status(False, "Validating...")
            page.update()
            err = await validate_key(provider, key)
            if err:
                _update_key_status(False, f"Invalid key: {err}")
            else:
                configure(provider, key)
                _update_key_status(True, f"Key valid ({provider})")
            page.update()

        if is_configured():
            _update_key_status(True, "Key configured")

        # ── Session controls ──
        topic_field = ft.TextField(
            label="Brainstorming topic",
            hint_text="e.g. Product ideas for Q3",
            expand=True,
        )
        join_field = ft.TextField(
            label="Session code",
            hint_text="e.g. ABC123",
            width=180,
            capitalization=ft.TextCapitalization.CHARACTERS,
        )
        error = ft.Text("", color=ft.Colors.RED_400, size=12)

        def on_create(e):
            if not is_configured():
                error.value = "Please configure an API key first."
                page.update()
                return
            topic = topic_field.value.strip()
            if not topic:
                error.value = "Please enter a topic."
                page.update()
                return
            session = create_session(topic)
            state["is_moderator"] = True
            show_name_prompt(session.id)

        def on_join(e):
            code = join_field.value.strip().upper()
            if not code:
                error.value = "Please enter a session code."
                page.update()
                return
            session = get_session(code)
            if not session:
                error.value = f"Session '{code}' not found."
                page.update()
                return
            if session.status not in (SessionStatus.ACTIVE, SessionStatus.COMPLETE):
                error.value = f"Session '{code}' is no longer active."
                page.update()
                return
            state["is_moderator"] = False
            show_name_prompt(session.id)

        join_field.on_submit = on_join

        page.controls.clear()
        page.add(
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    width=480,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Container(height=20),
                        ft.Text("MindMapAgent", size=32, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Collaborative brainstorming with AI-powered mindmaps",
                            size=14,
                            color=ft.Colors.GREY_600,
                        ),
                        ft.Divider(height=20),
                        # ── API key section ──
                        ft.Text("AI Provider", size=18, weight=ft.FontWeight.W_500),
                        ft.Row(
                            [provider_dd, key_field],
                            spacing=8,
                        ),
                        ft.Row(
                            [
                                ft.Button("Save Key", icon=ft.Icons.KEY, on_click=on_save_key),
                                key_status,
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Divider(height=20),
                        # ── Create session ──
                        ft.Text("Start a new session", size=18, weight=ft.FontWeight.W_500),
                        topic_field,
                        ft.Button(
                            "Create Session",
                            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                            on_click=on_create,
                            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE),
                        ),
                        ft.Divider(height=20),
                        # ── Join session ──
                        ft.Text("Join an existing session", size=18, weight=ft.FontWeight.W_500),
                        ft.Row(
                            [join_field, ft.Button("Join", on_click=on_join)],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        error,
                    ],
                ),
            )
        )
        page.update()

    # ── Name prompt ─────────────────────────────────────────────────
    def show_name_prompt(session_id: str):
        state["session_id"] = session_id
        session = get_session(session_id)

        name_field = ft.TextField(label="Your display name", autofocus=True, width=300)

        def submit(e):
            name = name_field.value.strip()
            if not name:
                return
            state["name"] = name
            session.participants.add(name)
            show_session_room()

        name_field.on_submit = submit

        role = "moderator" if state["is_moderator"] else "participant"
        page.controls.clear()
        page.add(
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    width=420,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=14,
                    controls=[
                        ft.Text(session.topic, size=22, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"Session {session_id}  ·  joining as {role}",
                            size=13,
                            color=ft.Colors.GREY_500,
                        ),
                        ft.Container(height=10),
                        name_field,
                        ft.Button("Enter", on_click=submit),
                    ],
                ),
            )
        )
        page.update()

    # ── Session room ────────────────────────────────────────────────
    def show_session_room():
        sid = state["session_id"]
        session = get_session(sid)
        if not session:
            show_landing()
            return

        # Subscribe to session pubsub topic
        page.pubsub.subscribe_topic(sid, on_session_msg)

        # Build live UI controls
        ideas_list = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        participant_text = ft.Text(f"{len(session.participants)} participant(s)", size=13)
        status_text = ft.Text("", size=13, color=ft.Colors.ORANGE_700, italic=True)
        ui.update(ideas_list=ideas_list, participants=participant_text, status=status_text)

        # Pre-populate existing ideas
        for idea in session.ideas:
            ideas_list.controls.append(_idea_tile(idea.author, idea.text))

        # Idea input
        idea_field = ft.TextField(
            hint_text="Type your idea and press Enter…",
            expand=True,
            border_radius=8,
            autofocus=True,
        )

        async def submit_idea(e):
            text = idea_field.value.strip()
            if not text or session.status != SessionStatus.ACTIVE:
                return
            add_idea(sid, text, state["name"])
            page.pubsub.send_all_on_topic(
                sid, {"type": "idea", "text": text, "author": state["name"]}
            )
            idea_field.value = ""
            await idea_field.focus()
            page.update()

        idea_field.on_submit = submit_idea

        # Notify others about join
        page.pubsub.send_all_on_topic(
            sid, {"type": "participants", "count": len(session.participants)}
        )

        # Copy code button
        async def copy_code(e):
            await page.clipboard.set(sid)
            snack(f"Session code {sid} copied!")

        # ── Moderator controls ──
        generate_btn = ft.Button(
            "Generate Mindmap",
            icon=ft.Icons.AUTO_AWESOME,
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE),
        )
        spinner = ft.ProgressRing(width=20, height=20, stroke_width=2, visible=False)

        async def on_generate(e):
            if not session.ideas:
                snack("No ideas to analyse yet!", error=True)
                return
            if not is_configured():
                snack("No API key configured! Go back and set one.", error=True)
                return

            generate_btn.disabled = True
            spinner.visible = True
            session.status = SessionStatus.GENERATING
            page.pubsub.send_all_on_topic(sid, {"type": "status", "text": "Generating mindmap…"})
            page.update()

            try:
                ideas_data = [{"text": i.text, "author": i.author} for i in session.ideas]
                analysis = await analyse_ideas(session.topic, ideas_data)
                filepath = render_mindmap_html(sid, session.topic, analysis)
                session.mindmap_html = filepath
                session.status = SessionStatus.COMPLETE
                page.pubsub.send_all_on_topic(
                    sid, {"type": "mindmap_ready", "session_id": sid}
                )
            except Exception as ex:
                session.status = SessionStatus.ACTIVE
                generate_btn.disabled = False
                spinner.visible = False
                page.pubsub.send_all_on_topic(
                    sid, {"type": "status", "text": f"Error: {ex}"}
                )
                page.update()

        generate_btn.on_click = on_generate

        def on_end(e):
            session.status = SessionStatus.ENDED
            page.pubsub.send_all_on_topic(
                sid, {"type": "status", "text": "Session ended by moderator."}
            )

        mod_row = (
            ft.Row(
                [
                    generate_btn,
                    spinner,
                    ft.OutlinedButton("End Session", icon=ft.Icons.STOP, on_click=on_end),
                ],
                spacing=8,
            )
            if state["is_moderator"]
            else ft.Container()
        )

        # ── Build page ──
        page.controls.clear()
        page.add(
            # Header
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(session.topic, size=20, weight=ft.FontWeight.BOLD),
                                ft.Row(
                                    [
                                        ft.Text(
                                            f"Code: {sid}",
                                            size=14,
                                            weight=ft.FontWeight.W_500,
                                            selectable=True,
                                        ),
                                        ft.IconButton(
                                            ft.Icons.COPY,
                                            on_click=copy_code,
                                            tooltip="Copy session code",
                                            icon_size=16,
                                        ),
                                    ],
                                    spacing=4,
                                ),
                            ],
                            expand=True,
                            spacing=2,
                        ),
                        ft.Column(
                            [participant_text, status_text],
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=2,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=ft.Padding.all(16),
                bgcolor=ft.Colors.BLUE_GREY_50,
            ),
            # Ideas list
            ft.Container(
                content=ideas_list,
                expand=True,
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            ),
            # Input bar + moderator controls
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        idea_field,
                        ft.IconButton(ft.Icons.SEND, on_click=submit_idea, tooltip="Submit"),
                    ]),
                    mod_row,
                ], spacing=8),
                padding=ft.Padding.all(16),
                bgcolor=ft.Colors.GREY_100,
            ),
        )
        page.update()

    # ── Mindmap result page ─────────────────────────────────────────
    def show_mindmap_page(session_id: str):
        session = get_session(session_id)
        if not session or not session.mindmap_html:
            snack("Mindmap not available.", error=True)
            return

        # Extract markdown preview from the saved HTML
        md_preview = ""
        try:
            with open(session.mindmap_html, "r") as f:
                html = f.read()
            tag = '<script type="text/template">'
            start = html.find(tag)
            if start >= 0:
                start += len(tag)
                end = html.find("</script>", start)
                md_preview = html[start:end].strip()
        except Exception:
            pass

        def open_file(e):
            page.launch_url(f"file://{session.mindmap_html}")

        page.controls.clear()
        page.add(
            # Header
            ft.Container(
                content=ft.Row([
                    ft.Text("Mindmap Generated!", size=20, weight=ft.FontWeight.BOLD, expand=True),
                    ft.OutlinedButton("Back to Session", icon=ft.Icons.ARROW_BACK, on_click=lambda e: show_session_room()),
                    ft.OutlinedButton("New Session", icon=ft.Icons.HOME, on_click=lambda e: show_landing()),
                ]),
                padding=ft.Padding.all(16),
                bgcolor=ft.Colors.GREEN_50,
            ),
            # Info + open button
            ft.Container(
                content=ft.Column([
                    ft.Text(f"Topic: {session.topic}", size=16, weight=ft.FontWeight.W_500),
                    ft.Text(
                        f"Saved to: {session.mindmap_html}",
                        size=12,
                        color=ft.Colors.GREY_600,
                        selectable=True,
                    ),
                    ft.Button(
                        "Open Interactive Mindmap in Browser",
                        icon=ft.Icons.OPEN_IN_NEW,
                        on_click=open_file,
                    ),
                ], spacing=8),
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            ),
            # Markdown preview
            ft.Container(
                content=ft.Markdown(
                    md_preview,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
                    selectable=True,
                ),
                expand=True,
                padding=ft.Padding.all(16),
                border=ft.Border.all(1, ft.Colors.GREY_300),
                border_radius=8,
                margin=ft.Margin.symmetric(horizontal=16),
            ),
        )
        page.update()

    # ── Disconnect handler ──────────────────────────────────────────
    def on_disconnect(e):
        sid = state.get("session_id")
        name = state.get("name")
        if sid and name:
            session = get_session(sid)
            if session:
                session.participants.discard(name)
                try:
                    page.pubsub.send_all_on_topic(
                        sid, {"type": "participants", "count": len(session.participants)}
                    )
                except Exception:
                    pass
        page.pubsub.unsubscribe_all()

    page.on_disconnect = on_disconnect

    # ── Initial routing (supports deep links like /session/ABC123) ──
    route = page.route or ""
    if route.startswith("/session/"):
        parts = route.strip("/").split("/")
        if len(parts) >= 2:
            sid = parts[1].upper()
            if get_session(sid):
                state["is_moderator"] = False
                show_name_prompt(sid)
                return
    show_landing()


ft.run(main, view=ft.AppView.WEB_BROWSER, port=8000)
