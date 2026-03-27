# Developer Knowledge API — Quick Reference

Base URL: `https://developerknowledge.googleapis.com`

Auth: API key via `?key=` query parameter.

## Endpoints

### 1. Search Document Chunks

```
GET /v1alpha/documents:searchDocumentChunks?query=QUERY&pageSize=N&key=KEY
```

| Parameter | Required | Default | Notes |
|-----------|----------|---------|-------|
| `query` | Yes | — | Natural language, e.g. "How to create a Cloud Storage bucket?" |
| `pageSize` | No | 5 | Max 20 |
| `pageToken` | No | — | For pagination |

**Response shape:**
```json
{
  "results": [
    {
      "parent": "documents/docs.cloud.google.com/storage/docs/creating-buckets",
      "id": "chunk-id",
      "content": "Markdown snippet..."
    }
  ],
  "nextPageToken": "..."
}
```

The `parent` field is the document name — use it with Get or BatchGet.

### 2. Get Document

```
GET /v1alpha/{name}?key=KEY
```

Where `{name}` is the `parent` from search results, e.g. `documents/docs.cloud.google.com/storage/docs/creating-buckets`.

Returns full Markdown content of the page.

### 3. Batch Get Documents

```
GET /v1alpha/documents:batchGet?names[]=NAME1&names[]=NAME2&key=KEY
```

Max 20 documents per batch. Returns them in request order.

**Response shape:**
```json
{
  "documents": [
    {
      "name": "documents/...",
      "content": "Full markdown..."
    }
  ]
}
```

## Corpus (Searchable Sites)

- ai.google.dev
- developer.android.com
- developer.chrome.com
- developers.home.google.com
- developers.google.com
- docs.cloud.google.com
- docs.apigee.com
- firebase.google.com
- fuchsia.dev
- web.dev
- www.tensorflow.org

Data freshness: re-indexed within 24 hours of publication.

## Quotas

- Preview API — check https://developers.google.com/knowledge/reference/quota-limits for current limits.
