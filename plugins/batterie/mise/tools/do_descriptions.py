"""do()'s two tool descriptions — server.py picks one at decoration time.

Split from tools/dispatch.py (its 500-line cap) when Sheets row inserts and
deletes landed. DO_DESCRIPTION_FULL is hard-capped at 2048 characters: over
it the API drops schema properties silently, and
tests/unit/test_tool_description_budget.py keeps 100 of headroom.
"""

DO_DESCRIPTION_FULL = """\
Act on Google Workspace.

Operations: create, copy, move, rename, share, overwrite, prepend, append, replace_text, draft, reply_draft, archive, star, label, comment, comment_reply, suggest, trash, respond, create_event, update_event, delete_event, freebusy, setup_oauth.
Create: content + title + doc_type (doc/sheet/file/folder/form). file_path= reads disk; form: YAML/JSON.
Edit: overwrite (full replace), prepend/append, replace_text (find + content; Gmail drafts too, count=N guard); append tab='T' adds a tab (doc: plain text; sheet: CSV). Sheets: overwrite=CSV, range='Tab'/'Tab!F9:F15'; append/prepend range='Tab!33' inserts rows after/before ('Tab!C'=cols, count=N blank); trash range='Tab!34:36' deletes (confirm=True); [label](url)→link, @url→chip. Docs: suggest=True (prepend/append/replace_text) proposes a tracked change; do(suggest, action=accept|reject, find='s2') folds one ([sN] tags renumber per fold).
Calendar: create_event (title + time_min/time_max; attendees/optional ⇒ preview, confirm=True books; guests ⇒ Meet unless meet=False). update_event (event/invite-thread id; time/guests/Meet gated). delete_event (file_id(s), own guest-less; confirm=True). freebusy (attendees+window). respond (RSVP). properties=tags. More: mise://docs/do.
Email: draft (to + subject + content; file_id=draft_id rewrites all; edit words: replace_text), reply_draft (file_id + content; refuses if thread has a draft, supersede=True discards), archive/star/label. Signature + quote auto-append (quote='none' skips); no sign-off.
Trash: file_id(s): Drive→bin (recoverable), drafts go for good.
Comments: comment (file_id + content = NEW thread; anchor='slide 3'/'Tab!B12'/quoted doc text, else panel-only; to= assigns), comment_reply (comment_id + content/action=resolve|reopen). '[agent] ' prefix.
Share: file_id + to + role (reader/writer/commenter); confirm=True runs.
Copy/Move: file_id(s) + folder_id.
setup_oauth: auth (force=true re-auths)."""

DO_DESCRIPTION_REMOTE = """\
Act on Google Workspace (remote mode — safe operations only).

Args:
    operation: What to do. One of: 'create', 'draft', 'reply_draft', 'archive', 'star', 'label'
    content: Text content (required for create, draft, reply_draft).
        Drafts auto-append the user's Gmail signature — don't write a sign-off.
    title: Document title (for create)
    doc_type: 'doc' | 'sheet' | 'file' | 'folder' | 'form' (for create). form: content is YAML/JSON spec
    folder_id: Optional destination folder (for create)
    file_id: Target thread ID (for reply_draft, archive, star, label)
    to: Recipient email address(es), comma-separated (for draft)
    subject: Email subject (for draft)
    cc: CC address(es), comma-separated (for draft, reply_draft)
    include: List of Drive file IDs to include as links in the email body (for draft, reply_draft)
    reply_all: If True, infer Cc from all recipients on the last message (for reply_draft)
    quote: 'none' leaves the reply bare; default quotes the message answered beneath the signature (for reply_draft)
    label: Label name to add/remove (for label operation; resolved to ID automatically)
    remove: If True, remove the label instead of adding it (for label operation)

Returns:
    file_id: File ID, draft ID, or thread ID
    web_link: URL to view/edit"""
