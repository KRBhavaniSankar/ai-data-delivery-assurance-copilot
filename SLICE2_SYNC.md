# Vertical Slice 2 Sync

This overlay extends the existing Slice 1 repository. It does not redesign Slice 1.

From the repository root:

```bash
unzip -o slice2-overlay.zip
uv sync
uv run pytest -q
```

Run the API and UI in separate terminals:

```bash
uv run uvicorn ai_data_delivery_assurance_copilot.api.main:app --reload
```

```bash
uv run streamlit run src/ai_data_delivery_assurance_copilot/ui/streamlit_app.py
```

Existing Slice 1 remains:
Requirement → Clarification → DE-SDD → Human Approval

New Slice 2:
Approved DE-SDD → Run Data Discovery → Mock Catalog + RAG → Evidence-backed Mapping

LlamaIndex/Qdrant are used when their local vector initialization succeeds; the deterministic lexical fallback keeps the demo runnable if vector initialization is unavailable.

No real enterprise catalog, ADO or production integration is introduced.
